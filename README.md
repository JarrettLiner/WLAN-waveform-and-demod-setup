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

