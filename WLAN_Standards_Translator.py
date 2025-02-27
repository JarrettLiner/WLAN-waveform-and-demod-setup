from RsInstrument import RsInstrument, RsInstrException
import logging
import time
from RS_SMx_WLAN_AX_BE import RS_SMX


class WLAN_Standards_Translator:
    """Helper class to translate WLAN standards between SMW and FSW formats."""

    STANDARD_MAP = {
        "WAX": (10, "IEEE 802.11ax", ":CONF:STAN 10"),
        "WBE": (11, "IEEE 802.11be", ":CONF:STAN 11"),
        "A": (0, "IEEE 802.11a", ":CONF:STAN 0"),
        "B": (1, "IEEE 802.11b", ":CONF:STAN 1"),
        "J10": (2, "IEEE 802.11j (10 MHz)", ":CONF:STAN 2"),
        "J20": (3, "IEEE 802.11j (20 MHz)", ":CONF:STAN 3"),
        "G": (4, "IEEE 802.11g", ":CONF:STAN 4"),
        "N": (6, "IEEE 802.11n", ":CONF:STAN 6"),
        "N_MIMO": (7, "IEEE 802.11n (MIMO)", ":CONF:STAN 7"),
        "AC": (8, "IEEE 802.11ac", ":CONF:STAN 8"),
        "P": (9, "IEEE 802.11p", ":CONF:STAN 9")
    }

    @staticmethod
    def to_fsw_command(smw_standard: str) -> str:
        """Converts SMW standard to FSW :CONF:STAN command."""
        entry = WLAN_Standards_Translator.STANDARD_MAP.get(smw_standard.upper(), None)
        if entry is None:
            logging.getLogger(__name__).warning(f"Unknown SMW standard '{smw_standard}'. Defaulting to 802.11be.")
            return ":CONF:STAN 11"
        return entry[2]

    @staticmethod
    def to_description(smw_standard: str) -> str:
        """Returns the human-readable description of the standard."""
        entry = WLAN_Standards_Translator.STANDARD_MAP.get(smw_standard.upper(), None)
        return entry[1] if entry else "IEEE 802.11be (default)"