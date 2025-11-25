"""Suspension model for load transfer and geometry effects."""

import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import SuspensionProperties
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import SuspensionProperties


class SuspensionModel:
    """Suspension geometry and load transfer model."""
    
    def __init__(self, config: SuspensionProperties):
        """
        Initialize suspension model.
        
        Args:
            config: Suspension properties configuration
        """
        self.config = config
        self.anti_squat_ratio = config.anti_squat_ratio
        self.ride_height_front = config.ride_height_front
        self.ride_height_rear = config.ride_height_rear
    
    def calculate_anti_squat_effect(
        self,
        longitudinal_acceleration: float,
        normal_force_rear: float
    ) -> float:
        """
        Calculate anti-squat effect on rear axle.
        
        Simplified model - full implementation would consider instant center geometry.
        
        Args:
            longitudinal_acceleration: Longitudinal acceleration (m/s²)
            normal_force_rear: Rear normal force (N)
            
        Returns:
            Additional normal force due to anti-squat (N)
        """
        # Anti-squat reduces load transfer during acceleration
        # This is a simplified model - full implementation requires geometry
        if self.anti_squat_ratio > 0:
            # Anti-squat reduces rear load transfer
            anti_squat_force = normal_force_rear * self.anti_squat_ratio * 0.1
            return anti_squat_force
        return 0.0


