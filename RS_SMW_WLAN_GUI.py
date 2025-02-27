import tkinter as tk
from tkinter import ttk, messagebox
from RS_SMx_WLAN_AX_BE import RS_SMX  # Assuming your RS_SMX class is in RS_SMX.py
import logging

class RS_SMX_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RS_SMX Waveform Generator Control")
        self.signal_generator = None

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Instrument Address
        ttk.Label(self.main_frame, text="Instrument Address:").grid(row=0, column=0, sticky=tk.W)
        self.address_var = tk.StringVar(value="TCPIP::192.168.200.10::hislip0")
        ttk.Entry(self.main_frame, textvariable=self.address_var, width=30).grid(row=0, column=1, sticky=tk.W)

        # Standard
        ttk.Label(self.main_frame, text="Standard:").grid(row=1, column=0, sticky=tk.W)
        self.standard_var = tk.StringVar(value="WBE")
        ttk.Combobox(self.main_frame, textvariable=self.standard_var, values=["WBE", "WAX"], state="readonly").grid(row=1, column=1, sticky=tk.W)

        # Bandwidth
        ttk.Label(self.main_frame, text="Bandwidth:").grid(row=2, column=0, sticky=tk.W)
        self.bw_var = tk.StringVar(value="BW320")
        ttk.Combobox(self.main_frame, textvariable=self.bw_var, values=["BW20", "BW40", "BW80", "BW160", "BW320"], state="readonly").grid(row=2, column=1, sticky=tk.W)

        # MCS
        ttk.Label(self.main_frame, text="MCS:").grid(row=3, column=0, sticky=tk.W)
        self.mcs_var = tk.StringVar(value="MCS13")
        self.mcs_combo = ttk.Combobox(self.main_frame, textvariable=self.mcs_var, state="readonly")
        self.mcs_combo.grid(row=3, column=1, sticky=tk.W)
        self.update_mcs_options()

        # Burst Length
        ttk.Label(self.main_frame, text="Burst Length (s):").grid(row=4, column=0, sticky=tk.W)
        self.burst_var = tk.DoubleVar(value=0.004)
        ttk.Entry(self.main_frame, textvariable=self.burst_var, width=10).grid(row=4, column=1, sticky=tk.W)

        # Duty Cycle
        ttk.Label(self.main_frame, text="Duty Cycle (0-1):").grid(row=5, column=0, sticky=tk.W)
        self.duty_var = tk.DoubleVar(value=0.5)
        ttk.Entry(self.main_frame, textvariable=self.duty_var, width=10).grid(row=5, column=1, sticky=tk.W)

        # Frequency
        ttk.Label(self.main_frame, text="Frequency (Hz):").grid(row=6, column=0, sticky=tk.W)
        self.freq_var = tk.DoubleVar(value=6e9)
        ttk.Entry(self.main_frame, textvariable=self.freq_var, width=15).grid(row=6, column=1, sticky=tk.W)

        # Power Level
        ttk.Label(self.main_frame, text="Power Level (dBm):").grid(row=7, column=0, sticky=tk.W)
        self.power_var = tk.DoubleVar(value=-10)
        ttk.Entry(self.main_frame, textvariable=self.power_var, width=10).grid(row=7, column=1, sticky=tk.W)

        # Buttons
        ttk.Button(self.main_frame, text="Connect", command=self.connect).grid(row=8, column=0, pady=5)
        ttk.Button(self.main_frame, text="Preset", command=self.preset).grid(row=8, column=1, pady=5)
        ttk.Button(self.main_frame, text="Generate Waveform", command=self.generate_waveform).grid(row=9, column=0, pady=5)
        ttk.Button(self.main_frame, text="Enable Output", command=self.enable_output).grid(row=9, column=1, pady=5)
        ttk.Button(self.main_frame, text="Disable Output", command=self.disable_output).grid(row=10, column=0, pady=5)
        ttk.Button(self.main_frame, text="Close", command=self.close).grid(row=10, column=1, pady=5)

        # Status Label
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(self.main_frame, textvariable=self.status_var, wraplength=300).grid(row=11, column=0, columnspan=2, pady=5)

        # Bind standard change to update MCS options
        self.standard_var.trace("w", self.update_mcs_options)

    def update_mcs_options(self, *args):
        standard = self.standard_var.get()
        if standard == "WBE":
            mcs_options = [f"MCS{i}" for i in range(14)]  # MCS0 to MCS13
        else:  # WAX
            mcs_options = [f"MCS{i}" for i in range(12)]  # MCS0 to MCS11
        self.mcs_combo["values"] = mcs_options
        if self.mcs_var.get() not in mcs_options:
            self.mcs_var.set(mcs_options[-1])  # Set to highest available if current is invalid

    def connect(self):
        if self.signal_generator is not None:
            messagebox.showwarning("Warning", "Already connected!")
            return
        try:
            self.signal_generator = RS_SMX(self.address_var.get(), tmo_s=50)
            self.status_var.set(f"Connected to {self.signal_generator.model}, Serial: {self.signal_generator.serial_number}")
        except Exception as e:
            self.status_var.set(f"Connection failed: {e}")
            messagebox.showerror("Error", f"Failed to connect: {e}")

    def preset(self):
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")
            return
        try:
            self.signal_generator.smx_preset()
            self.status_var.set("Instrument preset completed")
        except Exception as e:
            self.status_var.set(f"Preset failed: {e}")
            messagebox.showerror("Error", f"Preset failed: {e}")

    def generate_waveform(self):
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")
            return
        try:
            result = self.signal_generator.create_waveform(
                self.standard_var.get(),
                self.bw_var.get(),
                self.mcs_var.get(),
                self.burst_var.get(),
                self.duty_var.get()
            )
            if result == 0:
                self.signal_generator.set_frequency(self.freq_var.get())
                self.signal_generator.set_power_level(self.power_var.get())
                self.signal_generator.enable_WLAN()
                self.status_var.set("Waveform generated and WLAN enabled")
            else:
                self.status_var.set("Waveform generation failed")
                messagebox.showerror("Error", "Waveform generation failed")
        except Exception as e:
            self.status_var.set(f"Waveform generation failed: {e}")
            messagebox.showerror("Error", f"Waveform generation failed: {e}")

    def enable_output(self):
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")
            return
        try:
            self.signal_generator.enable_output()
            self.status_var.set("RF output enabled")
        except Exception as e:
            self.status_var.set(f"Enable output failed: {e}")
            messagebox.showerror("Error", f"Enable output failed: {e}")

    def disable_output(self):
        if self.signal_generator is None:
            messagebox.showerror("Error", "Not connected to an instrument!")
            return
        try:
            self.signal_generator.disable_output()
            self.status_var.set("RF output disabled")
        except Exception as e:
            self.status_var.set(f"Disable output failed: {e}")
            messagebox.showerror("Error", f"Disable output failed: {e}")

    def close(self):
        if self.signal_generator is not None:
            try:
                self.signal_generator.close()
                self.signal_generator = None
                self.status_var.set("Disconnected")
            except Exception as e:
                self.status_var.set(f"Close failed: {e}")
                messagebox.showerror("Error", f"Close failed: {e}")
        else:
            self.status_var.set("No active connection to close")

if __name__ == "__main__":
    root = tk.Tk()
    app = RS_SMX_GUI(root)
    root.mainloop()