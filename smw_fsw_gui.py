import tkinter as tk
from tkinter import ttk, messagebox
from RS_SMx_WLAN_AX_BE import RS_SMX
from RS_FSx_WLAN_AX_BE import RS_FSX_WLAN_AX_BE
import logging

class CombinedSMWFSWGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SMW & FSW WLAN Control")
        self.smw = None
        self.fsw = None

        # Configure logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

        # Main notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True)

        # SMW Tab
        self.smw_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.smw_tab, text="SMW Setup")
        self.setup_smw_tab()

        # FSW Tab
        self.fsw_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.fsw_tab, text="FSW Demodulation")
        self.setup_fsw_tab()

        # Status bar (shared across tabs)
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(root, textvariable=self.status_var, wraplength=400, font=("Arial", 12, "bold")).pack(pady=5)

    # --- SMW Tab Setup ---
    def setup_smw_tab(self):
        frame = ttk.Frame(self.smw_tab, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Instrument Address
        ttk.Label(frame, text="SMW Address:").grid(row=0, column=0, sticky=tk.W)
        self.smw_address_var = tk.StringVar(value="TCPIP::192.168.200.10::hislip0")
        ttk.Entry(frame, textvariable=self.smw_address_var, width=30).grid(row=0, column=1, sticky=tk.W)

        # Standard
        ttk.Label(frame, text="Standard:").grid(row=1, column=0, sticky=tk.W)
        self.standard_var = tk.StringVar(value="WBE")
        ttk.Combobox(frame, textvariable=self.standard_var, values=["WBE", "WAX"], state="readonly").grid(row=1, column=1, sticky=tk.W)

        # Bandwidth
        ttk.Label(frame, text="Bandwidth:").grid(row=2, column=0, sticky=tk.W)
        self.bw_var = tk.StringVar(value="BW320")
        ttk.Combobox(frame, textvariable=self.bw_var, values=["BW20", "BW40", "BW80", "BW160", "BW320"], state="readonly").grid(row=2, column=1, sticky=tk.W)

        # MCS
        ttk.Label(frame, text="MCS:").grid(row=3, column=0, sticky=tk.W)
        self.mcs_var = tk.StringVar(value="MCS13")
        self.mcs_combo = ttk.Combobox(frame, textvariable=self.mcs_var, state="readonly")
        self.mcs_combo.grid(row=3, column=1, sticky=tk.W)
        self.update_mcs_options()
        self.standard_var.trace("w", self.update_mcs_options)

        # Burst Length
        ttk.Label(frame, text="Burst Length (s):").grid(row=4, column=0, sticky=tk.W)
        self.burst_var = tk.DoubleVar(value=0.004)
        ttk.Entry(frame, textvariable=self.burst_var, width=10).grid(row=4, column=1, sticky=tk.W)

        # Duty Cycle
        ttk.Label(frame, text="Duty Cycle (0-1):").grid(row=5, column=0, sticky=tk.W)
        self.duty_var = tk.DoubleVar(value=0.5)
        ttk.Entry(frame, textvariable=self.duty_var, width=10).grid(row=5, column=1, sticky=tk.W)

        # Frequency
        ttk.Label(frame, text="Frequency (Hz):").grid(row=6, column=0, sticky=tk.W)
        self.freq_var = tk.DoubleVar(value=6e9)
        ttk.Entry(frame, textvariable=self.freq_var, width=15).grid(row=6, column=1, sticky=tk.W)

        # Power Level
        ttk.Label(frame, text="Power Level (dBm):").grid(row=7, column=0, sticky=tk.W)
        self.power_var = tk.DoubleVar(value=-10)
        ttk.Entry(frame, textvariable=self.power_var, width=10).grid(row=7, column=1, sticky=tk.W)

        # Buttons
        ttk.Button(frame, text="Connect SMW", command=self.connect_smw).grid(row=8, column=0, pady=5)
        ttk.Button(frame, text="Preset", command=self.preset_smw).grid(row=8, column=1, pady=5)
        ttk.Button(frame, text="Generate Waveform", command=self.generate_waveform).grid(row=9, column=0, pady=5)
        ttk.Button(frame, text="Enable Output", command=self.enable_smw_output).grid(row=9, column=1, pady=5)
        ttk.Button(frame, text="Disable Output", command=self.disable_smw_output).grid(row=10, column=0, pady=5)

    # --- FSW Tab Setup ---
    def setup_fsw_tab(self):
        frame = ttk.Frame(self.fsw_tab, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # FSW Address
        ttk.Label(frame, text="FSW Address:").grid(row=0, column=0, sticky=tk.W)
        self.fsw_address_var = tk.StringVar(value="TCPIP::192.168.200.20::INSTR")
        ttk.Entry(frame, textvariable=self.fsw_address_var, width=30).grid(row=0, column=1, sticky=tk.W)

        # Buttons
        ttk.Button(frame, text="Connect FSW", command=self.connect_fsw).grid(row=1, column=0, pady=5)
        ttk.Button(frame, text="Extract Settings from SMW", command=self.extract_settings).grid(row=1, column=1, pady=5)
        ttk.Button(frame, text="Full Setup", command=self.full_setup).grid(row=2, column=0, pady=5)
        ttk.Button(frame, text="Auto Level", command=self.auto_level).grid(row=2, column=1, pady=5)

    # --- SMW Methods ---
    def connect_smw(self):
        if self.smw is not None:
            messagebox.showwarning("Warning", "SMW already connected!")
            return
        try:
            self.smw = RS_SMX(self.smw_address_var.get(), tmo_s=50)
            self.status_var.set(f"SMW Connected: {self.smw.model}, Serial: {self.smw.serial_number}")
            if self.fsw and not self.fsw.smw:
                self.fsw.smw = self.smw  # Share SMW instance with FSW if connected
        except Exception as e:
            self.status_var.set(f"SMW Connection failed: {e}")
            messagebox.showerror("Error", f"SMW Connection failed: {e}")

    def preset_smw(self):
        if self.smw is None:
            messagebox.showerror("Error", "SMW not connected!")
            return
        try:
            self.smw.smx_preset()
            self.status_var.set("SMW preset completed")
        except Exception as e:
            self.status_var.set(f"SMW Preset failed: {e}")
            messagebox.showerror("Error", f"SMW Preset failed: {e}")

    def generate_waveform(self):
        if self.smw is None:
            messagebox.showerror("Error", "SMW not connected!")
            return
        try:
            result = self.smw.create_waveform(
                self.standard_var.get(),
                self.bw_var.get(),
                self.mcs_var.get(),
                self.burst_var.get(),
                self.duty_var.get()
            )
            if result == 0:
                self.smw.set_frequency(self.freq_var.get())
                self.smw.set_power_level(self.power_var.get())
                self.smw.enable_WLAN()
                self.status_var.set("SMW Waveform generated and WLAN enabled")
            else:
                self.status_var.set("SMW Waveform generation failed")
                messagebox.showerror("Error", "SMW Waveform generation failed")
        except Exception as e:
            self.status_var.set(f"SMW Waveform generation failed: {e}")
            messagebox.showerror("Error", f"SMW Waveform generation failed: {e}")

    def enable_smw_output(self):
        if self.smw is None:
            messagebox.showerror("Error", "SMW not connected!")
            return
        try:
            self.smw.enable_output()
            self.status_var.set("SMW RF output enabled")
        except Exception as e:
            self.status_var.set(f"SMW Enable output failed: {e}")
            messagebox.showerror("Error", f"SMW Enable output failed: {e}")

    def disable_smw_output(self):
        if self.smw is None:
            messagebox.showerror("Error", "SMW not connected!")
            return
        try:
            self.smw.disable_output()
            self.status_var.set("SMW RF output disabled")
        except Exception as e:
            self.status_var.set(f"SMW Disable output failed: {e}")
            messagebox.showerror("Error", f"SMW Disable output failed: {e}")

    def update_mcs_options(self, *args):
        standard = self.standard_var.get()
        mcs_options = [f"MCS{i}" for i in range(14 if standard == "WBE" else 12)]
        self.mcs_combo["values"] = mcs_options
        if self.mcs_var.get() not in mcs_options:
            self.mcs_var.set(mcs_options[-1])

    # --- FSW Methods ---
    def connect_fsw(self):
        if self.fsw is not None:
            messagebox.showwarning("Warning", "FSW already connected!")
            return
        try:
            self.fsw = RS_FSX_WLAN_AX_BE(self.fsw_address_var.get(), tmo_s=10, smw_resource_id=None)
            if self.smw:
                self.fsw.smw = self.smw  # Share existing SMW instance
            status = f"FSW Connected: {self.fsw.model}, Serial: {self.fsw.serial_number}"
            if self.smw:
                status += "; SMW linked"
            self.status_var.set(status)
        except Exception as e:
            self.status_var.set(f"FSW Connection failed: {e}")
            messagebox.showerror("Error", f"FSW Connection failed: {e}")

    def extract_settings(self):
        if self.fsw is None:
            messagebox.showerror("Error", "FSW not connected!")
            return
        if not self.fsw.smw:
            self.status_var.set("No SMW linked; cannot extract settings")
            messagebox.showwarning("Warning", "No SMW linked")
            return
        try:
            settings = self.fsw.extract_settings_from_generator()
            if settings:
                freq_mhz = settings.get("frequency_hz", 0) / 1e6
                standard_desc = self.fsw.translator.to_description(settings.get("standard", "WBE"))
                capture_time_ms = (settings.get("frame_duration_s", 0) + settings.get("idle_time_s", 0)) * 1000 * 4
                self.status_var.set(f"SMW Settings: Freq={freq_mhz:.2f} MHz, Standard={standard_desc}, Capture={capture_time_ms:.2f} ms")
            else:
                self.status_var.set("Failed to extract SMW settings")
        except Exception as e:
            self.status_var.set(f"Extract settings failed: {e}")
            messagebox.showerror("Error", f"Extract failed: {e}")

    def full_setup(self):
        if self.fsw is None:
            messagebox.showerror("Error", "FSW not connected!")
            return
        try:
            self.fsw.FSW_preset()
            settings = self.fsw.extract_settings_from_generator() if self.fsw.smw else {}
            standard = settings.get("standard", "WBE")
            self.fsw.setup_WLAN_app(standard=standard)
            if self.fsw.smw:
                self.fsw.sync_with_smw()
            self.fsw.FSW_autolevel()
            desc = self.fsw.translator.to_description(standard)
            self.status_var.set(f"FSW Full setup completed: WLAN={desc}, {'Synced with SMW' if self.fsw.smw else 'No SMW'}")
        except Exception as e:
            self.status_var.set(f"FSW Full setup failed: {e}")
            messagebox.showerror("Error", f"FSW Full setup failed: {e}")

    def auto_level(self):
        if self.fsw is None:
            messagebox.showerror("Error", "FSW not connected!")
            return
        try:
            self.fsw.FSW_autolevel()
            self.status_var.set("FSW Auto power leveling completed")
        except Exception as e:
            self.status_var.set(f"FSW Auto level failed: {e}")
            messagebox.showerror("Error", f"FSW Auto level failed: {e}")

    # --- Cleanup ---
    def on_closing(self):
        if self.smw:
            self.smw.close()
        if self.fsw:
            self.fsw = None  # RS_FSX_WLAN_AX_BE closes SMW internally if it owns it
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CombinedSMWFSWGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()