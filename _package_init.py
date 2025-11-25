"""Package initialization helper to ensure imports work correctly.

This module ensures that the package can be imported correctly whether:
1. Installed via pip install -e .
2. Run directly from source
3. Imported from other locations
"""

import sys
from pathlib import Path

# Get the package root directory
_PACKAGE_ROOT = Path(__file__).parent.resolve()

# Add to sys.path if not already there (for development mode)
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

# Verify package structure
_REQUIRED_DIRS = ['config', 'vehicle', 'dynamics', 'simulation', 'rules', 'analysis']
_missing_dirs = [d for d in _REQUIRED_DIRS if not (_PACKAGE_ROOT / d).is_dir()]

if _missing_dirs:
    raise ImportError(
        f"Package structure incomplete. Missing directories: {_missing_dirs}\n"
        f"Package root: {_PACKAGE_ROOT}"
    )

