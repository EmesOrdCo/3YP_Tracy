"""Simulation state management."""

from dataclasses import dataclass
from typing import Dict


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

    # Driveline torsional state. Only integrated when
    # powertrain.driveline_compliance_enabled is True; otherwise the rigid
    # coupling motor_speed = wheel_speed_rear * gear_ratio is used and this
    # stays at its default 0.
    driveline_twist: float = 0.0  # rad at wheel hub (motor side - wheel side)

    # Derivative carriers (populated by _calculate_derivatives so that
    # _rk4_step can integrate motor_speed and driveline_twist without
    # overloading the value slots above).
    motor_alpha: float = 0.0  # rad/s^2 - motor angular acceleration
    driveline_twist_rate: float = 0.0  # rad/s - dtheta_twist/dt
    
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
    
    # Slip ratios
    slip_ratio_rear: float = 0.0  # Rear tire slip ratio
    optimal_slip_ratio: float = 0.0  # Pacejka optimal slip (load-dependent)
    
    # Power
    power_consumed: float = 0.0  # W
    
    # Energy storage state (for supercapacitor tracking)
    dc_bus_voltage: float = 0.0  # V - DC bus voltage from energy storage
    energy_storage_soc: float = 1.0  # State of charge (0-1)
    energy_storage_loss: float = 0.0  # W - Power loss in energy storage (ESR)
    in_field_weakening: bool = False  # True if motor is in field weakening region
    
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
            'slip_ratio_rear': self.slip_ratio_rear,
            'optimal_slip_ratio': self.optimal_slip_ratio,
            'power_consumed': self.power_consumed,
            'dc_bus_voltage': self.dc_bus_voltage,
            'energy_storage_soc': self.energy_storage_soc,
            'energy_storage_loss': self.energy_storage_loss,
            'in_field_weakening': self.in_field_weakening,
            'driveline_twist': self.driveline_twist,
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
            slip_ratio_rear=self.slip_ratio_rear,
            optimal_slip_ratio=self.optimal_slip_ratio,
            power_consumed=self.power_consumed,
            dc_bus_voltage=self.dc_bus_voltage,
            energy_storage_soc=self.energy_storage_soc,
            energy_storage_loss=self.energy_storage_loss,
            in_field_weakening=self.in_field_weakening,
            driveline_twist=self.driveline_twist,
            motor_alpha=self.motor_alpha,
            driveline_twist_rate=self.driveline_twist_rate,
            time=self.time
        )



