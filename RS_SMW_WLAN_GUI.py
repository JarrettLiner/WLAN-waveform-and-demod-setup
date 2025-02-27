# Import required libraries for GUI creation and instrument control
import tkinter as tk  # Basic GUI toolkit
from tkinter import ttk, messagebox  # Themed widgets and dialog boxes
from RS_SMx_WLAN_AX_BE import RS_SMX  # Custom module for Rohde & Schwarz SMx signal generator control
import logging  # For logging status and errors


class RS_SMX_GUI:
    """
    A GUI class to control the Rohde & Schwarz SMx Vector Signal Generator for WLAN signal generation.
    Supports 802.11be (Wi-Fi 7) and 802.11ax (Wi-Fi 6) standards.

    Notes:
    - This GUI allows users to configure waveform parameters and control the instrument.
    - It assumes the RS_SMX class is defined in 'RS_SMx_WLAN_AX_BE.py' (updated filename).
    - The signal parameter display section was removed from an earlier version for simplicity.
    """

    def __init__(self, root):
        # Initialize the GUI window
        self.root = root
        self.root.title("RS_SMX Waveform Generator Control")  # Set window title
        self.signal_generator = None  # Placeholder for the RS_SMX object (set on connection)

        # Configure logging for debugging and status updates
        logging.basicConfig(level=logging.INFO)  # Log info-level messages and above
        self.logger = logging.getLogger(__name__)  # Logger instance for this class

        # Create the main frame to hold all widgets
        self.main_frame = ttk.Frame(self.root, padding="10")  # Padding for spacing
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))  # Fill the window

        # --- Input Fields ---
        # Instrument Address
        ttk.Label(self.main_frame, text="Instrument Address:").grid(row=0, column=0, sticky=tk.W)
        self.address_var = tk.StringVar(value="TCPIP::192.168.200.10::hislip0")  # Default IP address
        ttk.Entry(self.main_frame, textvariable=self.address_var, width=30).grid(row=0, column=1, sticky=tk.W)
        # Note: Enter the instrument’s TCPIP address here (e.g., 'TCPIP::[IP]::hislip0').

        # WLAN Standard (WBE for 802.11be, WAX for 802.11ax)
        ttk.Label(self.main_frame, text="Standard:").grid(row=1, column=0, sticky=tk.W)
        self.standard_var = tk.StringVar(value="WBE")  # Default to 802.11be
        ttk.Combobox(self.main_frame, textvariable=self.standard_var, values=["WBE", "WAX"], state="readonly").grid(
            row=1, column=1, sticky=tk.W)
        # Note: 'readonly' prevents manual text entry, ensuring valid options only.

        # Bandwidth Selection
        ttk.Label(self.main_frame, text="Bandwidth:").grid(row=2, column=0, sticky=tk.W)
        self.bw_var = tk.StringVar(value="BW320")  # Default to 320 MHz
        ttk.Combobox(self.main_frame, textvariable=self.bw_var, values=["BW20", "BW40", "BW80", "BW160", "BW320"],
                     state="readonly").grid(row=2, column=1, sticky=tk.W)
        # Note: Options correspond to 20, 40, 80, 160, and 320 MHz bandwidths.

        # Modulation and Coding Scheme (MCS)
        ttk.Label(self.main_frame, text="MCS:").grid(row=3, column=0, sticky=tk.W)
        self.mcs_var = tk.StringVar(value="MCS13")  # Default to MCS13 (highest for WBE)
        self.mcs_combo = ttk.Combobox(self.main_frame, textvariable=self.mcs_var, state="readonly")
        self.mcs_combo.grid(row=3, column=1, sticky=tk.W)
        self.update_mcs_options()  # Populate MCS options based on standard
        # Note: MCS options adjust dynamically based on the selected standard.

        # Burst Length (in seconds)
        ttk.Label(self.main_frame, text="Burst Length (s):").grid(row=4, column=0, sticky=tk.W)
        self.burst_var = tk.DoubleVar(value=0.004)  # Default to 4 ms
        ttk.Entry(self.main_frame, textvariable=self.burst_var, width=10).grid(row=4, column=1, sticky=tk.W)
        # Note: Enter a float value (e.g., 0.004 for 4 ms).

        # Duty Cycle (0 to 1)
        ttk.Label(self.main_frame, text="Duty Cycle (0-1):").grid(row=5, column=0, sticky=tk.W)
        self.duty_var = tk.DoubleVar(value=0.5)  # Default to 50%
        ttk.Entry(self.main_frame, textvariable=self.duty_var, width=10).grid(row=5, column=1, sticky=tk.W)
        # Note: Must be a float between 0 and 1 (e.g., 0.5 for 50% duty cycle).

        # Frequency (in Hz)
        ttk.Label(self.main_frame, text="Frequency (Hz):").grid(row=6, column=0, sticky=tk.W)
        self.freq_var = tk.DoubleVar(value=6e9)  # Default to 6 GHz
        ttk.Entry(self.main_frame, textvariable=self.freq_var, width=15).grid(row=6, column=1, sticky=tk.W)
        # Note: Enter frequency in Hz (e.g., 6e9 for 6 GHz).

        # Power Level (in dBm)
        ttk.Label(self.main_frame, text="Power Level (dBm):").grid(row=7, column=0, sticky=tk.W)
        self.power_var = tk.DoubleVar(value=-10)  # Default to -10 dBm
        ttk.Entry(self.main_frame, textvariable=self.power_var, width=10).grid(row=7, column=1, sticky=tk.W)
        # Note: Enter power in dBm (e.g., -10 for -10 dBm).

        # --- Control Buttons ---
        ttk.Button(self.main_frame, text="Connect", command=self.connect).grid(row=8, column=0, pady=5)
        ttk.Button(self.main_frame, text="Preset", command=self.preset).grid(row=8, column=1, pady=5)
        ttk.Button(self.main_frame, text="Generate Waveform", command=self.generate_waveform).grid(row=9, column=0,
                                                                                                   pady=5)
        ttk.Button(self.main_frame, text="Enable Output", command=self.enable_output).grid(row=9, column=1, pady=5)
        ttk.Button(self.main_frame, text="Disable Output", command=self.disable_output).grid(row=10, column=0, pady=5)
        ttk.Button(self.main_frame, text="Close", command=self.close).grid(row=10, column=1, pady=5)
        # Note: Buttons control the instrument; 'Connect' must be clicked first.

        # --- Status Display ---
        self.status_var = tk.StringVar(value="Disconnected")  # Initial status
        ttk.Label(self.main_frame, textvariable=self.status_var, wraplength=300).grid(row=11, column=0, columnspan=2,
                                                                                      pady=5)
        # Note: Displays connection status and operation results.

        # Bind standard change to update MCS options dynamically
        self.standard_var.trace("w", self.update_mcs_options)
        # Note: Ensures MCS options reflect the selected standard (WBE or WAX).

    def update_mcs_options(self, *args):
        """
        Updates the MCS dropdown options based on the selected standard.
        - WBE (802.11be): MCS0 to MCS13
        - WAX (802.11ax): MCS0 to MCS11
        """
        standard = self.standard_var.get()
        if standard == "WBE":
            mcs_options = [f"MCS{i}" for i in range(14)]  # 14 options for WBE
        else:  # WAX
            mcs_options = [f"MCS{i}" for i in range(12)]  # 12 options for WAX
        self.mcs_combo["values"] = mcs_options
        if self.mcs_var.get() not in mcs_options:
            self.mcs_var.set(mcs_options[-1])  # Default to highest valid MCS if current is invalid

    def connect(self):
        """Establishes a connection to the signal generator using the provided address."""
        if self.signal_generator is not None:
            messagebox.showwarning("Warning", "Already connected!")  # Prevent multiple connections
            return
        try:
            self.signal_generator = RS_SMX(self.address_var.get(), tmo_s=50)  # Timeout set to 50s
            self.status_var.set(
                f"Connected to {self.signal_generator.model}, Serial: {self.signal_generator.serial_number}")
        except Exception as e:
            self.status_var.set(f"Connection failed: {e}")
            messagebox.showerror("Error", f"Failed to connect: {e}")

    def preset(self):
        """Resets the instrument to a default state."""
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")  # Check connection
            return
        try:
            self.signal_generator.smx_preset()
            self.status_var.set("Instrument preset completed")
        except Exception as e:
            self.status_var.set(f"Preset failed: {e}")
            messagebox.showerror("Error", f"Preset failed: {e}")

    def generate_waveform(self):
        """Generates a WLAN waveform based on input parameters and enables WLAN output."""
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")  # Check connection
            return
        try:
            result = self.signal_generator.create_waveform(
                self.standard_var.get(),
                self.bw_var.get(),
                self.mcs_var.get(),
                self.burst_var.get(),
                self.duty_var.get()
            )
            if result == 0:  # Success
                self.signal_generator.set_frequency(self.freq_var.get())
                self.signal_generator.set_power_level(self.power_var.get())
                self.signal_generator.enable_WLAN()
                self.status_var.set("Waveform generated and WLAN enabled")
            else:  # Failure
                self.status_var.set("Waveform generation failed")
                messagebox.showerror("Error", "Waveform generation failed")
        except Exception as e:
            self.status_var.set(f"Waveform generation failed: {e}")
            messagebox.showerror("Error", f"Waveform generation failed: {e}")

    def enable_output(self):
        """Turns on the RF output of the signal generator."""
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")  # Check connection
            return
        try:
            self.signal_generator.enable_output()
            self.status_var.set("RF output enabled")
        except Exception as e:
            self.status_var.set(f"Enable output failed: {e}")
            messagebox.showerror("Error", f"Enable output failed: {e}")

    def disable_output(self):
        """Turns off the RF output of the signal generator."""
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")  # Check connection
            return
        try:
            self.signal_generator.disable_output()
            self.status_var.set("RF output disabled")
        except Exception as e:
            self.status_var.set(f"Disable output failed: {e}")
            messagebox.showerror("Error", f"Disable output failed: {e}")

    def close(self):
        """Closes the connection to the signal generator."""
        if self.signal_generator is not None:
            try:
                self.signal_generator.close()
                self.signal_generator = None
                self.status_var.set("Disconnected")
            except Exception as e:
                self.status_var.set(f"Close failed: {e}")
                messagebox.showerror("Error", f"Close failed: {e}")
        else:
            self.status_var.set("No active connection to close")  # Nothing to close


# --- Main Execution ---
if __name__ == "__main__":
    """
    Entry point for the script. Creates and runs the GUI application.
    """
    root = tk.Tk()  # Create the main window
    app = RS_SMX_GUI(root)  # Instantiate the GUI class
    root.mainloop()  # Start the GUI event loop