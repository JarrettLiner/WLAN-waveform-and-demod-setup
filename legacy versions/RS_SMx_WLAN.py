from RsInstrument import RsInstrument, RsInstrException
import logging
import time
from enum import Enum
from typing import Optional, List, Tuple
from IEEE80211be  import Bandwidth, IEEE80211be

# Assuming IEEE80211be is in the same file or imported
# from your_module import IEEE80211be, Bandwidth

class RS_SMX:
    """Class to control Rohde & Schwarz SMx Vector Signal Generators."""

    def __init__(self, resource_id: str, tmo_s: int):
        """Initializes the RS_SMX instrument."""
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        self.instrument = None
        self.ieee_80211be = IEEE80211be()  # Instantiate the 802.11be reference
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
        commands = ['*RST', '*CLS']
        for cmd in commands:
            self.opc_check(cmd)
        time.sleep(3)
        self.logger.info("SMX preset completed.")

    def set_frequency(self, frequency: float):
        """Sets the output frequency of the instrument."""
        cmd = f"FREQ:CW {frequency} Hz"
        self.opc_check(cmd)
        self.logger.info(f"Frequency set to {frequency} Hz")

    def query_frequency(self) -> float:
        """Queries the output frequency of the instrument."""
        try:
            cmd = "FREQ:CW?"
            freq = float(self.query_command(cmd))
            self.logger.info(f"Frequency: {freq} Hz")
            return freq
        except Exception as e:
            self.logger.error(f"Error querying frequency: {e}")
            return 0.0

    def set_power_level(self, power: float):
        """Sets the output power level of the instrument."""
        cmd = f"SOUR:POW:LEV:IMM:AMPL {power} dBm"
        self.opc_check(cmd)
        self.logger.info(f"Power level set to {power} dBm")

    def query_power_level(self) -> float:
        """Queries the output power level of the instrument."""
        try:
            cmd = "SOUR:POW:LEV:IMM:AMPL?"
            power = float(self.query_command(cmd))
            self.logger.info(f"Power level: {power} dBm")
            return power
        except Exception as e:
            self.logger.error(f"Error querying power level: {e}")
            return 0.0

    def setup_11bexxx(self, bandwidth: str, mcs_index: Optional[int] = None):
        """Configures the instrument for 802.11be signal generation."""
        # Validate bandwidth
        try:
            bw_value = Bandwidth[bandwidth.upper()].value
        except KeyError:
            valid_options = self.ieee_80211be.get_valid_bandwidths()
            raise ValueError(f"Invalid bandwidth! Must be one of {valid_options}")

        # Validate MCS index if provided
        if mcs_index is not None:
            if mcs_index not in self.ieee_80211be.MCS_DATA:
                raise ValueError(f"MCS index {mcs_index} is not valid for 802.11be")

        try:
            # Enable WLAN baseband
            self.opc_check("SOURce1:BB:WLNN:STATe ON")
            # Set WLAN standard to 802.11be
            self.opc_check("SOURce1:BB:WLNN:FBLOCK1:STANdard WBE")
            # Set bandwidth
            self.opc_check(f"SOURce1:BB:WLNN:BWidth {bw_value}")
            # Set MCS index if provided
            if mcs_index is not None:
                self.opc_check(f"SOURce1:BB:WLNN:FBLOck1:USER1:MCS MCS{mcs_index}")
            self.logger.info(f"802.11be configured with bandwidth {bw_value}" +
                             (f" and MCS {mcs_index}" if mcs_index is not None else ""))
        except Exception as e:
            self.logger.error(f"Failed to configure 802.11be: {e}")
            raise

    def setup_11be(self, bandwidth: str,tx_mode: str, burst_length: int, mcs_index: Optional[int] = None, num_mpdus: Optional[int] = None,
                   guard_interval: float = 0.8, mpdu_size: int = 128.5):
        """Configures the instrument for 802.11be signal generation with MPDU count."""
        # Validate bandwidth
        try:
            bw_value = Bandwidth[bandwidth.upper()].value
        except KeyError:
            valid_options = self.ieee_80211be.get_valid_bandwidths()
            raise ValueError(f"Invalid bandwidth! Must be one of {valid_options}")
        # Set Tx Mode
        try:
            tx_mode = ''.join(['EHT', bw_value[2:]]) # Extract numeric part (e.g., 320 from "BW320")
        except KeyError:
            valid_options = self.ieee_80211be.get_valid_bandwidths()
            raise ValueError(f"Invalid TX Mode! Must be one of HE {valid_options}")
        # Validate MCS index if provided
        if mcs_index is not None:
            if mcs_index not in self.ieee_80211be.MCS_DATA:
                raise ValueError(f"MCS index {mcs_index} is not valid for 802.11be")

        # Validate guard interval (in µs)
        valid_gi = [gi / 1000 for gi in self.ieee_80211be.VALID_GI]  # Convert ns to µs
        if guard_interval not in valid_gi:
            raise ValueError(f"Guard Interval {guard_interval} µs is not valid. Must be one of {valid_gi}")

        # Validate num_mpdus if provided
        if num_mpdus is not None and (not isinstance(num_mpdus, int) or num_mpdus <= 0):
            raise ValueError("Number of MPDUs must be a positive integer")

        try:
            # Enable WLAN baseband
            self.opc_check("SOURce1:BB:WLNN:STATe ON")
            # Set WLAN standard to 802.11be
            self.opc_check("SOURce1:BB:WLNN:FBLOCK1:STANdard WBE")
            # Set bandwidth
            self.opc_check(f"SOURce1:BB:WLNN:BWidth {bw_value}")
            # Set Tx Mode
            self.opc_check(f"SOURce1:BB:WLNN:FBLOck1:TXMOde {tx_mode}")
            # Set MCS index if provided
            if mcs_index is not None:
                self.opc_check(f"SOURce1:BB:WLNN:FBLOck1:USER1:MCS MCS{mcs_index}")
            # Set guard interval
            gi_map = {0.8: "GD08", 1.6: "GD16", 3.2: "GD32"}  # SMW Guard Interval syntax
            self.opc_check(f"SOURce1:BB:WLNN:FBLOck1:GUARd  {gi_map[guard_interval]}")

            # Set number of MPDUs if provided
            if num_mpdus is not None:
                self.opc_check(f"SOURce1:BB:WLNN:FBLock1:USER1:MPDU1:COUNt {num_mpdus}")

                # Estimate frame duration for logging (optional)
                if mcs_index is not None:
                    bw_mhz = int(bw_value[2:])  # Extract numeric part (e.g., 320 from "BW320")
                    gi_ns = int(guard_interval * 1000)  # Convert µs to ns
                    data_rate = self.ieee_80211be.get_data_rate(mcs_index, bw_mhz, gi_ns)
                    if data_rate:
                        header_duration = 43.2e-6  # approx.
                        t_symbol = 12.8 + guard_interval  # Symbol duration in µs
                        bits_per_symbol = int (self.query_command("SOURce1:BB:WLNN:FBLock1:USER1:DATA:BPSYmbols?"))
                        bytes_per_symbol = bits_per_symbol // 8
                        symbol_duration = round(symbol_duration + gi, 7)
                        # set symbols, round them
                        no_of_symbols_required = round((burst_length - header_duration) / symbol_duration, 0)
                        no_of_bytes_required = no_of_symbols_required * bytes_per_symbol
                        # 4bytes are added automatically. Reduce number of required bytes by 100 to stay below limit
                        assert no_of_bytes_required > 100, 'no of required bytes too low'
                        no_of_bytes_required -= 100
                        logger.debug(f'no_of_symbols_required: {no_of_symbols_required}')
                        # max_bytes_per_mpdu = 116991
                        max_bytes_per_mpdu = int(winiq.query(':SOURce1:BB:WLNN:FBLock1:USER1:MPDU1:DATA:LENGth? MAX'))
                        no_of_mpdus_required, remainder = divmod(no_of_bytes_required, max_bytes_per_mpdu)
                        no_of_mpdus_required = int(no_of_mpdus_required + 1)
                        logger.debug(f'no_of_mpdus_required: {no_of_mpdus_required}, remainder: {remainder}')
                        #
                        self.write_command(f':SOURce1:BB:WLNN:FBLock1:MPDU1:COUNt {no_of_mpdus_required}')
                        for mpdu in range(no_of_mpdus_required):
                            self.write_command(f':SOURce1:BB:WLNN:FBLock1:USER1:MPDU{mpdu + 1}:DATA:SOURce PN23')
                            if mpdu == no_of_mpdus_required - 1:
                                self.write_command(f':SOURce1:BB:WLNN:FBLock1:USER1:MPDU{mpdu + 1}:DATA:LENGth {remainder}')
                            else:
                                self.write_command(
                                    f':SOURce1:BB:WLNN:FBLock1:USER1:MPDU{mpdu + 1}:DATA:LENGth {max_bytes_per_mpdu}')
                        #
                    else:
                        logger.info('wrong \'standard\' string')
                        return -1
                        #  bits_per_symbol = (data_rate * t_symbol) / 1e6  # Mbit/s * µs = bits
                        no_of_symbols_required = round((burst_length - header_duration) / symbol_duration, 0)
                        no_of_bytes_required = no_of_symbols_required * bytes_per_symbol
                        mpdu_bits = mpdu_size * 8  # Bytes to bits
                        symbols_per_mpdu = mpdu_bits / bits_per_symbol
                        total_symbols = num_mpdus * symbols_per_mpdu
                        t_preamble = 36  # Assumed preamble duration in µs
                        t_ppdu = t_preamble + (total_symbols * t_symbol)
                        self.logger.info(f"Estimated {num_mpdus} MPDUs = {total_symbols:.1f} symbols, "
                                         f"PPDU duration: {t_ppdu:.1f} µs")
                    else:
                        self.logger.warning("Could not estimate frame duration due to missing data rate")

            self.logger.info(f"802.11be configured with bandwidth {bw_value}" +
                             (f" and MCS {mcs_index}" if mcs_index is not None else "") +
                             (f", {num_mpdus} MPDUs" if num_mpdus is not None else ""))
        except Exception as e:
            self.logger.error(f"Failed to configure 802.11be: {e}")
            raise

    def enable_ARB(self):
        """Enables the ARB output."""
        cmd = "OUTP:ARB ON"
        self.opc_check(cmd)
        self.logger.info("ARB output enabled.")

    def disable_ARB(self):
        """Disables the ARB output."""
        cmd = "OUTP:ARB OFF"
        self.opc_check(cmd)
        self.logger.info("ARB output disabled.")

    def enable_modulation(self):
        """Enables the modulation output."""
        cmd = "OUTP ON"
        self.opc_check(cmd)
        self.logger.info("Modulation output enabled.")

    def disable_modulation(self):
        """Disables the modulation output."""
        cmd = "OUTP OFF"
        self.opc_check(cmd)
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
        signal_generator = RS_SMX(instr_address, tmo_s=10)
        signal_generator.smx_preset()
        signal_generator.set_frequency(6e9)
        freq = signal_generator.query_frequency()
        signal_generator.set_power_level(-20)
        power = signal_generator.query_power_level()
        signal_generator.setup_11be("BW320", mcs_index=9, num_mpdus=10, guard_interval=0.8)
        signal_generator.enable_modulation()

        # Example: Query MCS data
        modulation, coding_rate, rates = signal_generator.ieee_80211be.get_mcs_info(13)
        data_rate = signal_generator.ieee_80211be.get_data_rate(9, 320, 800)
        print(f"MCS 13: {modulation}, {coding_rate}, 320 MHz @ 800 ns GI: {data_rate} Mbit/s")
        MPDU_count = signal_generator.query_command("SOURce1:BB:WLNN:FBLock1:MPDU1:COUNt?")
        print(f"MPDU count: {MPDU_count}")
        FRAME_duration = signal_generator.query_command("SOURce1:BB:WLNN:FBLock1:DATA:FDURation?")
        print(f"FRAME duration: {FRAME_duration}")
        SYMBOLS_count = signal_generator.query_command("SOURce1:BB:WLNN:FBLock1:USER1:DATA:SYMBols?")
        print(f"SYMBOLS count: {SYMBOLS_count}")

    except Exception as e:
        logging.getLogger(__name__).error(f"Error in main: {e}")
    finally:
        if signal_generator is not None:
            signal_generator.close()