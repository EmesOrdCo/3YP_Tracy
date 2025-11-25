"""Helper module to ensure consistent imports across the codebase.

This module provides a way to import modules that works both when:
- The package is installed (relative imports work)
- Running from source (absolute imports needed)
"""

import sys
from pathlib import Path

# Determine if we're running as an installed package or from source
_PACKAGE_ROOT = Path(__file__).parent.resolve()
_IS_INSTALLED = False

# Check if we're in site-packages or a development install
try:
    import config
    import vehicle
    _IS_INSTALLED = True
except ImportError:
    # Not installed, add to path
    if str(_PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(_PACKAGE_ROOT))

def get_import_path(module_path: str) -> str:
    """
    Get the correct import path for a module.
    
    Args:
        module_path: Relative path like 'config.vehicle_config'
        
    Returns:
        Import path that will work in current context
    """
    return module_path

