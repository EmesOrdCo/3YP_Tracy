"""Comprehensive optimization - optimizes all parameters that need optimization,
   sets sensible values for minimize/maximize parameters, and outputs complete summary."""

from pathlib import Path
import sys
import json
import copy

print("=" * 70, flush=True)
print("FORMULA STUDENT ACCELERATION - COMPREHENSIVE OPTIMIZATION", flush=True)
print("=" * 70, flush=True)
print("", flush=True)

# Add parent directory to path  
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

print("Loading configuration...", flush=True)
from config.config_loader import load_config
from config.vehicle_config import VehicleConfig
from simulation.multi_objective_optimizer import MultiObjectiveOptimizer

# Load base config
base_config = load_config("config/vehicle_configs/base_vehicle.json")
print(f"✓ Configuration loaded: {base_config.mass.total_mass} kg", flush=True)

# ============================================================================
# SET SENSIBLE HARDCODED VALUES FOR MINIMIZE/MAXIMIZE PARAMETERS
# ============================================================================

print("\n" + "=" * 70, flush=True)
print("SETTING SENSIBLE HARDCODED VALUES", flush=True)
print("=" * 70, flush=True)

# Create a copy to modify
optimized_config = copy.deepcopy(base_config)

# MINIMIZE parameters - set to reasonable minimums
print("\nSetting MINIMIZE parameters to sensible minimum values:", flush=True)
optimized_config.mass.total_mass = 200.0  # Minimize - assume minimum allowed by rules
print(f"  mass.total_mass: {optimized_config.mass.total_mass} kg (MINIMIZE)", flush=True)

optimized_config.mass.cg_z = 0.22  # Minimize - as low as practical (ground clearance constraint)
print(f"  mass.cg_z: {optimized_config.mass.cg_z} m (MINIMIZE)", flush=True)

optimized_config.mass.unsprung_mass_front = 12.0  # Minimize - lighter components
print(f"  mass.unsprung_mass_front: {optimized_config.mass.unsprung_mass_front} kg (MINIMIZE)", flush=True)

optimized_config.mass.unsprung_mass_rear = 12.0  # Minimize - lighter components
print(f"  mass.unsprung_mass_rear: {optimized_config.mass.unsprung_mass_rear} kg (MINIMIZE)", flush=True)

optimized_config.mass.i_pitch = 150.0  # Minimize - optimize mass distribution
print(f"  mass.i_pitch: {optimized_config.mass.i_pitch} kg·m² (MINIMIZE)", flush=True)

optimized_config.tires.rolling_resistance_coeff = 0.010  # Minimize - lower rolling resistance
print(f"  tires.rolling_resistance_coeff: {optimized_config.tires.rolling_resistance_coeff} (MINIMIZE)", flush=True)

optimized_config.powertrain.battery_internal_resistance = 0.008  # Minimize - better cells
print(f"  powertrain.battery_internal_resistance: {optimized_config.powertrain.battery_internal_resistance} Ω (MINIMIZE)", flush=True)

optimized_config.powertrain.wheel_inertia = 0.06  # Minimize - lighter wheels
print(f"  powertrain.wheel_inertia: {optimized_config.powertrain.wheel_inertia} kg·m² (MINIMIZE)", flush=True)

optimized_config.aerodynamics.cda = 0.65  # Minimize - lower drag
print(f"  aerodynamics.cda: {optimized_config.aerodynamics.cda} (MINIMIZE)", flush=True)

optimized_config.suspension.ride_height_front = 0.08  # Minimize - lower ride height
print(f"  suspension.ride_height_front: {optimized_config.suspension.ride_height_front} m (MINIMIZE)", flush=True)

optimized_config.suspension.ride_height_rear = 0.08  # Minimize - lower ride height
print(f"  suspension.ride_height_rear: {optimized_config.suspension.ride_height_rear} m (MINIMIZE)", flush=True)

# MAXIMIZE parameters - set to reasonable maximums
print("\nSetting MAXIMIZE parameters to sensible maximum values:", flush=True)
optimized_config.tires.mu_max = 1.7  # Maximize - best tire compound available
print(f"  tires.mu_max: {optimized_config.tires.mu_max} (MAXIMIZE)", flush=True)

optimized_config.powertrain.motor_torque_constant = 0.65  # Maximize - better motor
print(f"  powertrain.motor_torque_constant: {optimized_config.powertrain.motor_torque_constant} N·m/A (MAXIMIZE)", flush=True)

optimized_config.powertrain.motor_max_current = 250.0  # Maximize - higher current capability
print(f"  powertrain.motor_max_current: {optimized_config.powertrain.motor_max_current} A (MAXIMIZE)", flush=True)

