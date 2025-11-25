"""Vehicle configuration classes for acceleration simulation."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class MassProperties:
    """Vehicle mass and inertia properties."""
    total_mass: float  # kg
    cg_x: float  # m from front axle
    cg_z: float  # m from ground
    wheelbase: float  # m
    front_track: float  # m
    rear_track: float  # m
    i_yaw: float  # kg·m²
    i_pitch: float  # kg·m²
    unsprung_mass_front: float = 0.0  # kg
    unsprung_mass_rear: float = 0.0  # kg
    
    @property
    def sprung_mass(self) -> float:
        """Calculate sprung mass."""
        return self.total_mass - self.unsprung_mass_front - self.unsprung_mass_rear


@dataclass
class TireProperties:
    """Tire properties and model parameters."""
    radius_loaded: float  # m
    mass: float  # kg
    # Simplified tire model parameters (upgrade to Pacejka later)
    mu_max: float  # Maximum friction coefficient
    mu_slip_optimal: float  # Optimal slip ratio
    rolling_resistance_coeff: float = 0.015
    # Pacejka parameters (optional, for advanced model)
    pacejka_D: Optional[float] = None
    pacejka_C: Optional[float] = None
    pacejka_B: Optional[float] = None
    pacejka_E: Optional[float] = None


@dataclass
class PowertrainProperties:
    """Powertrain configuration."""
    # Motor properties (required)
    motor_torque_constant: float  # N·m/A
    motor_max_current: float  # A
    motor_max_speed: float  # rad/s
    
    # Battery properties (required)
    battery_voltage_nominal: float  # V
    battery_internal_resistance: float  # Ω
    battery_max_current: float  # A
    
    # Drivetrain (required)
    gear_ratio: float  # Overall gear ratio
    
    # Optional parameters (with defaults)
    motor_efficiency: float = 0.95  # Constant efficiency (can be map later)
    drivetrain_efficiency: float = 0.95
    differential_ratio: float = 1.0
    max_power_accumulator_outlet: float = 80e3  # W (80 kW) - Formula Student rule EV 2.2
    wheel_inertia: float = 0.1  # kg·m²


@dataclass
class AerodynamicsProperties:
    """Aerodynamic properties."""
    cda: float  # Drag area (m²)
    cl_front: float = 0.0  # Front downforce coefficient
    cl_rear: float = 0.0  # Rear downforce coefficient
    air_density: float = 1.225  # kg/m³ (sea level, 15°C)


@dataclass
class SuspensionProperties:
    """Suspension geometry and properties."""
    anti_squat_ratio: float = 0.0
    ride_height_front: float = 0.1  # m
    ride_height_rear: float = 0.1  # m
    wheel_rate_front: float = 30000.0  # N/m
    wheel_rate_rear: float = 30000.0  # N/m


@dataclass
class ControlProperties:
    """Control strategy parameters."""
    launch_torque_limit: float = 1000.0  # N·m
    target_slip_ratio: float = 0.15
    torque_ramp_rate: float = 500.0  # N·m/s
    traction_control_enabled: bool = True


@dataclass
class EnvironmentProperties:
    """Environmental conditions."""
    air_density: float = 1.225  # kg/m³
    ambient_temperature: float = 20.0  # °C
    track_grade: float = 0.0  # radians (slope)
    wind_speed: float = 0.0  # m/s
    surface_mu_scaling: float = 1.0  # Grip multiplier


@dataclass
class VehicleConfig:
    """Complete vehicle configuration."""
    mass: MassProperties
    tires: TireProperties
    powertrain: PowertrainProperties
    aerodynamics: AerodynamicsProperties
    suspension: SuspensionProperties
    control: ControlProperties
    environment: EnvironmentProperties
    
    # Simulation parameters
    dt: float = 0.001  # s (time step)
    max_time: float = 30.0  # s (max simulation time)
    target_distance: float = 75.0  # m (Formula Student acceleration distance)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Check power limit (EV 2.2)
        if self.powertrain.max_power_accumulator_outlet > 80e3:
            errors.append("Power limit exceeds 80 kW (EV 2.2)")
        
        # Check mass properties
        if self.mass.total_mass <= 0:
            errors.append("Total mass must be positive")
        
        if self.mass.cg_x < 0 or self.mass.cg_x > self.mass.wheelbase:
            errors.append("CG X position must be within wheelbase")
        
        # Check tire properties
        if self.tires.radius_loaded <= 0:
            errors.append("Tire radius must be positive")
        
        # Check powertrain
        if self.powertrain.gear_ratio <= 0:
            errors.append("Gear ratio must be positive")
        
        return errors

