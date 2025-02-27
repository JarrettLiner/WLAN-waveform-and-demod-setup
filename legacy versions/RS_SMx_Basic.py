from RsInstrument import RsInstrument, RsInstrException
import logging
import time
from typing import Optional, List, Tuple

class RS_SMX:
    """Class to control Rohde & Schwarz SMx Vector Signal Generators."""

    def __init__(self, resource_id: str, tmo_s: int):
        """Initializes the RS_SMX instrument."""
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        self.instrument = None
        try:
            self.instrument = RsInstrument(resource_id, reset=False, id_query=True)
            self.instrument.visa_timeout = tmo_s * 1000  # Convert seconds to milliseconds
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
            raise  # Raise the exception instead of just logging it

    def query_command(self, command: str) -> str:
        """Queries a SCPI command and returns the response."""
        try:
            return self.instrument.query_str(command)
        except RsInstrException as e:
            self.logger.error(f"Error querying command '{command}': {e}")
            raise  # Raise instead of returning empty string

    def opc_check(self, cmd: str):
        """Executes a command with OPC synchronization."""
        try:
            self.write_command("*ESE 1")  # Enable OPC bit
            self.write_command("*SRE 32")  # Service request for OPC
            self.write_command(f"{cmd};*OPC")
            timeout = time.time() + 10  # 10 second timeout
            while (self.instrument.query_int("*ESR?") & 1) != 1:
                if time.time() > timeout:
                    raise TimeoutError(f"OPC check timeout for command '{cmd}'")
                time.sleep(0.2)
            self.logger.info(f"Command '{cmd}' completed successfully.")
        except Exception as e:
            self.logger.error(f"Error during OPC check for command '{cmd}': {e}")
            raise

    def smx_preset(self):  # Method name should be lowercase with underscores
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
            freq = float(self.query_command(cmd))  # Use float instead of int
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
            power = float(self.query_command(cmd))  # Use float instead of int
            self.logger.info(f"Power level: {power} dBm")
            return power
        except Exception as e:
            self.logger.error(f"Error querying power level: {e}")
            return 0.0

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
        # Initialize the instrument
        signal_generator.smx_preset()
        # Set the frequency
        signal_generator.set_frequency(1e9)
        # Query the frequency
        freq = signal_generator.query_frequency()
        # Set the power level
        signal_generator.set_power_level(-10)
        # Query the power level
        power = signal_generator.query_power_level()

    except Exception as e:
        logging.getLogger(__name__).error(f"Error in main: {e}")
    finally:
        if signal_generator is not None:
            signal_generator.close()