optimized_config.powertrain.motor_efficiency = 0.96  # Maximize - better efficiency
print(f"  powertrain.motor_efficiency: {optimized_config.powertrain.motor_efficiency} (MAXIMIZE)", flush=True)

optimized_config.powertrain.battery_voltage_nominal = 350.0  # Maximize - higher voltage (within rules)
print(f"  powertrain.battery_voltage_nominal: {optimized_config.powertrain.battery_voltage_nominal} V (MAXIMIZE)", flush=True)

optimized_config.powertrain.battery_max_current = 350.0  # Maximize - higher battery current
print(f"  powertrain.battery_max_current: {optimized_config.powertrain.battery_max_current} A (MAXIMIZE)", flush=True)

optimized_config.powertrain.drivetrain_efficiency = 0.97  # Maximize - better drivetrain
print(f"  powertrain.drivetrain_efficiency: {optimized_config.powertrain.drivetrain_efficiency} (MAXIMIZE)", flush=True)

optimized_config.aerodynamics.cl_front = 1.5  # Maximize - front downforce (if have aero)
print(f"  aerodynamics.cl_front: {optimized_config.aerodynamics.cl_front} (MAXIMIZE)", flush=True)

optimized_config.aerodynamics.cl_rear = 1.8  # Maximize - rear downforce (if have aero)
print(f"  aerodynamics.cl_rear: {optimized_config.aerodynamics.cl_rear} (MAXIMIZE)", flush=True)

optimized_config.control.traction_control_enabled = True  # Maximize - always enable
print(f"  control.traction_control_enabled: {optimized_config.control.traction_control_enabled} (MAXIMIZE)", flush=True)

# ============================================================================
# DEFINE PARAMETERS TO OPTIMIZE (all "OPTIMIZE" parameters)
# ============================================================================

print("\n" + "=" * 70, flush=True)
print("DEFINING PARAMETERS TO OPTIMIZE", flush=True)
print("=" * 70, flush=True)

parameter_bounds = {
    # Mass parameters
    'mass.cg_x': (0.9, 1.3),  # OPTIMIZE - find optimal balance
    
    # Tire parameters
    'tires.radius_loaded': (0.20, 0.25),  # OPTIMIZE - torque vs speed trade-off
    'tires.mu_slip_optimal': (0.12, 0.18),  # OPTIMIZE - match with target_slip_ratio
    
    # Powertrain parameters
    'powertrain.gear_ratio': (8.0, 13.0),  # OPTIMIZE - torque vs speed trade-off
    
    # Suspension parameters
    'suspension.anti_squat_ratio': (0.0, 0.6),  # OPTIMIZE - load transfer optimization
    
    # Control parameters
    'control.launch_torque_limit': (600.0, 1400.0),  # OPTIMIZE - launch strategy
    'control.target_slip_ratio': (0.10, 0.20),  # OPTIMIZE - traction control
}

print(f"\nParameters to optimize: {len(parameter_bounds)}", flush=True)
for param, (min_val, max_val) in parameter_bounds.items():
    print(f"  - {param}: [{min_val}, {max_val}]", flush=True)

# ============================================================================
# RUN OPTIMIZATION
# ============================================================================

print("\n" + "=" * 70, flush=True)
print("STARTING OPTIMIZATION", flush=True)
print("=" * 70, flush=True)
print(f"Settings: 40 iterations × 25 population = ~1000 simulations", flush=True)
print("Estimated time: 5-10 minutes", flush=True)
print("Progress updates will appear every 10 evaluations...\n", flush=True)
print("-" * 70, flush=True)

# Create optimizer
optimizer = MultiObjectiveOptimizer(
    base_config=optimized_config,  # Use config with hardcoded values
    parameter_bounds=parameter_bounds,
    objective='minimize_time_with_rules',
    enforce_rules=True
)

result = optimizer.optimize(
    method='differential_evolution',
    max_iterations=40,
    population_size=25,
    verbose=True
)

# ============================================================================
# OUTPUT RESULTS
# ============================================================================

print("\n" + "=" * 70, flush=True)
print("OPTIMIZATION RESULTS", flush=True)
print("=" * 70, flush=True)

print(f"\n✓ Optimization complete!")
print(f"  Best time: {result.best_simulation_result.final_time:.3f}s")
print(f"  Power compliant: {result.best_simulation_result.power_compliant}")
print(f"  Total evaluations: {len(result.all_evaluations)}")

final_config = result.best_config

print("\n" + "=" * 70, flush=True)
print("OPTIMIZED PARAMETERS (from optimization script):", flush=True)
print("=" * 70, flush=True)
for param in parameter_bounds.keys():
    parts = param.split('.')
    value = final_config
    for part in parts:
        value = getattr(value, part)
    print(f"  {param:35s} = {value:.6f}", flush=True)

