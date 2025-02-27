from RsInstrument import RsInstrument, RsInstrException
import logging
import time
from enum import Enum
from typing import Optional, List, Tuple
from IEEE80211be import Bandwidth, IEEE80211be  # Assuming separate module
from pathlib import Path

"""
RS_SMX Waveform Generator for 802.11be (Wi-Fi 7) and 802.11ax (Wi-Fi 6)
Created: February 24, 2025
Author: Jarrett Liner, Rohde & Schwarz +13365012179
Dependencies: RsInstrument (pyvisa-based), IEEE80211be module, pathlib

Purpose:
    This script controls a Rohde & Schwarz SMW200A Vector Signal Generator to configure
    and generate WLAN waveforms for 802.11be (WBE) and 802.11ax (WAX) standards.
    It calculates the number of OFDM symbols and MPDUs required for a specified
    burst length and duty cycle, then applies these settings to the instrument.

Supported Standards:
    - WBE (802.11be): Uses EHT transmission modes (e.g., EHT320), MCS 0-13.
    - WAX (802.11ax): Uses HE transmission modes (e.g., HE80), MCS 0-11.

Key Features:
    - Configures bandwidth (BW20, BW40, BW80, BW160, BW320), MCS, burst length,
      and duty cycle.
    - Queries bits per symbol from the SMW for accurate MPDU calculations.
    - Supports dynamic guard interval (GI) settings (0.8, 1.6, 3.2 µs).
    - Includes error handling and logging for debugging.

Usage:
    1. Set the instrument address (e.g., 'TCPIP::192.168.200.10::hislip0').
    2. Define waveform parameters in the __main__ block (standard, bw, mcs,
       burst_length, duty_cycle).
    3. Run the script to configure the SMW and enable modulation.
    4. Optionally uncomment waveform saving to store .wv files.

Assumptions:
    - Preamble durations: 43.2 µs for WBE (EHT), 40 µs for WAX (HE SU).
    - IEEE80211be module provides MCS data for 802.11be; WAX MCS is limited to 0-11 here.

Customization Tips:
    - Extend IEEE80211be class for full 802.11ax MCS data if needed.
    - Add waveform saving by uncommenting the relevant section and providing a save directory.
    - Adjust header_duration if your PPDU type differs (e.g., HE MU vs. HE SU).
    - Modify TXMode Enum for additional modes (e.g., HE_TB for 802.11ax trigger-based).

Example Parameters:
    WBE: standard="WBE", bw="BW320", mcs="MCS13", burst_length=4e-3, duty_cycle=0.5
    WAX: standard="WAX", bw="BW80", mcs="MCS11", burst_length=4e-3, duty_cycle=0.5
"""

class TXMode(Enum):
    """Valid 802.11be transmission modes for SMW."""
    EHT_SU = "EHT_SU"  # Single-User MIMO
    EHT_MU = "EHT_MU"  # Multi-User MIMO/OFDMA
    EHT_TB = "EHT_TB"  # Trigger-Based PPDU

