"""
RS_FSX_WLAN_AX_BE.py
Created: February 25, 2025
Author: Jarrett Liner, Rohde & Schwarz +13365012179
Dependencies: RsInstrument (pyvisa-based), RS_SMx_WLAN_AX_BE.py, WLAN_Standards_Translator.py

Purpose:
    This script controls a Rohde & Schwarz FSW Spectrum Analyzer to configure WLAN measurements
    for 802.11ax (Wi-Fi 6) and 802.11be (Wi-Fi 7) standards, synchronizing settings with an SMW200A
    signal generator. It sets up the WLAN application, adjusts capture time based on SMW frame
    duration and idle time, and ensures reliable SCPI communication with OPC synchronization.

Supported Standards:
    - IEEE 802.11ax (WAX on SMW, :CONF:STAN 10 on FSW)
    - IEEE 802.11be (WBE on SMW, :CONF:STAN 11 on FSW)
    - Older standards (e.g., 802.11a/b/g/n/ac) via WLAN_Standards_Translator

Key Features:
    - Synchronizes FSW frequency and WLAN standard with SMW output.
    - Sets capture time to 4x (frame duration + idle time) from SMW, capped at 1 second.
    - Uses OPC synchronization for all SCPI writes and queries to ensure reliability.

Usage:
    1. Ensure FSW and SMW are connected (e.g., 'TCPIP::192.168.200.20::INSTR' for FSW).
    2. Run the script to extract SMW settings, sync FSW, and configure WLAN app.
    3. Check logs for errors or warnings (e.g., capture time capping).

Notes:
    - SMW frame duration and idle time are reported in milliseconds, converted to seconds here.
    - FSW sweep time (:SENS:SWE:TIME) has a typical max of 1 s; adjust max_capture_time_s if extended memory is available.
    - External trigger (:TRIG:SEQ:SOUR EXT) requires a physical trigger connection.
"""
from RsInstrument import RsInstrument, RsInstrException
import logging
import time
from RS_SMx_WLAN_AX_BE import RS_SMX
from WLAN_Standards_Translator import WLAN_Standards_Translator