# ============================================================================
# COMPLETE PARAMETER SUMMARY
# ============================================================================

print("\n" + "=" * 70, flush=True)
print("COMPLETE PARAMETER SUMMARY (All Parameters)", flush=True)
print("=" * 70, flush=True)
print(f"{'Parameter':<50s} {'Value':<20s} {'Source':<20s}", flush=True)
print("-" * 90, flush=True)

# Helper function to get nested attribute
def get_nested_attr(obj, path):
    """Get nested attribute like 'mass.cg_x'"""
    parts = path.split('.')
    value = obj
    for part in parts:
        value = getattr(value, part)
    return value

# Define all parameters with their sources
all_parameters = {
    # MASS PARAMETERS
    'mass.total_mass': 'HARDCODED (MINIMIZE)',
    'mass.cg_x': 'OPTIMIZATION',
    'mass.cg_z': 'HARDCODED (MINIMIZE)',
    'mass.wheelbase': 'BASE_CONFIG (FIXED)',
    'mass.front_track': 'BASE_CONFIG (NO IMPACT)',
    'mass.rear_track': 'BASE_CONFIG (NO IMPACT)',
    'mass.i_yaw': 'BASE_CONFIG (NO IMPACT)',
    'mass.i_pitch': 'HARDCODED (MINIMIZE)',
    'mass.unsprung_mass_front': 'HARDCODED (MINIMIZE)',
    'mass.unsprung_mass_rear': 'HARDCODED (MINIMIZE)',
    
    # TIRE PARAMETERS
    'tires.radius_loaded': 'OPTIMIZATION',
    'tires.mass': 'BASE_CONFIG (FIXED)',
    'tires.mu_max': 'HARDCODED (MAXIMIZE)',
    'tires.mu_slip_optimal': 'OPTIMIZATION',
    'tires.rolling_resistance_coeff': 'HARDCODED (MINIMIZE)',
    
    # POWERTRAIN PARAMETERS
    'powertrain.motor_torque_constant': 'HARDCODED (MAXIMIZE)',
    'powertrain.motor_max_current': 'HARDCODED (MAXIMIZE)',
    'powertrain.motor_max_speed': 'BASE_CONFIG (NOT LIMITING)',
    'powertrain.motor_efficiency': 'HARDCODED (MAXIMIZE)',
    'powertrain.battery_voltage_nominal': 'HARDCODED (MAXIMIZE)',
    'powertrain.battery_internal_resistance': 'HARDCODED (MINIMIZE)',
    'powertrain.battery_max_current': 'HARDCODED (MAXIMIZE)',
    'powertrain.gear_ratio': 'OPTIMIZATION',
    'powertrain.drivetrain_efficiency': 'HARDCODED (MAXIMIZE)',
    'powertrain.differential_ratio': 'BASE_CONFIG (NO IMPACT)',
    'powertrain.max_power_accumulator_outlet': 'BASE_CONFIG (RULE)',
    'powertrain.wheel_inertia': 'HARDCODED (MINIMIZE)',
    
    # AERODYNAMICS PARAMETERS
    'aerodynamics.cda': 'HARDCODED (MINIMIZE)',
    'aerodynamics.cl_front': 'HARDCODED (MAXIMIZE)',
    'aerodynamics.cl_rear': 'HARDCODED (MAXIMIZE)',
    'aerodynamics.air_density': 'BASE_CONFIG (ENVIRONMENTAL)',
    
    # SUSPENSION PARAMETERS
    'suspension.anti_squat_ratio': 'OPTIMIZATION',
    'suspension.ride_height_front': 'HARDCODED (MINIMIZE)',
    'suspension.ride_height_rear': 'HARDCODED (MINIMIZE)',
    'suspension.wheel_rate_front': 'BASE_CONFIG (LOW IMPACT)',
    'suspension.wheel_rate_rear': 'BASE_CONFIG (LOW IMPACT)',
    
    # CONTROL PARAMETERS
    'control.launch_torque_limit': 'OPTIMIZATION',
    'control.target_slip_ratio': 'OPTIMIZATION',
    'control.torque_ramp_rate': 'BASE_CONFIG (LOW IMPACT)',
    'control.traction_control_enabled': 'HARDCODED (MAXIMIZE)',
    
    # ENVIRONMENT PARAMETERS
    'environment.air_density': 'BASE_CONFIG (ENVIRONMENTAL)',
    'environment.ambient_temperature': 'BASE_CONFIG (ENVIRONMENTAL)',
    'environment.track_grade': 'BASE_CONFIG (ENVIRONMENTAL)',
    'environment.wind_speed': 'BASE_CONFIG (ENVIRONMENTAL)',
    'environment.surface_mu_scaling': 'BASE_CONFIG (ENVIRONMENTAL)',
    
    # SIMULATION PARAMETERS
    'simulation.dt': 'BASE_CONFIG (SIMULATION)',
    'simulation.max_time': 'BASE_CONFIG (SIMULATION)',
    'simulation.target_distance': 'BASE_CONFIG (RULE)',
}

    # Print all parameters
