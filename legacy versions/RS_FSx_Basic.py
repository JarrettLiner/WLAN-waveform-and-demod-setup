from RsInstrument import RsInstrument, RsInstrException
import logging
import time
from typing import Optional, List, Tuple

class RS_SMx:
    """Class to control Rohde & Schwarz SMx Vector Signal Generators."""

    def __init__(self, resource_id: str, tmo_s: int):
        """Initializes the RS_SMx instrument."""
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        self.instrument = None
        try:
            self.instrument = RsInstrument(resource_id, reset=False, id_query=True)
            self.instrument.visa_timeout = tmo_s * 10000  # Set timeout in milliseconds
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

    def query_command(self, command: str) -> str:
        """Queries a SCPI command and returns the response."""
        try:
            return self.instrument.query_str(command)
        except RsInstrException as e:
            self.logger.error(f"Error querying command '{command}': {e}")
            return ""

    def query_command_int(self, command: str) -> int:
        """Queries a SCPI command and returns an integer response."""
        try:
            return self.instrument.query_int(command)
        except RsInstrException as e:
            self.logger.error(f"Error querying command '{command}': {e}")
            return 0

    def opc_check(self, cmd: str):
        """Executes a command with OPC synchronization."""
        try:
            self.write_command("*ESE 1")  # Enable OPC bit
            self.write_command("*SRE 32")  # Service request for OPC
            self.write_command(f"{cmd};*OPC")
            while (self.query_command_int("*ESR?") & 1) != 1:
                time.sleep(0.2)
            self.logger.info(f"Command '{cmd}' completed successfully.")
        except Exception as e:
            self.logger.error(f"Error during OPC check for command '{cmd}': {e}")
            raise

    def SMx_preset(self):
        """Resets the instrument to a preset state."""
        commands = ['*RST', '*CLS']
        for cmd in commands:
            self.opc_check(cmd)
        time.sleep(3)
        self.logger.info("SMx preset completed.")

    def set_frequency(self, frequency: float):
        """Sets the output frequency of the instrument."""
        cmd = f"FREQ:CW {frequency} Hz"
        self.opc_check(cmd)
        self.logger.info(f"Frequency set to {frequency} Hz.")

    def query_frequency(self) -> float:
        """Queries the output frequency of the instrument."""
        cmd = "FREQ:CW?"
        freq = self.query_command_int(cmd)
        self.logger.info(f"Frequency: {freq} Hz")
        return freq

    def set_power_level(self, power: float):
        """Sets the output power level of the instrument."""
        cmd = f"SOUR:POW:LEV:IMM:AMPL {power} dBm"
        self.opc_check(cmd)
        self.logger.info(f"Power level set to {power} dBm.")

    def query_power_level(self) -> float:
        """Queries the output power level of the instrument."""
        cmd = "SOUR:POW:LEV:IMM:AMPL?"
        power = self.query_command_int(cmd)
        self.logger.info(f"Power level: {power} dBm")
        return power

    def close(self):
        """Closes the connection to the instrument."""
        try:
            self.instrument.close()
            self.logger.info("Instrument connection closed.")
        except RsInstrException as e:
            self.logger.error(f"Error closing instrument connection: {e}")


# Example Usage
if __name__ == "__main__":
    instr_address_1 = "TCPIP::192.168.200.20::hislip0"
    FSx_1 = None
    try:
        FSx_1 = RS_FSx(instr_address_1, tmo_s=10)
        # Initialize the instrument
        FSx_1.FSW_preset()
        FSx_1.auto_level_once()
        # Check status and errors
        #  RS_SMx.query_error_queue()
        FSx_1.query_status_byte()
        # Set frequency
        FSx_1.set_frequency(frequency=6.905e9)
        FSx_1.query_frequency()
        FSx_1.set_trigger_input("EXT")
        FSx_1.set_span(span=200e6)
        # Set reference level
        ref_lvl = FSx_1.query_reference_level()
        FSx_1.set_reference_level(ref_lvl)
        # Enable auto attenuation
        FSx_1.set_auto_attenuation(True)
        # New features
        FSx_1.set_resolution_bandwidth(1e6)  # 1 MHz RBW
        FSx_1.single_sweep()
        FSx_1.set_remote_mode(False)  # Ensure remote control
    except Exception as e:
        logging.getLogger(__name__).error(f"Error in main: {e}")
    finally:
        if FSx_1 is not None:
            FSx_1.close()