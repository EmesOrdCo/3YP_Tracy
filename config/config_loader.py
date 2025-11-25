"""Configuration file loader for vehicle parameters."""

import json
import yaml
from pathlib import Path
from typing import Union
import sys

# Import with fallback for both package and development modes
try:
    from .vehicle_config import (
        VehicleConfig, MassProperties, TireProperties, PowertrainProperties,
        AerodynamicsProperties, SuspensionProperties, ControlProperties,
        EnvironmentProperties
    )
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import (
        VehicleConfig, MassProperties, TireProperties, PowertrainProperties,
        AerodynamicsProperties, SuspensionProperties, ControlProperties,
        EnvironmentProperties
    )


def load_config(config_path: Union[str, Path]) -> VehicleConfig:
    """
    Load vehicle configuration from JSON or YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        VehicleConfig object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Load file based on extension
    if config_path.suffix == '.json':
        with open(config_path, 'r') as f:
            data = json.load(f)
    elif config_path.suffix in ['.yaml', '.yml']:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported config file format: {config_path.suffix}")
    
    # Build configuration objects
    mass = MassProperties(**data.get('mass', {}))
    tires = TireProperties(**data.get('tires', {}))
    powertrain = PowertrainProperties(**data.get('powertrain', {}))
    aerodynamics = AerodynamicsProperties(**data.get('aerodynamics', {}))
    suspension = SuspensionProperties(**data.get('suspension', {}))
    control = ControlProperties(**data.get('control', {}))
    environment = EnvironmentProperties(**data.get('environment', {}))
    
    # Simulation parameters
    sim_params = data.get('simulation', {})
    
    config = VehicleConfig(
        mass=mass,
        tires=tires,
        powertrain=powertrain,
        aerodynamics=aerodynamics,
        suspension=suspension,
        control=control,
        environment=environment,
        dt=sim_params.get('dt', 0.001),
        max_time=sim_params.get('max_time', 30.0),
        target_distance=sim_params.get('target_distance', 75.0)
    )
    
    # Validate configuration
    errors = config.validate()
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return config