for param_path, source in sorted(all_parameters.items()):
    try:
        # Handle simulation parameters (direct attributes, not nested)
        if param_path.startswith('simulation.'):
            attr_name = param_path.split('.')[1]
            value = getattr(final_config, attr_name)
        else:
            value = get_nested_attr(final_config, param_path)
        # Format value appropriately
        if isinstance(value, bool):
            value_str = str(value)
        elif isinstance(value, (int, float)):
            if abs(value) < 0.001 or abs(value) > 10000:
                value_str = f"{value:.4e}"
            else:
                value_str = f"{value:.6f}"
        else:
            value_str = str(value)
        print(f"{param_path:<50s} {value_str:<20s} {source:<20s}", flush=True)
    except AttributeError:
        # Try with different path format
        print(f"{param_path:<50s} {'N/A':<20s} {source:<20s}", flush=True)

print("\n" + "=" * 70, flush=True)
print("OPTIMIZATION COMPLETE!", flush=True)
print("=" * 70, flush=True)

# Save optimized config to JSON
output_file = Path(__file__).parent.parent / "config" / "vehicle_configs" / "optimized_vehicle.json"
print(f"\nSaving optimized configuration to: {output_file}", flush=True)

def config_to_dict(config):
    """Convert VehicleConfig to dictionary."""
    return {
        'mass': {
            'total_mass': config.mass.total_mass,
            'cg_x': config.mass.cg_x,
            'cg_z': config.mass.cg_z,
            'wheelbase': config.mass.wheelbase,
            'front_track': config.mass.front_track,
            'rear_track': config.mass.rear_track,
            'i_yaw': config.mass.i_yaw,
            'i_pitch': config.mass.i_pitch,
            'unsprung_mass_front': config.mass.unsprung_mass_front,
            'unsprung_mass_rear': config.mass.unsprung_mass_rear,
        },
        'tires': {
            'radius_loaded': config.tires.radius_loaded,
            'mass': config.tires.mass,
            'mu_max': config.tires.mu_max,
            'mu_slip_optimal': config.tires.mu_slip_optimal,
            'rolling_resistance_coeff': config.tires.rolling_resistance_coeff,
        },
        'powertrain': {
            'motor_torque_constant': config.powertrain.motor_torque_constant,
            'motor_max_current': config.powertrain.motor_max_current,
            'motor_max_speed': config.powertrain.motor_max_speed,
            'motor_efficiency': config.powertrain.motor_efficiency,
            'battery_voltage_nominal': config.powertrain.battery_voltage_nominal,
            'battery_internal_resistance': config.powertrain.battery_internal_resistance,
            'battery_max_current': config.powertrain.battery_max_current,
            'gear_ratio': config.powertrain.gear_ratio,
            'drivetrain_efficiency': config.powertrain.drivetrain_efficiency,
            'differential_ratio': config.powertrain.differential_ratio,
            'max_power_accumulator_outlet': config.powertrain.max_power_accumulator_outlet,
            'wheel_inertia': config.powertrain.wheel_inertia,
        },
        'aerodynamics': {
            'cda': config.aerodynamics.cda,
            'cl_front': config.aerodynamics.cl_front,
            'cl_rear': config.aerodynamics.cl_rear,
            'air_density': config.aerodynamics.air_density,
        },
        'suspension': {
            'anti_squat_ratio': config.suspension.anti_squat_ratio,
            'ride_height_front': config.suspension.ride_height_front,
            'ride_height_rear': config.suspension.ride_height_rear,
            'wheel_rate_front': config.suspension.wheel_rate_front,
            'wheel_rate_rear': config.suspension.wheel_rate_rear,
        },
        'control': {
            'launch_torque_limit': config.control.launch_torque_limit,
            'target_slip_ratio': config.control.target_slip_ratio,
            'torque_ramp_rate': config.control.torque_ramp_rate,
            'traction_control_enabled': config.control.traction_control_enabled,
        },
        'environment': {
            'air_density': config.environment.air_density,
            'ambient_temperature': config.environment.ambient_temperature,
            'track_grade': config.environment.track_grade,
            'wind_speed': config.environment.wind_speed,
            'surface_mu_scaling': config.environment.surface_mu_scaling,
        },
        'simulation': {
            'dt': config.dt,
            'max_time': config.max_time,
            'target_distance': config.target_distance,
        },
    }

with open(output_file, 'w') as f:
    json.dump(config_to_dict(final_config), f, indent=2)

print(f"✓ Configuration saved successfully!", flush=True)

