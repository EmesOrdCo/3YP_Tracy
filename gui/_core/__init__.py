"""Shared plumbing for the Streamlit GUI."""

from pathlib import Path
import sys

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

PACKAGE_ROOT = _PACKAGE_ROOT
CONFIG_DIR = _PACKAGE_ROOT / "config" / "vehicle_configs"
