"""Aerodynamic force model for acceleration simulation."""

import numpy as np
from typing import Tuple
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import AerodynamicsProperties
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import AerodynamicsProperties


class AerodynamicsModel:
    """Aerodynamic drag and downforce model."""
    
    def __init__(self, config: AerodynamicsProperties):
        """
        Initialize aerodynamics model.
        
        Args:
            config: Aerodynamics properties configuration
        """
        self.config = config
        self.cda = config.cda
        self.cl_front = config.cl_front
        self.cl_rear = config.cl_rear
        self.air_density = config.air_density
    
    def calculate_forces(self, velocity: float) -> Tuple[float, float, float]:
        """
        Calculate aerodynamic drag and downforce.
        
        Args:
            velocity: Vehicle velocity (m/s)
            
        Returns:
            Tuple of (drag_force, downforce_front, downforce_rear) in N
        """
        # Dynamic pressure
        q = 0.5 * self.air_density * velocity ** 2
        
        # Drag force (opposes motion)
        drag_force = -self.cda * q * np.sign(velocity) if velocity != 0 else 0.0
        
        # Downforce (negative lift)
        # Simple model: downforce proportional to velocity squared
        # More complex models can include ride height effects, etc.
        downforce_front = -self.cl_front * q  # Negative = down
        downforce_rear = -self.cl_rear * q
        
        return drag_force, downforce_front, downforce_rear

