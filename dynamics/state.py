"""Simulation state management."""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SimulationState:
    """State vector for acceleration simulation."""
    # Position and velocity
    position: float = 0.0  # m
    velocity: float = 0.0  # m/s
    acceleration: float = 0.0  # m/s²
    
    # Wheel states
    wheel_angular_velocity_front: float = 0.0  # rad/s
    wheel_angular_velocity_rear: float = 0.0  # rad/s
    
    # Motor state
    motor_speed: float = 0.0  # rad/s
    motor_current: float = 0.0  # A
    motor_torque: float = 0.0  # N·m
    
    # Forces
    drive_force: float = 0.0  # N
    drag_force: float = 0.0  # N
    rolling_resistance: float = 0.0  # N
    
    # Normal forces
    normal_force_front: float = 0.0  # N
    normal_force_rear: float = 0.0  # N
    
    # Tire forces
    tire_force_front: float = 0.0  # N
    tire_force_rear: float = 0.0  # N
    
    # Power
    power_consumed: float = 0.0  # W
    
    # Time
    time: float = 0.0  # s
    
    def to_dict(self) -> Dict:
        """Convert state to dictionary for logging."""
        return {
            'time': self.time,
            'position': self.position,
            'velocity': self.velocity,
            'acceleration': self.acceleration,
            'wheel_speed_front': self.wheel_angular_velocity_front,
            'wheel_speed_rear': self.wheel_angular_velocity_rear,
            'motor_speed': self.motor_speed,
            'motor_current': self.motor_current,
            'motor_torque': self.motor_torque,
            'drive_force': self.drive_force,
            'drag_force': self.drag_force,
            'rolling_resistance': self.rolling_resistance,
            'normal_force_front': self.normal_force_front,
            'normal_force_rear': self.normal_force_rear,
            'tire_force_front': self.tire_force_front,
            'tire_force_rear': self.tire_force_rear,
            'power_consumed': self.power_consumed
        }
    
    def copy(self) -> 'SimulationState':
        """Create a copy of the state."""
        return SimulationState(
            position=self.position,
            velocity=self.velocity,
            acceleration=self.acceleration,
            wheel_angular_velocity_front=self.wheel_angular_velocity_front,
            wheel_angular_velocity_rear=self.wheel_angular_velocity_rear,
            motor_speed=self.motor_speed,
            motor_current=self.motor_current,
            motor_torque=self.motor_torque,
            drive_force=self.drive_force,
            drag_force=self.drag_force,
            rolling_resistance=self.rolling_resistance,
            normal_force_front=self.normal_force_front,
            normal_force_rear=self.normal_force_rear,
            tire_force_front=self.tire_force_front,
            tire_force_rear=self.tire_force_rear,
            power_consumed=self.power_consumed,
            time=self.time
        )


