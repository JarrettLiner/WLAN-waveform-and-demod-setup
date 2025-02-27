import tkinter as tk
from tkinter import ttk, messagebox
from RS_FSx_WLAN_AX_BE import RS_FSX_WLAN_AX_BE  # Import your FSW control class
import logging


class RS_FSX_GUI:
    """
    A GUI class to control the Rohde & Schwarz FSW Spectrum Analyzer for WLAN measurements.
    Supports 802.11ax (WAX) and 802.11be (WBE) standards, with synchronization to an SMW signal generator.

    Notes:
    - Requires 'RS_FSX_WLAN_AX_BE.py' with dependencies ('RS_SMx_WLAN_AX_BE.py', 'WLAN_Standards_Translator.py').
    - Use 'Connect' first, then 'Extract Settings from SMW' to view SMW config, or 'Full Setup' for a complete sequence.
    - SMW address is optional; leave blank if not used. Full functionality requires an SMW connection.
    - WLAN standard is automatically retrieved from SMW settings during sync.
    """

    def __init__(self, root):
        # Initialize the GUI window
        self.root = root
        self.root.title("RS_FSX WLAN Measurement Control")
        self.fsw = None

        # Configure logging for detailed feedback
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)

        # Main frame setup
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- Input Fields ---
        ttk.Label(self.main_frame, text="FSW Address:").grid(row=0, column=0, sticky=tk.W)
        self.fsw_address_var = tk.StringVar(value="TCPIP::192.168.200.20::INSTR")
        ttk.Entry(self.main_frame, textvariable=self.fsw_address_var, width=30).grid(row=0, column=1, sticky=tk.W)
        # Note: Enter FSW VISA address (e.g., 'TCPIP::192.168.200.20::INSTR').

        ttk.Label(self.main_frame, text="SMW Address (optional):").grid(row=1, column=0, sticky=tk.W)
        self.smw_address_var = tk.StringVar(value="TCPIP::192.168.200.10::INSTR")
        ttk.Entry(self.main_frame, textvariable=self.smw_address_var, width=30).grid(row=1, column=1, sticky=tk.W)
        # Note: Optional SMW address (e.g., 'TCPIP::192.168.200.10::INSTR'); leave blank if not used.

        # --- Control Buttons ---
        ttk.Button(self.main_frame, text="Connect", command=self.connect).grid(row=2, column=0, pady=5)
        ttk.Button(self.main_frame, text="Extract Settings from SMW", command=self.extract_settings).grid(row=2,
                                                                                                          column=1,
                                                                                                          pady=5)
        ttk.Button(self.main_frame, text="Full Setup", command=self.full_setup).grid(row=3, column=0, pady=5)
        ttk.Button(self.main_frame, text="Auto Level", command=self.auto_level).grid(row=3, column=1, pady=5)
        ttk.Button(self.main_frame, text="Close", command=self.close).grid(row=4, column=0, pady=5)
        # Note: 'Full Setup' runs Preset -> Setup WLAN App -> Sync with SMW -> Auto Level in sequence.

        # --- Status Display ---
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(self.main_frame, textvariable=self.status_var, wraplength=300,
                  font=("Arial", 12, "bold")).grid(row=5, column=0, columnspan=2, pady=5)
        # Note: Displays connection status, operation results, or errors in larger, bold text.

    def connect(self):
        """Connects to the FSW and optionally the SMW."""
        if self.fsw is not None:
            messagebox.showwarning("Warning", "Already connected!")
            return
        try:
            smw_address = self.smw_address_var.get().strip()
            if smw_address:
                self.fsw = RS_FSX_WLAN_AX_BE(self.fsw_address_var.get(), tmo_s=10, smw_resource_id=smw_address)
                self.status_var.set(f"Connected to FSW: {self.fsw.model}, Serial: {self.fsw.serial_number}; "
                                    f"SMW connected")
            else:
                self.fsw = RS_FSX_WLAN_AX_BE(self.fsw_address_var.get(), tmo_s=10)
                self.status_var.set(f"Connected to FSW: {self.fsw.model}, Serial: {self.fsw.serial_number}; "
                                    f"No SMW connection")
            self.logger.info("Connection successful")
        except Exception as e:
            self.status_var.set(f"Connection failed: {e}")
            self.logger.error(f"Connection failed: {e}")
            messagebox.showerror("Error", f"Failed to connect: {e}")

    def extract_settings(self):
        """Extracts and displays settings from the SMW signal generator."""
        if self.fsw is None:
            messagebox.showerror("Error", "Not connected to FSW!")
            return
        if not self.fsw.smw:
            self.status_var.set("No SMW connected; cannot extract settings")
            messagebox.showwarning("Warning", "No SMW connected")
            return
        try:
            settings = self.fsw.extract_settings_from_generator()
            if settings:
                freq_mhz = settings.get("frequency_hz", 0) / 1e6
                standard_desc = self.fsw.translator.to_description(settings.get("standard", "WBE"))
                capture_time_ms = (settings.get("frame_duration_s", 0) + settings.get("idle_time_s", 0)) * 1000
                self.status_var.set(f"SMW Settings: Freq={freq_mhz:.2f} MHz, Standard={standard_desc}, "
                                    f"Frame={settings.get('frame_duration_s', 0) * 1000:.2f} ms, "
                                    f"Idle={settings.get('idle_time_s', 0) * 1000:.2f} ms, "
                                    f"Capture (4x)={capture_time_ms * 4:.2f} ms")
                self.logger.info(f"Extracted SMW settings: {settings}")
            else:
                self.status_var.set("Failed to extract SMW settings")
        except Exception as e:
            self.status_var.set(f"Extract settings failed: {e}")
            self.logger.error(f"Extract settings failed: {e}")
            messagebox.showerror("Error", f"Extract failed: {e}")

    def full_setup(self):
        """Performs a full FSW setup: Preset, Setup WLAN App, Sync with SMW, and Auto Level."""
        if self.fsw is None:
            messagebox.showerror("Error", "Not connected to FSW!")
            return
        try:
            # Step 1: Preset FSW
            self.fsw.FSW_preset()
            self.status_var.set("FSW preset completed")
            self.logger.info("FSW preset completed")

            # Step 2: Setup WLAN App (standard from SMW if connected, else default to WBE)
            settings = self.fsw.extract_settings_from_generator() if self.fsw.smw else {}
            standard = settings.get("standard", "WBE")  # Use SMW standard or default to WBE
            self.fsw.setup_WLAN_app(standard=standard)
            desc = self.fsw.translator.to_description(standard)
            self.status_var.set(f"WLAN app configured for {desc}")
            self.logger.info(f"WLAN app configured for {desc}")

            # Step 3: Sync with SMW (if connected)
            if self.fsw.smw:
                self.fsw.sync_with_smw()
                settings = self.fsw.extract_settings_from_generator()
                freq_mhz = settings.get("frequency_hz", 0) / 1e6
                standard_desc = self.fsw.translator.to_description(settings.get("standard", standard))
                capture_time_ms = 4 * (settings.get("frame_duration_s", 0) + settings.get("idle_time_s", 0)) * 1000
                self.status_var.set(f"Preset done, WLAN={standard_desc}, Synced Freq={freq_mhz:.2f} MHz, "
                                    f"Capture={capture_time_ms:.2f} ms")
                self.logger.info(f"Synchronized with SMW: {settings}")
            else:
                self.status_var.set(f"Preset done, WLAN={desc}, No SMW sync")
                self.logger.warning("No SMW connected; skipping sync")

            # Step 4: Auto Level
            self.fsw.FSW_autolevel()
            self.status_var.set(f"Full setup completed: Preset, WLAN={desc}, "
                                f"{'Synced with SMW, ' if self.fsw.smw else 'No SMW, '}Auto Level done")
            self.logger.info("Auto leveling completed")
        except Exception as e:
            self.status_var.set(f"Full setup failed: {e}")
            self.logger.error(f"Full setup failed: {e}")
            messagebox.showerror("Error", f"Full setup failed: {e}")

    def auto_level(self):
        """Runs auto power leveling on the FSW."""
        if self.fsw is None:
            messagebox.showerror("Error", "Not connected to FSW!")
            return
        try:
            self.fsw.FSW_autolevel()
            self.status_var.set("FSW auto power leveling completed")
            self.logger.info("Auto leveling completed")
        except Exception as e:
            self.status_var.set(f"Auto level failed: {e}")
            self.logger.error(f"Auto level failed: {e}")
            messagebox.showerror("Error", f"Auto level failed: {e}")

    def close(self):
        """Closes the FSW (and SMW) connection."""
        if self.fsw is not None:
            try:
                self.fsw = None  # RS_FSX_WLAN_AX_BE handles SMW closure internally
                self.status_var.set("Disconnected")
                self.logger.info("Connection closed")
            except Exception as e:
                self.status_var.set(f"Close failed: {e}")
                self.logger.error(f"Close failed: {e}")
                messagebox.showerror("Error", f"Close failed: {e}")
        else:
            self.status_var.set("No active connection to close")


if __name__ == "__main__":
    """
    Entry point: Launches the FSW GUI application.
    """
    root = tk.Tk()
    app = RS_FSX_GUI(root)
    root.mainloop()