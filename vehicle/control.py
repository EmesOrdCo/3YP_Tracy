"""Control strategy model for launch and traction control."""

import numpy as np
from typing import Tuple, Optional
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import ControlProperties
    from ..dynamics.state import SimulationState
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import ControlProperties
    from dynamics.state import SimulationState


class ControlStrategy:
    """Launch and traction control strategy."""
    
    def __init__(self, config: ControlProperties):
        """
        Initialize control strategy.
        
        Args:
            config: Control properties configuration
        """
        self.config = config
        self.launch_torque_limit = config.launch_torque_limit
        self.target_slip_ratio = config.target_slip_ratio
        self.torque_ramp_rate = config.torque_ramp_rate
        self.traction_control_enabled = config.traction_control_enabled
        
        # Internal state for ramp control
        self.current_torque_request = 0.0
        self.previous_slip_ratio = 0.0
    
    def calculate_requested_torque(
        self,
        state: SimulationState,
        normal_force_rear: float,
        max_tire_force: float,
        tire_radius: float,
        dt: float
    ) -> float:
        """
        Calculate requested torque based on control strategy.
        
        Args:
            state: Current simulation state
            normal_force_rear: Rear normal force (N)
            max_tire_force: Maximum tire force capability (N)
            tire_radius: Tire radius (m)
            dt: Time step (s)
            
        Returns:
            Requested torque at wheels (N·m)
        """
        # Calculate current slip ratio
        wheel_velocity = state.wheel_angular_velocity_rear * tire_radius
        vehicle_velocity = state.velocity
        
        if abs(vehicle_velocity) < 0.1:
            if abs(wheel_velocity) > 0.1:
                slip_ratio = 1.0 if wheel_velocity > 0 else -1.0
            else:
                slip_ratio = 0.0
        else:
            slip_ratio = (wheel_velocity - vehicle_velocity) / abs(vehicle_velocity)
        
        slip_ratio = np.clip(slip_ratio, -1.0, 1.0)
        
        # Launch control: ramp torque up from zero
        if state.time < 0.1:  # Initial launch phase
            target_torque = min(
                self.current_torque_request + self.torque_ramp_rate * dt,
                self.launch_torque_limit
            )
        else:
            target_torque = self.launch_torque_limit
        
        # Traction control: reduce torque if slip is too high
        if self.traction_control_enabled:
            if abs(slip_ratio) > self.target_slip_ratio * 1.2:  # 20% margin
                # Reduce torque based on slip error
                slip_error = abs(slip_ratio) - self.target_slip_ratio
                reduction_factor = max(0.5, 1.0 - slip_error / 0.5)  # Reduce up to 50%
                target_torque *= reduction_factor
        
        # Limit by available grip
        max_torque_grip = max_tire_force * tire_radius
        requested_torque = min(target_torque, max_torque_grip)
        
        # Update internal state
        self.current_torque_request = requested_torque
        self.previous_slip_ratio = slip_ratio
        
        return requested_torque
    
    def reset(self):
        """Reset control strategy state (e.g., for new simulation)."""
        self.current_torque_request = 0.0
        self.previous_slip_ratio = 0.0
    
    def calculate_optimal_launch_torque(
        self,
        normal_force_rear: float,
        mu_max: float,
        tire_radius: float
    ) -> float:
        """
        Calculate optimal launch torque based on available grip.
        
        Args:
            normal_force_rear: Rear normal force (N)
            mu_max: Maximum friction coefficient
            tire_radius: Tire radius (m)
            
        Returns:
            Optimal torque at wheels (N·m)
        """
        max_tire_force = mu_max * normal_force_rear
        optimal_torque = max_tire_force * tire_radius
        
        # Apply launch limit
        return min(optimal_torque, self.launch_torque_limit)


class LaunchControl:
    """Simplified launch control for initial acceleration."""
    
    def __init__(self, config: ControlProperties):
        """
        Initialize launch control.
        
        Args:
            config: Control properties configuration
        """
        self.config = config
        self.torque_ramp_rate = config.torque_ramp_rate
        self.launch_torque_limit = config.launch_torque_limit
        
    def get_launch_torque(self, time: float, dt: float) -> float:
        """
        Get launch torque with ramp-up.
        
        Args:
            time: Current simulation time (s)
            dt: Time step (s)
            
        Returns:
            Launch torque at wheels (N·m)
        """
        if time == 0:
            return 0.0
        
        # Ramp up torque gradually
        target_torque = min(
            self.launch_torque_limit,
            self.torque_ramp_rate * time
        )
        
        return target_torque


class TractionControl:
    """Traction control to maintain optimal slip ratio."""
    
    def __init__(self, config: ControlProperties):
        """
        Initialize traction control.
        
        Args:
            config: Control properties configuration
        """
        self.config = config
        self.target_slip_ratio = config.target_slip_ratio
        self.enabled = config.traction_control_enabled
        
        # PID-like parameters (simple implementation)
        self.kp = 100.0  # Proportional gain
        self.kd = 10.0   # Derivative gain
        self.previous_error = 0.0
    
    def calculate_torque_adjustment(
        self,
        current_slip_ratio: float,
        dt: float
    ) -> float:
        """
        Calculate torque adjustment to maintain target slip.
        
        Args:
            current_slip_ratio: Current wheel slip ratio
            dt: Time step (s)
            
        Returns:
            Torque adjustment factor (0.0 to 1.0)
        """
        if not self.enabled:
            return 1.0
        
        # Calculate error
        error = abs(current_slip_ratio) - self.target_slip_ratio
        
        # Simple proportional control
        if error > 0:  # Slip too high
            adjustment = max(0.5, 1.0 - self.kp * error)
        else:  # Slip too low
            adjustment = min(1.0, 1.0 + 0.1 * abs(error))
        
        self.previous_error = error
        
        return adjustment

