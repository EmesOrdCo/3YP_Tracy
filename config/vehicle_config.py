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
    # Simplified tire model parameters (used when tire_model_type="simple")
    mu_max: float  # Maximum friction coefficient
    mu_slip_optimal: float  # Optimal slip ratio
    rolling_resistance_coeff: float = 0.015
    
    # Tire model selection: "pacejka" or "simple"
    tire_model_type: str = "pacejka"
    
    # Pacejka Magic Formula coefficients (used when tire_model_type="pacejka")
    # These are the simplified form coefficients
    pacejka_B: Optional[float] = None  # Stiffness factor
    pacejka_C: Optional[float] = None  # Shape factor (typically 1.5-1.9)
    pacejka_D: Optional[float] = None  # Peak friction coefficient (μ_peak)
    pacejka_E: Optional[float] = None  # Curvature factor
    
    # Advanced Pacejka coefficients for load sensitivity
    # D = Fz * (pDx1 + pDx2 * dfz) where dfz = (Fz - Fz0) / Fz0
    pacejka_pDx1: Optional[float] = None  # Peak μ at nominal load
    pacejka_pDx2: Optional[float] = None  # Load sensitivity coefficient
    pacejka_Fz0: Optional[float] = None   # Nominal load (N)
    
    # Slip stiffness coefficients
    # Kx = pKx1 + pKx2 * dfz, then B = Kx / (C * D)
    pacejka_pKx1: Optional[float] = None  # Longitudinal slip stiffness
    pacejka_pKx2: Optional[float] = None  # Variation with load


