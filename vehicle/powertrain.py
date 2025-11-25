"""Powertrain model for acceleration simulation."""

import numpy as np
from typing import Tuple
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import PowertrainProperties
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import PowertrainProperties


class PowertrainModel:
    """Powertrain model including motor, battery, and drivetrain."""
    
    def __init__(self, config: PowertrainProperties):
        """
        Initialize powertrain model.
        
        Args:
            config: Powertrain properties configuration
        """
        self.config = config
        self.max_power = config.max_power_accumulator_outlet
        self.motor_kt = config.motor_torque_constant
        self.motor_max_current = config.motor_max_current
        self.motor_max_speed = config.motor_max_speed
        self.motor_efficiency = config.motor_efficiency
        self.battery_voltage = config.battery_voltage_nominal
        self.battery_resistance = config.battery_internal_resistance
        self.gear_ratio = config.gear_ratio
        self.drivetrain_efficiency = config.drivetrain_efficiency
        self.wheel_inertia = config.wheel_inertia
    
    def calculate_torque(
        self,
        requested_torque: float,
        motor_speed: float,
        vehicle_velocity: float
    ) -> Tuple[float, float, float]:
        """
        Calculate available motor torque considering limits and power constraints.
        
        Args:
            requested_torque: Requested torque at wheels (N·m)
            motor_speed: Motor angular velocity (rad/s)
            vehicle_velocity: Vehicle velocity (m/s)
            
        Returns:
            Tuple of (wheel_torque, motor_current, power_consumed)
            - wheel_torque: Actual torque at wheels (N·m)
            - motor_current: Motor current (A)
            - power_consumed: Power consumed at accumulator outlet (W)
        """
        # Convert wheel torque to motor torque
        motor_torque_requested = requested_torque / (self.gear_ratio * self.drivetrain_efficiency)
        
        # Limit by motor current
        max_motor_torque_current = self.motor_kt * self.motor_max_current
        motor_torque = np.clip(motor_torque_requested, -max_motor_torque_current, max_motor_torque_current)
        
        # Limit by motor speed (simplified - no field weakening)
        if abs(motor_speed) > self.motor_max_speed:
            motor_torque = 0.0
        
        # Calculate motor current
        motor_current = motor_torque / self.motor_kt if self.motor_kt > 0 else 0.0
        
        # Calculate power at motor (electrical input)
        motor_power = self.battery_voltage * motor_current
        
        # Account for motor efficiency
        if motor_power > 0:  # Motoring
            electrical_power = motor_power / self.motor_efficiency
        else:  # Regenerating
            electrical_power = motor_power * self.motor_efficiency
        
        # Apply power limit at accumulator outlet (EV 2.2)
        if electrical_power > self.max_power:
            # Scale back torque to meet power limit
            scale_factor = self.max_power / electrical_power
            motor_torque *= scale_factor
            motor_current *= scale_factor
            electrical_power = self.max_power
        elif electrical_power < -self.max_power:
            # Limit regeneration power
            scale_factor = -self.max_power / electrical_power
            motor_torque *= scale_factor
            motor_current *= scale_factor
            electrical_power = -self.max_power
        
        # Convert back to wheel torque
        wheel_torque = motor_torque * self.gear_ratio * self.drivetrain_efficiency
        
        return wheel_torque, motor_current, electrical_power
    
    def calculate_motor_speed(self, wheel_angular_velocity: float) -> float:
        """
        Calculate motor speed from wheel speed.
        
        Args:
            wheel_angular_velocity: Wheel angular velocity (rad/s)
            
        Returns:
            Motor angular velocity (rad/s)
        """
        return wheel_angular_velocity * self.gear_ratio
    
    def calculate_wheel_speed(self, motor_speed: float) -> float:
        """
        Calculate wheel speed from motor speed.
        
        Args:
            motor_speed: Motor angular velocity (rad/s)
            
        Returns:
            Wheel angular velocity (rad/s)
        """
        return motor_speed / self.gear_ratio


