"""Ensure package is importable before any other imports.

This should be imported first to set up the Python path correctly.
"""

import sys
from pathlib import Path

# Get the package root (this file's parent directory)
_PACKAGE_ROOT = Path(__file__).parent.resolve()

# Add to Python path if not already there
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

# Verify we can import the package
try:
    import config
    import vehicle
    import dynamics
    import simulation
    import rules
    import analysis
except ImportError as e:
    raise ImportError(
        f"Failed to import package modules. Package root: {_PACKAGE_ROOT}\n"
        f"Error: {e}\n"
        f"sys.path: {sys.path[:5]}"
    ) from e