@dataclass
class PowertrainProperties:
    """Powertrain configuration."""
    # Motor properties (required)
    motor_torque_constant: float  # N·m/A
    motor_max_current: float  # A
    motor_max_speed: float  # rad/s
    
    # Battery properties (required for battery mode)
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
    wheel_inertia: float = 0.1  # kg·m² (per pair of driven wheels, so total 2 * wheel_inertia)

    # --- Driveline torsional compliance ---
    # When enabled, motor and rear-wheel angular velocities become separate
    # integrated states coupled by a spring-damper. Off by default so legacy
    # results remain identical; flip the flag (or set
    # ``driveline_compliance_enabled: true`` in JSON) to get the higher-
    # fidelity launch dynamics.
    driveline_compliance_enabled: bool = False
    motor_inertia: float = 0.077  # kg·m² - YASA P400R rotor inertia (datasheet)
    # Combined gearbox + two-halfshaft torsional stiffness, reflected to the
    # rear wheel hub. 15 000 N·m/rad matches a typical FS setup (two 25 mm
    # steel halfshafts in parallel plus a stiff single-stage reduction).
    driveline_stiffness: float = 15000.0  # N·m / rad at the wheel hub
    # Damping tuned for zeta ~ 0.7 against 15 000 N·m/rad and the reduced
    # inertia of motor+wheel (~0.09 kg·m²), giving a well-damped ~65 Hz mode.
    driveline_damping: float = 50.0  # N·m·s / rad at the wheel hub
    
    # Energy storage type selection
    energy_storage_type: str = "battery"  # "battery" or "supercapacitor"
    
    # Supercapacitor properties (used when energy_storage_type="supercapacitor")
    # Based on C46W-3R0-0600 configuration from main.m
    supercap_cell_voltage: float = 3.0  # V per cell
    supercap_cell_capacitance: float = 600.0  # F per cell
    supercap_cell_esr: float = 0.7e-3  # Ω per cell (0.7 mΩ)
    supercap_num_cells: int = 200  # Number of cells in series
    supercap_min_voltage: float = 350.0  # V - minimum operating voltage (inverter threshold)


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
    """Control strategy parameters.

    The solver reads:
      * ``launch_torque_limit`` - hard upper bound on requested wheel torque.
      * ``traction_control_enabled`` - if False, slip governor is bypassed.

    Slip targeting and torque ramp timing are handled internally:
      * Target slip ratio: Pacejka-optimal (load-dependent, per tyre).
      * Launch ramp: fixed 80 ms.
    """
    launch_torque_limit: float = 1000.0  # N.m
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
        """Return a list of human-readable configuration errors (empty = valid).

        Designed to catch problems at load time (before the solver runs),
        since many of the knobs silently produce garbage results if zeroed or
        negated rather than raising.
        """
        errors: List[str] = []

        # --- FS rule: accumulator outlet cap (EV 2.2) ---
        if self.powertrain.max_power_accumulator_outlet > 80e3 + 1.0:
            errors.append("powertrain.max_power_accumulator_outlet exceeds FS 80 kW cap (EV 2.2).")

        # --- Mass / geometry ---
        if self.mass.total_mass <= 0:
            errors.append("mass.total_mass must be positive.")
        if self.mass.wheelbase <= 0:
            errors.append("mass.wheelbase must be positive.")
        if not (0 < self.mass.cg_x < self.mass.wheelbase):
            errors.append("mass.cg_x must lie strictly between the axles (0 < cg_x < wheelbase).")
        if self.mass.cg_z <= 0:
            errors.append("mass.cg_z must be positive (CG height above ground).")
        if self.mass.front_track <= 0 or self.mass.rear_track <= 0:
            errors.append("mass.front_track and rear_track must be positive.")
        if self.mass.i_yaw <= 0 or self.mass.i_pitch <= 0:
            errors.append("mass inertias (i_yaw, i_pitch) must be positive.")
        if self.mass.unsprung_mass_front < 0 or self.mass.unsprung_mass_rear < 0:
            errors.append("unsprung masses must be non-negative.")
        if (self.mass.unsprung_mass_front + self.mass.unsprung_mass_rear
                > self.mass.total_mass):
            errors.append("unsprung_mass_front + unsprung_mass_rear exceeds total_mass.")

        # --- Tyres ---
        if self.tires.radius_loaded <= 0:
            errors.append("tires.radius_loaded must be positive.")
        if self.tires.mu_max <= 0:
            errors.append("tires.mu_max must be positive.")
        if not (0 < self.tires.mu_slip_optimal < 1):
            errors.append("tires.mu_slip_optimal must be in (0, 1).")
        if self.tires.rolling_resistance_coeff < 0:
            errors.append("tires.rolling_resistance_coeff must be non-negative.")
        if self.tires.tire_model_type not in ("pacejka", "simple"):
            errors.append("tires.tire_model_type must be 'pacejka' or 'simple'.")

        # --- Powertrain ---
        pt = self.powertrain
        if pt.gear_ratio <= 0:
            errors.append("powertrain.gear_ratio must be positive.")
        if pt.motor_torque_constant <= 0:
            errors.append("powertrain.motor_torque_constant must be positive.")
        if pt.motor_max_current <= 0:
            errors.append("powertrain.motor_max_current must be positive.")
        if pt.motor_max_speed <= 0:
            errors.append("powertrain.motor_max_speed must be positive.")
        if not (0 < pt.motor_efficiency <= 1):
            errors.append("powertrain.motor_efficiency must be in (0, 1].")
        if not (0 < pt.drivetrain_efficiency <= 1):
            errors.append("powertrain.drivetrain_efficiency must be in (0, 1].")
        if pt.battery_voltage_nominal <= 0:
            errors.append("powertrain.battery_voltage_nominal must be positive.")
        if pt.battery_internal_resistance < 0:
            errors.append("powertrain.battery_internal_resistance must be non-negative.")
        if pt.battery_max_current <= 0:
            errors.append("powertrain.battery_max_current must be positive.")
        if pt.wheel_inertia <= 0:
            errors.append("powertrain.wheel_inertia must be positive.")
        if pt.driveline_compliance_enabled:
            if pt.motor_inertia <= 0:
                errors.append("powertrain.motor_inertia must be positive when driveline compliance is on.")
            if pt.driveline_stiffness <= 0:
                errors.append("powertrain.driveline_stiffness must be positive when driveline compliance is on.")
            if pt.driveline_damping < 0:
                errors.append("powertrain.driveline_damping must be non-negative.")
        if pt.energy_storage_type not in ("battery", "supercapacitor"):
            errors.append("powertrain.energy_storage_type must be 'battery' or 'supercapacitor'.")
        if pt.energy_storage_type == "supercapacitor":
            if pt.supercap_num_cells <= 0:
                errors.append("powertrain.supercap_num_cells must be positive.")
            if pt.supercap_cell_voltage <= 0 or pt.supercap_cell_capacitance <= 0:
                errors.append("supercap cell voltage and capacitance must be positive.")
            full_stack_v = pt.supercap_cell_voltage * pt.supercap_num_cells
            if pt.supercap_min_voltage >= full_stack_v:
                errors.append(
                    "powertrain.supercap_min_voltage must be below full-stack voltage "
                    f"({full_stack_v:.1f} V)."
                )

        # --- Aero ---
        if self.aerodynamics.cda < 0:
            errors.append("aerodynamics.cda must be non-negative.")
        if self.aerodynamics.air_density <= 0:
            errors.append("aerodynamics.air_density must be positive.")

        # --- Suspension ---
        if not (0 <= self.suspension.anti_squat_ratio <= 1):
            errors.append("suspension.anti_squat_ratio must be in [0, 1].")

        # --- Environment ---
        if not (0 < self.environment.surface_mu_scaling <= 1.5):
            errors.append("environment.surface_mu_scaling must be in (0, 1.5].")
        if self.environment.air_density <= 0:
            errors.append("environment.air_density must be positive.")

        # --- Simulation ---
        if self.dt <= 0:
            errors.append("simulation.dt must be positive.")
        if self.max_time <= 0:
            errors.append("simulation.max_time must be positive.")
        if self.target_distance <= 0:
            errors.append("simulation.target_distance must be positive.")

        return errors