class RS_FSX_WLAN_AX_BE:
    """Class to control Rohde & Schwarz FSW Spectrum Analyzer for WLAN AX/BE measurements."""

    def __init__(self, resource_id: str, tmo_s: int, smw_resource_id: str = None):
        """
        Initializes the FSW with an optional SMW connection.

        Args:
            resource_id (str): FSW VISA address (e.g., 'TCPIP::192.168.200.20::INSTR').
            tmo_s (int): Timeout in seconds for VISA operations.
            smw_resource_id (str, optional): SMW VISA address (e.g., 'TCPIP::192.168.200.10::INSTR').
        """
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        self.instrument = None
        self.smw = None
        self.translator = WLAN_Standards_Translator()  # Maps SMW standards (WAX/WBE) to FSW commands
        try:
            self.instrument = RsInstrument(resource_id, reset=False, id_query=True)
            self.instrument.visa_timeout = tmo_s * 1000  # Convert to milliseconds
            idn = self.instrument.query_str("*IDN?").split(',')
            self.manufacturer = idn[0]
            self.model = idn[1]
            self.serial_number = idn[2]
            self.address = resource_id
            self.logger.info(f"Connected to {self.manufacturer} {self.model}, Serial: {self.serial_number}")

            if smw_resource_id:
                self.smw = RS_SMX(smw_resource_id, tmo_s)
                self.logger.info("SMW connection established for WLAN AX/BE settings retrieval.")
        except RsInstrException as e:
            self.logger.error(f"Failed to connect to the instrument: {e}")
            raise

    def write_command(self, command: str):
        """Sends a SCPI command to the FSW with OPC synchronization for reliability."""
        try:
            self.instrument.write_str(f"{command};*OPC")  # Append *OPC to wait for completion
            timeout = time.time() + 10  # 10-second timeout
            while self.instrument.query_int("*ESR?") & 1 != 1:  # Check ESR bit 0 for completion
                if time.time() > timeout:
                    raise TimeoutError(f"OPC timeout for write command '{command}'")
                time.sleep(0.2)
            self.logger.debug(f"Write command '{command}' completed successfully.")
        except RsInstrException as e:
            self.logger.error(f"Error sending command '{command}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during write command '{command}': {e}")
            raise

    def query_command(self, command: str) -> str:
        """Queries a SCPI command from the FSW with OPC synchronization."""
        try:
            # query_str_with_opc ensures the query completes before returning the response
            response = self.instrument.query_str_with_opc(command)
            self.logger.debug(f"Query command '{command}' returned: {response}")
            return response
        except RsInstrException as e:
            self.logger.error(f"Error querying command '{command}': {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during query command '{command}': {e}")
            raise

    def opc_check(self, cmd: str):
        """Legacy method for explicit OPC synchronization; uses write_command internally."""
        try:
            self.write_command(cmd)
        except Exception as e:
            self.logger.error(f"Error during OPC check for command '{cmd}': {e}")
            raise

    def FSW_preset(self):
        """Preset the FSW to default settings."""
        try:
            self.write_command("*CLS; *RST")  # Preset the instrument
            self.logger.info("FSW preset completed successfully.")
        except Exception as e:
            self.logger.error(f"Error during FSW preset: {e}")
            raise

    def FSW_autolevel(self):
        """Perform auto power leveling on the FSW."""
        try:
            self.write_command(':CONF:POW:AUTO ONCE; *WAI')  # Auto power leveling
            self.logger.info("FSW auto power leveling completed successfully.")
        except Exception as e:
            self.logger.error(f"Error during FSW auto power leveling: {e}")
            raise

    def setup_WLAN_app(self, standard: str = "WBE"):
        """Configures the WLAN application on the FSW, adjusting capture time based on SMW settings.

        Args:
            standard (str): WLAN standard from SMW (e.g., 'WAX' for 802.11ax, 'WBE' for 802.11be).

        Notes:
            - Capture time is set to 4x (frame duration + idle time) from SMW, converted from ms to s.
            - Capped at 1 s to avoid FSW range errors; adjust max_capture_time_s if extended memory is used.
            - Requires SMW connection for capture time adjustment.
        """
        try:
            self.write_command(':INST:CRE:NEW WLAN, "WLAN"')  # Start WLAN measurement mode
            standard_command = self.translator.to_fsw_command(standard)  # Translate SMW standard to FSW
            self.write_command(standard_command)  # e.g., :CONF:STAN 10 for WAX
            self.write_command(':CONF:POW:AUTO ONCE; *WAI')  # Auto power leveling
            self.write_command(':INP:GAIN:STAT OFF')  # Disable input gain
            self.write_command(':TRIG:SEQ:SOUR EXT')  # Use external trigger (ensure connection)

            if self.smw:
                # SMW reports frame duration and idle time in milliseconds; convert to seconds
                frame_duration_ms = float(self.smw.query_command("SOURce1:BB:WLNN:FBLock1:DATA:FDURation?"))
                idle_time_ms = float(self.smw.query_command("SOURce1:BB:WLNN:FBLock1:ITIMe?"))
                frame_duration_s = frame_duration_ms / 1000.0
                idle_time_s = idle_time_ms / 1000.0
                capture_time_s = 4 * (frame_duration_s + idle_time_s)  # 4x total burst time
                max_capture_time_s = 1.0  # FSW typical max; increase if extended memory available
                if capture_time_s > max_capture_time_s:
                    self.logger.warning(f"Calculated capture time {capture_time_s:.6f} s exceeds FSW max "
                                       f"({max_capture_time_s} s). Capping at {max_capture_time_s} s.")
                    capture_time_s = max_capture_time_s
                self.write_command(f":SENS:SWE:TIME {capture_time_s}")  # Set capture time in seconds
                self.logger.info(f"Set capture time to {capture_time_s*1000:.3f} ms "
                                f"(4x frame_duration={frame_duration_s*1000:.3f} ms + idle_time={idle_time_s*1000:.3f} ms)")
            else:
                self.logger.warning("No SMW connected. Skipping capture time adjustment; default FSW time applies.")

            self.logger.info(f"WLAN app configured with {standard_command} ({self.translator.to_description(standard)})")
        except Exception as e:
            self.logger.error(f"Failed to setup WLAN app: {e}")
            raise

    def extract_settings_from_generator(self) -> dict:
        """Extracts key settings from the SMW signal generator.

        Returns:
            dict: SMW settings with frame_duration_s and idle_time_s in seconds.

        Notes:
            - SMW returns frame duration and idle time in milliseconds; converted here to seconds.
            - Requires SMW connection; returns empty dict if not connected.
        """
        if not self.smw:
            self.logger.warning("No SMW connected. Returning empty settings.")
            return {}

        try:
            frame_duration_ms = float(self.smw.query_command("SOURce1:BB:WLNN:FBLock1:DATA:FDURation?"))
            idle_time_ms = float(self.smw.query_command("SOURce1:BB:WLNN:FBLock1:ITIMe?"))
            settings = {
                "frequency_hz": float(self.smw.query_command("FREQ:CW?")),
                "power_dbm": float(self.smw.query_command("SOURce1:POW:LEV:IMM:AMPL?")),
                "rf_output_enabled": self.smw.query_command("OUTPut1:STATe?") == "1",
                "wlan_enabled": self.smw.query_command("SOURce1:BB:WLNN:STATe?") == "1",
                "standard": self.smw.query_command("SOURce1:BB:WLNN:FBLOck1:STANdard?"),
                "bandwidth": self.smw.query_command("SOURce1:BB:WLNN:BWidth?"),
                "mcs": self.smw.query_command("SOURce1:BB:WLNN:FBLOck1:USER1:MCS?"),
                "guard_interval": self.smw.query_command("SOURce1:BB:WLNN:FBLOck1:GUARd?"),
                "idle_time_s": idle_time_ms / 1000.0,  # Convert ms to s
                "frame_duration_s": frame_duration_ms / 1000.0  # Convert ms to s
            }
            self.logger.info(f"Extracted SMW settings: {settings}")
            return settings
        except ValueError as e:
            self.logger.error(f"Invalid numeric response from SMW: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Error extracting SMW settings: {e}")
            return {}

    def sync_with_smw(self):
        """Synchronizes FSW frequency and standard with SMW output."""
        if not self.smw:
            self.logger.warning("No SMW connected. Skipping synchronization.")
            return

        try:
            settings = self.extract_settings_from_generator()
            if not settings:
                raise ValueError("Failed to retrieve SMW settings for synchronization")

            self.write_command(f":FREQ:CENT {settings['frequency_hz']}")  # Sync center frequency
            standard_command = self.translator.to_fsw_command(settings["standard"])
            self.write_command(standard_command)  # Sync WLAN standard

            self.logger.info(f"Synchronized FSW with SMW: Freq={settings['frequency_hz']/1e6} MHz, "
                            f"Standard={self.translator.to_description(settings['standard'])}")
        except Exception as e:
            self.logger.error(f"Failed to sync with SMW: {e}")
            raise


# Example usage
if __name__ == "__main__":
    # Example: Connect to FSW at 192.168.200.20 and SMW at 192.168.200.10
    fsw = RS_FSX_WLAN_AX_BE("TCPIP::192.168.200.20::INSTR", tmo_s=10, smw_resource_id="TCPIP::192.168.200.10::INSTR")
    fsw.FSW_preset()  # Preset FSW to default settings
    settings = fsw.extract_settings_from_generator()  # Get SMW settings
    print("SMW Settings:", settings)
    fsw.setup_WLAN_app(standard=settings.get("standard", "WBE") if settings else "WBE")  # Configure WLAN app
    fsw.sync_with_smw()  # Sync FSW with SMW
    fsw.FSW_autolevel()  # Perform auto power leveling
