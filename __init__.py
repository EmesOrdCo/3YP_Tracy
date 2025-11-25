"""Formula Student Acceleration Simulation System."""

__version__ = "1.0.0"

# Initialize package paths
from pathlib import Path
import sys

_PACKAGE_ROOT = Path(__file__).parent.resolve()
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

# Export common imports for convenience
try:
    from config.config_loader import load_config
    from config.vehicle_config import VehicleConfig
    from simulation.acceleration_sim import AccelerationSimulation
    __all__ = ['load_config', 'VehicleConfig', 'AccelerationSimulation', '__version__']
except ImportError:
    # If imports fail, at least export version
    __all__ = ['__version__']

