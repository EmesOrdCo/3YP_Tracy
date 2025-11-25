"""Mass properties model for vehicle dynamics."""

import numpy as np
from typing import Tuple
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import MassProperties
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import MassProperties


class MassPropertiesModel:
    """Mass properties and geometry calculations."""
    
    def __init__(self, config: MassProperties):
        """
        Initialize mass properties model.
        
        Args:
            config: Mass properties configuration
        """
        self.config = config
        self.mass = config.total_mass
        self.cg_x = config.cg_x
        self.cg_z = config.cg_z
        self.wheelbase = config.wheelbase
        self.front_track = config.front_track
        self.rear_track = config.rear_track
    
    def calculate_static_load_distribution(self) -> Tuple[float, float]:
        """
        Calculate static load distribution.
        
        Returns:
            Tuple of (front_normal_force, rear_normal_force) in N
        """
        g = 9.81  # m/s²
        total_weight = self.mass * g
        
        # Distance from CG to rear axle
        a = self.cg_x
        # Distance from CG to front axle
        b = self.wheelbase - self.cg_x
        
        # Load distribution (assuming level ground)
        front_load = total_weight * (b / self.wheelbase)
        rear_load = total_weight * (a / self.wheelbase)
        
        return front_load, rear_load
    
    def calculate_load_transfer(
        self,
        longitudinal_acceleration: float
    ) -> Tuple[float, float]:
        """
        Calculate longitudinal load transfer.
        
        Args:
            longitudinal_acceleration: Longitudinal acceleration (m/s²)
            
        Returns:
            Tuple of (front_load_transfer, rear_load_transfer) in N
            Positive = load increases, negative = load decreases
        """
        # Load transfer due to longitudinal acceleration
        # ΔFz = (m * a * h_cg) / wheelbase
        load_transfer = (self.mass * longitudinal_acceleration * self.cg_z) / self.wheelbase
        
        # Front loses load, rear gains load (during acceleration)
        front_transfer = -load_transfer
        rear_transfer = load_transfer
        
        return front_transfer, rear_transfer
    
    def calculate_normal_forces(
        self,
        longitudinal_acceleration: float,
        front_downforce: float = 0.0,
        rear_downforce: float = 0.0
    ) -> Tuple[float, float]:
        """
        Calculate total normal forces on front and rear axles.
        
        Args:
            longitudinal_acceleration: Longitudinal acceleration (m/s²)
            front_downforce: Aerodynamic downforce on front (N)
            rear_downforce: Aerodynamic downforce on rear (N)
            
        Returns:
            Tuple of (front_normal_force, rear_normal_force) in N
        """
        # Static load
        front_static, rear_static = self.calculate_static_load_distribution()
        
        # Load transfer
        front_transfer, rear_transfer = self.calculate_load_transfer(longitudinal_acceleration)
        
        # Total normal forces
        front_normal = front_static + front_transfer + front_downforce
        rear_normal = rear_static + rear_transfer + rear_downforce
        
        # Ensure forces are positive (vehicle can't lift off ground in this model)
        front_normal = max(0.0, front_normal)
        rear_normal = max(0.0, rear_normal)
        
        return front_normal, rear_normal

