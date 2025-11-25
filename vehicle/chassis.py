"""Chassis geometry model for vehicle dynamics."""

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


class ChassisGeometry:
    """Chassis geometry calculations and parameters."""
    
    def __init__(self, mass_properties: MassProperties):
        """
        Initialize chassis geometry model.
        
        Args:
            mass_properties: Mass properties containing geometry parameters
        """
        self.mass_props = mass_properties
        self.wheelbase = mass_properties.wheelbase
        self.front_track = mass_properties.front_track
        self.rear_track = mass_properties.rear_track
        self.cg_x = mass_properties.cg_x
        self.cg_z = mass_properties.cg_z
    
    def calculate_wheel_positions(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Calculate absolute positions of wheel centers.
        
        Returns:
            Tuple of ((front_left_x, front_left_y), (rear_left_x, rear_left_y))
            Assuming front axle at x=0, rear axle at x=wheelbase
        """
        front_x = 0.0
        rear_x = self.wheelbase
        
        front_y_left = -self.front_track / 2
        front_y_right = self.front_track / 2
        rear_y_left = -self.rear_track / 2
        rear_y_right = self.rear_track / 2
        
        return (
            (front_x, front_y_left, front_x, front_y_right),
            (rear_x, rear_y_left, rear_x, rear_y_right)
        )
    
    def calculate_cg_location(self) -> Tuple[float, float, float]:
        """
        Calculate center of gravity location.
        
        Returns:
            Tuple of (cg_x, cg_y, cg_z) in meters
            Assuming symmetric vehicle, cg_y = 0
        """
        return (self.cg_x, 0.0, self.cg_z)
    
    def calculate_wheelbase_ratio(self) -> float:
        """
        Calculate ratio of CG distance to front axle over wheelbase.
        
        Returns:
            Ratio (0 = at front axle, 1 = at rear axle)
        """
        return self.cg_x / self.wheelbase if self.wheelbase > 0 else 0.5
    
    def calculate_track_width_average(self) -> float:
        """
        Calculate average track width.
        
        Returns:
            Average of front and rear track widths
        """
        return (self.front_track + self.rear_track) / 2.0
    
    def calculate_track_aspect_ratio(self) -> float:
        """
        Calculate aspect ratio of vehicle (wheelbase / average track).
        
        Returns:
            Aspect ratio
        """
        avg_track = self.calculate_track_width_average()
        return self.wheelbase / avg_track if avg_track > 0 else 0.0