class RS_SMX:
    """Class to control Rohde & Schwarz SMx Vector Signal Generators."""

    def __init__(self, resource_id: str, tmo_s: int):
        """Initializes the RS_SMX instrument."""
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        self.instrument = None
        self.ieee_80211be = IEEE80211be()
        try:
            self.instrument = RsInstrument(resource_id, reset=False, id_query=True)
            self.instrument.visa_timeout = tmo_s * 1000
            idn = self.instrument.query_str("*IDN?").split(',')
            self.manufacturer = idn[0]
            self.model = idn[1]
            self.serial_number = idn[2]
            self.address = resource_id
            self.logger.info(f"Connected to {self.manufacturer} {self.model}, Serial: {self.serial_number}")
        except RsInstrException as e:
            self.logger.error(f"Failed to connect to the instrument: {e}")
            raise

    def write_command(self, command: str):
        """Sends a SCPI command to the instrument."""
        try:
            self.instrument.write_str(command)
        except RsInstrException as e:
            self.logger.error(f"Error sending command '{command}': {e}")
            raise

    def query_command(self, command: str) -> str:
        """Queries a SCPI command and returns the response."""
        try:
            return self.instrument.query_str(command)
        except RsInstrException as e:
            self.logger.error(f"Error querying command '{command}': {e}")
            raise

    def opc_check(self, cmd: str):
        """Executes a command with OPC synchronization."""
        try:
            self.write_command("*ESE 1")
            self.write_command("*SRE 32")
            self.write_command(f"{cmd};*OPC")
            timeout = time.time() + 10
            while (self.instrument.query_int("*ESR?") & 1) != 1:
                if time.time() > timeout:
                    raise TimeoutError(f"OPC check timeout for command '{cmd}'")
                time.sleep(0.2)
            self.logger.info(f"Command '{cmd}' completed successfully.")
        except Exception as e:
            self.logger.error(f"Error during OPC check for command '{cmd}': {e}")
            raise

    def smx_preset(self):
        """Resets the instrument to a preset state."""
        commands = ['*RST', '*CLS', 'SOURce1:BB:WLNN:PRESet']
        for cmd in commands:
            self.opc_check(cmd)
        time.sleep(3)
        self.logger.info("SMX preset completed.")

    def create_waveform(self, standard: str, bw: str, mcs: str, burst_length: float, duty_cycle: float):
        """Creates and saves an 802.11be waveform on the SMW."""
        try:
            # Validate duty cycle
            if not 0 < duty_cycle <= 1:
                raise ValueError(f"Duty cycle must be between 0 and 1, got {duty_cycle}")

            # Preset WLAN and disable baseband initially
            self.write_command("SOURce1:BB:WLNN:STATe 0")
            self.opc_check("SOURce1:BB:WLNN:PRESet")

            # Validate and set bandwidth
            try:
                bw_value = Bandwidth[bw.upper()].value
            except KeyError:
                valid_options = self.ieee_80211be.get_valid_bandwidths()
                raise ValueError(f"Invalid bandwidth! Must be one of {valid_options}")
            self.opc_check(f"SOURce1:BB:WLNN:BWidth {bw_value}")

            # Set standard (assuming WBE for 802.11be)
            if standard != "WBE":
                raise ValueError("Only 'WBE' (802.11be) is supported in this method")
            self.opc_check("SOURce1:BB:WLNN:FBLOck1:STANdard WBE")

            # Set TX Mode
            tx_mode = f"EHT{bw_value[2:]}"  # e.g., EHT320
            self.opc_check(f"SOURce1:BB:WLNN:FBLOck1:TMOde {tx_mode}")

            # Set MCS
            mcs_index = int(mcs.replace("MCS", "", 1))  # Convert 'MCS13' to 13
            if mcs_index not in self.ieee_80211be.MCS_DATA:
                raise ValueError(f"MCS index {mcs_index} is not valid for 802.11be")
            self.opc_check(f"SOURce1:BB:WLNN:FBLOck1:USER1:MCS {mcs}")

            # Timing configuration
            header_duration = 43.2e-6  # Typical EHT preamble duration (seconds)
            gi = self.query_command("SOURce1:BB:WLNN:FBLOck1:GUARd?")  # e.g., "GD08"
            gi_value = {"GD08": 0.8e-6, "GD16": 1.6e-6, "GD32": 3.2e-6}.get(gi, 0.8e-6)  # Default to 0.8 µs
            symbol_duration = 12.8e-6 + gi_value  # OFDM symbol duration + GI
            self.logger.debug(f"Symbol duration (including GI): {symbol_duration} s")

            # Calculate symbols and MPDUs
            bits_per_symbol = int(self.query_command("SOURce1:BB:WLNN:FBLock1:USER1:DATA:BPSymbol?"))
            bytes_per_symbol = bits_per_symbol // 8
            no_of_symbols_required = round((burst_length - header_duration) / symbol_duration, 0)
            print("Number of Symbols Required: ", no_of_symbols_required)
            no_of_bytes_required = no_of_symbols_required * bytes_per_symbol
            assert no_of_bytes_required > 100, "Number of required bytes too low"
            no_of_bytes_required -= 100  # Adjust to stay below limit
            self.logger.debug(f"No of symbols required: {no_of_symbols_required}")

            max_bytes_per_mpdu = int(self.query_command("SOURce1:BB:WLNN:FBLock1:USER1:MPDU1:DATA:LENGth? MAX"))
            no_of_mpdus_required, remainder = divmod(no_of_bytes_required, max_bytes_per_mpdu)
            no_of_mpdus_required = int(no_of_mpdus_required + 1)
            self.logger.debug(f"No of MPDUs required: {no_of_mpdus_required}, remainder: {remainder}")

            # Set MPDU count and data
            self.opc_check(f"SOURce1:BB:WLNN:FBLock1:USER1:MPDU1:COUNt {no_of_mpdus_required}")
            for mpdu in range(no_of_mpdus_required):
                self.write_command(f"SOURce1:BB:WLNN:FBLock1:USER1:MPDU{mpdu + 1}:DATA:SOURce PN23")
                if mpdu == no_of_mpdus_required - 1:
                    self.write_command(f"SOURce1:BB:WLNN:FBLock1:USER1:MPDU{mpdu + 1}:DATA:LENGth {remainder}")
                else:
                    self.write_command(f"SOURce1:BB:WLNN:FBLock1:USER1:MPDU{mpdu + 1}:DATA:LENGth {max_bytes_per_mpdu}")

            # Set idle time for duty cycle
            idle_time = burst_length * (1 / duty_cycle) - burst_length
            self.logger.debug(f"Calculated idle time: {idle_time} s for duty cycle {duty_cycle}")
            self.opc_check(f"SOURce1:BB:WLNN:FBLock1:ITIMe {idle_time}")
            Frame_Duration = self.query_command("SOURce1:BB:WLNN:FBLock1:DATA:FDURation?")
            print(f"Frame Duration: {Frame_Duration} ms")
            print("Duty Cycle: ", duty_cycle)
            idle = idle_time * 1e6  # Convert to microseconds
            print(f"idle time: {idle} us")
            '''
            # Enable baseband and create waveform
            self.opc_check("SOURce1:BB:WLNN:STATe 1")
            waveform_name = f"WLAN_{standard}_{bw}_{mcs}_burst{burst_length}s_duty{duty_cycle}.wv"
            savefile = savedir / waveform_name
            savefile = savefile.as_posix()
            self.opc_check(f"SOURce1:BB:WLNN:WAVeform:CREate \"{savefile}\"")
            self.logger.info(f"{waveform_name} successfully written") '''
            return 0

        except Exception as e:
            self.logger.error(f"Failed to create waveform: {e}")
            return -1

    def enable_modulation(self):
        """Enables the modulation output."""
        self.opc_check("OUTP ON")
        self.logger.info("Modulation output enabled.")

    def enable_WLAN(self):
        """Enables the WLAN output."""
        self.write_command("SOURce1:BB:WLNN:STATe 1")
        self.logger.info("WLAN output enabled.")

    def disable_WLAN(self):
        """Disables the WLAN output."""
        self.opc_check("SOURce1:BB:WLNN:STATe 0")
        self.logger.info("WLAN output disabled.")


    def disable_modulation(self):
        """Disables the modulation output."""
        self.opc_check("OUTP OFF")
        self.logger.info("Modulation output disabled.")

    def close(self):
        """Closes the connection to the instrument."""
        try:
            if self.instrument is not None:
                self.instrument.close()
                self.logger.info("Instrument connection closed.")
        except RsInstrException as e:
            self.logger.error(f"Error closing instrument connection: {e}")
            raise

# Example Usage
if __name__ == "__main__":
    instr_address = "TCPIP::192.168.200.10::hislip0"
    signal_generator = None
    try:
        signal_generator = RS_SMX(instr_address, tmo_s=50)  # Increased timeout for waveform creation
        signal_generator.smx_preset()
        '''
        savedir = Path(r"C:\Temp\Waveforms")  # Adjust to your directory
        assert savedir.is_dir(), "Savedir is not a correct path"
        '''
        # 802.11be waveform parameters
        standard = "WBE"
        bw = "BW320"
        mcs = "MCS13"
        burst_length =4e-3  # seconds
        duty_cycle =0.5  # Duty cycle as a float between 0 and 1

        result = signal_generator.create_waveform(standard, bw, mcs, burst_length, duty_cycle)
        if result == 0:
            signal_generator.enable_WLAN()
            signal_generator.enable_modulation()

    except Exception as e:
        logging.getLogger(__name__).error(f"Error in main: {e}")
    finally:
        if signal_generator is not None:
            signal_generator.close()