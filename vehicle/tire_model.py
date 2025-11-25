"""Tire force model for acceleration simulation."""

import numpy as np
from typing import Tuple
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import TireProperties
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import TireProperties


class TireModel:
    """Tire force model for longitudinal acceleration."""
    
    def __init__(self, config: TireProperties):
        """
        Initialize tire model.
        
        Args:
            config: Tire properties configuration
        """
        self.config = config
        self.radius = config.radius_loaded
        self.mu_max = config.mu_max
        self.mu_slip_optimal = config.mu_slip_optimal
        self.rolling_resistance_coeff = config.rolling_resistance_coeff
    
    def calculate_longitudinal_force(
        self,
        normal_force: float,
        slip_ratio: float,
        velocity: float
    ) -> Tuple[float, float]:
        """
        Calculate longitudinal tire force and rolling resistance.
        
        Args:
            normal_force: Normal force on tire (N)
            slip_ratio: Slip ratio (0 = no slip, 1 = wheel spinning, tire stationary)
            velocity: Vehicle velocity (m/s)
            
        Returns:
            Tuple of (longitudinal_force, rolling_resistance_force) in N
        """
        # Simplified tire model: Fx = μ(λ) * Fz
        # Linear friction model (can upgrade to Pacejka later)
        mu = self._calculate_friction_coefficient(slip_ratio)
        
        # Longitudinal force
        fx = mu * normal_force
        
        # Rolling resistance (proportional to normal force)
        frr = self.rolling_resistance_coeff * normal_force
        
        # Rolling resistance direction (opposes motion)
        if velocity > 0:
            frr = -abs(frr)
        elif velocity < 0:
            frr = abs(frr)
        else:
            frr = 0.0
        
        return fx, frr
    
    def _calculate_friction_coefficient(self, slip_ratio: float) -> float:
        """
        Calculate friction coefficient as function of slip ratio.
        
        Simplified model: linear increase to optimal, then linear decrease.
        Can be replaced with Pacejka model when tire data is available.
        
        Args:
            slip_ratio: Slip ratio (0-1)
            
        Returns:
            Friction coefficient
        """
        slip_ratio = abs(slip_ratio)
        optimal_slip = self.mu_slip_optimal
        
        if slip_ratio <= optimal_slip:
            # Linear increase to optimal
            mu = (self.mu_max / optimal_slip) * slip_ratio
        else:
            # Linear decrease after optimal
            mu = self.mu_max * (1.0 - (slip_ratio - optimal_slip) / (1.0 - optimal_slip))
            mu = max(0.0, mu)  # Don't go negative
        
        return mu
    
    def calculate_slip_ratio(
        self,
        wheel_angular_velocity: float,
        vehicle_velocity: float
    ) -> float:
        """
        Calculate slip ratio from wheel and vehicle velocities.
        
        Args:
            wheel_angular_velocity: Wheel angular velocity (rad/s)
            vehicle_velocity: Vehicle velocity (m/s)
            
        Returns:
            Slip ratio
        """
        wheel_velocity = wheel_angular_velocity * self.radius
        
        if abs(vehicle_velocity) < 0.1:  # Near zero velocity
            if abs(wheel_velocity) > 0.1:
                return 1.0 if wheel_velocity > 0 else -1.0
            else:
                return 0.0
        
        slip = (wheel_velocity - vehicle_velocity) / abs(vehicle_velocity)
        return np.clip(slip, -1.0, 1.0)


