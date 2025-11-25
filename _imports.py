"""Centralized import utility for handling package imports.

This module provides utilities to ensure imports work correctly whether:
- Package is installed via pip
- Running from source directly
- Running as a script or module
"""

import sys
from pathlib import Path
from typing import Any

# Cache for package root
_PACKAGE_ROOT = None

def get_package_root() -> Path:
    """Get the package root directory."""
    global _PACKAGE_ROOT
    if _PACKAGE_ROOT is None:
        # This file should be at the package root
        _PACKAGE_ROOT = Path(__file__).parent.resolve()
        # Ensure it's in sys.path
        if str(_PACKAGE_ROOT) not in sys.path:
            sys.path.insert(0, str(_PACKAGE_ROOT))
    return _PACKAGE_ROOT

def import_with_fallback(module_path: str, item_name: str = None, relative_level: int = 1):
    """
    Import a module or item with fallback from relative to absolute imports.
    
    Args:
        module_path: Module path, e.g., 'config.vehicle_config' or '..config.vehicle_config'
        item_name: Optional item to import from module, e.g., 'VehicleConfig'
        relative_level: Number of parent directories for relative import (1 = .., 2 = ...)
        
    Returns:
        Imported module or item
    """
    package_root = get_package_root()
    
    # Try relative import first (works when installed as package)
    try:
        if module_path.startswith('..'):
            # Relative import
            # Calculate the relative level
            dots = len(module_path) - len(module_path.lstrip('.'))
            module_path_clean = module_path.lstrip('.')
            
            # Try relative import
            if dots == 1:
                # One level up
                caller_file = Path(sys._getframe(2).f_code.co_filename)
                caller_dir = caller_file.parent
                parent_package = caller_dir.parent.name
                full_path = f"{parent_package}.{module_path_clean}"
            elif dots == 2:
                # Two levels up  
                caller_file = Path(sys._getframe(2).f_code.co_filename)
                caller_dir = caller_file.parent
                grandparent_package = caller_dir.parent.parent.name
                full_path = f"{grandparent_package}.{module_path_clean}"
            else:
                full_path = module_path_clean
            
            module = __import__(full_path, fromlist=[item_name] if item_name else [])
        else:
            module = __import__(module_path, fromlist=[item_name] if item_name else [])
        
        if item_name:
            return getattr(module, item_name)
        return module
        
    except (ImportError, ValueError, AttributeError):
        # Fall back to absolute import
        if module_path.startswith('..'):
            # Convert relative to absolute
            module_path_clean = module_path.lstrip('.')
        else:
            module_path_clean = module_path
        
        # Ensure package root is in path
        if str(package_root) not in sys.path:
            sys.path.insert(0, str(package_root))
        
        # Import absolutely
        module = __import__(module_path_clean, fromlist=[item_name] if item_name else [])
        if item_name:
            return getattr(module, item_name)
        return module

