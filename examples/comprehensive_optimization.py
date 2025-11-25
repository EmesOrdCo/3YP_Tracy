"""Comprehensive optimization example: Finding the ultimate vehicle setup.

This script demonstrates how to optimize multiple vehicle parameters simultaneously
to find the best overall configuration within Formula Student regulations.

The optimizer uses intelligent search algorithms (differential evolution/genetic algorithms)
to efficiently explore millions of possible configurations without brute-force testing.
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from simulation.multi_objective_optimizer import MultiObjectiveOptimizer, OptimizationResult
from analysis.visualization import plot_optimization_results


def main():
    """Run comprehensive optimization."""
    
    print("=" * 70)
    print("COMPREHENSIVE VEHICLE OPTIMIZATION")
    print("Finding optimal setup within Formula Student regulations")
    print("=" * 70)
    
    # Load base configuration
    config_path = Path(__file__).parent.parent / "config" / "vehicle_configs" / "base_vehicle.json"
    base_config = load_config(config_path)
    
    print(f"\nBase configuration loaded from: {config_path}")
    print(f"Initial setup:")
    print(f"  Mass: {base_config.mass.total_mass:.1f} kg")
    print(f"  CG X: {base_config.mass.cg_x:.3f} m")
    print(f"  CG Z: {base_config.mass.cg_z:.3f} m")
    print(f"  Gear ratio: {base_config.powertrain.gear_ratio:.2f}")
    
    # Define parameter bounds for optimization
    # These are the parameters you want to optimize
    parameter_bounds = {
        # Mass distribution parameters
        'mass.cg_x': (0.8, 1.4),  # CG position (front to rear)
        'mass.cg_z': (0.2, 0.4),  # CG height (lower is better)
        
        # Powertrain parameters
        'powertrain.gear_ratio': (8.0, 12.0),  # Gear ratio
        
        # Control parameters
        'control.target_slip_ratio': (0.10, 0.20),  # Optimal slip ratio
        'control.launch_torque_limit': (500.0, 1500.0),  # Launch torque
        
        # Aerodynamics (if you have aero)
        'aerodynamics.cda': (0.6, 1.0),  # Drag coefficient
        'aerodynamics.cl_rear': (0.0, 2.0),  # Rear downforce
        
        # Suspension
        'suspension.anti_squat_ratio': (0.0, 0.5),  # Anti-squat
    }
    
    print(f"\nOptimizing {len(parameter_bounds)} parameters:")
    for param, (min_val, max_val) in parameter_bounds.items():
        print(f"  {param}: [{min_val:.2f}, {max_val:.2f}]")
    
    # Create optimizer
    optimizer = MultiObjectiveOptimizer(
        base_config=base_config,
        parameter_bounds=parameter_bounds,
        objective='minimize_time_with_rules',  # Minimize time while staying within rules
        enforce_rules=True,  # Penalize rule violations
        n_workers=None  # Auto-detect number of CPU cores
    )
    
    print("\nStarting optimization...")
    print("This will run many simulations to find the optimal configuration.")
    print("The optimizer uses intelligent search (genetic algorithm) to avoid")
    print("testing all millions of combinations.\n")
    
    # Run optimization
    result: OptimizationResult = optimizer.optimize(
        method='differential_evolution',  # Genetic algorithm - good for global search
        max_iterations=50,  # Number of generations (increase for better results)
        population_size=30,  # Population size (more = better exploration, slower)
        verbose=True,
        save_progress='optimization_progress.json'
    )
    
    # Display results
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)
    
    best_result = result.best_simulation_result
    best_config = result.best_config
    
    print(f"\nBest Configuration:")
    print(f"  Final Time: {best_result.final_time:.3f} s")
    print(f"  Final Distance: {best_result.final_distance:.2f} m")
    print(f"  Final Velocity: {best_result.final_velocity:.2f} m/s ({best_result.final_velocity*3.6:.1f} km/h)")
    print(f"  Power Compliant: {best_result.power_compliant}")
    print(f"  Time Compliant: {best_result.time_compliant}")
    if best_result.score:
        print(f"  Score: {best_result.score:.1f} points")
    
    print(f"\nOptimized Parameters:")
    for param_name in parameter_bounds.keys():
        category, param = param_name.split('.')
        if category == 'mass':
            value = getattr(best_config.mass, param)
        elif category == 'powertrain':
            value = getattr(best_config.powertrain, param)
        elif category == 'control':
            value = getattr(best_config.control, param)
        elif category == 'aerodynamics':
            value = getattr(best_config.aerodynamics, param)
        elif category == 'suspension':
            value = getattr(best_config.suspension, param)
        else:
            value = "N/A"
        
        original_value = None
        if category == 'mass':
            original_value = getattr(base_config.mass, param)
        elif category == 'powertrain':
            original_value = getattr(base_config.powertrain, param)
        elif category == 'control':
            original_value = getattr(base_config.control, param)
        elif category == 'aerodynamics':
            original_value = getattr(base_config.aerodynamics, param)
        elif category == 'suspension':
            original_value = getattr(base_config.suspension, param)
        
        if isinstance(value, (int, float)):
            change = value - original_value if original_value is not None else 0
            change_pct = (change / original_value * 100) if original_value else 0
            print(f"  {param_name}: {value:.4f} (was {original_value:.4f}, change: {change:+.4f} ({change_pct:+.1f}%))")
        else:
            print(f"  {param_name}: {value}")
    
    print(f"\nOptimization Statistics:")
    print(f"  Total evaluations: {len(result.all_evaluations)}")
    print(f"  Optimization time: {result.optimization_info.get('elapsed_time', 0):.1f} s")
    print(f"  Success: {result.optimization_info.get('success', False)}")
    
    # Save optimized configuration
    output_path = Path(__file__).parent.parent / "config" / "vehicle_configs" / "optimized_vehicle.json"
    save_optimized_config(best_config, output_path)
    print(f"\nOptimized configuration saved to: {output_path}")
    
    return result


def save_optimized_config(config, output_path: Path):
    """Save optimized configuration to JSON file."""
    config_dict = {
        "mass": {
            "total_mass": config.mass.total_mass,
            "cg_x": config.mass.cg_x,
            "cg_z": config.mass.cg_z,
            "wheelbase": config.mass.wheelbase,
            "front_track": config.mass.front_track,
            "rear_track": config.mass.rear_track,
            "i_yaw": config.mass.i_yaw,
            "i_pitch": config.mass.i_pitch,
            "unsprung_mass_front": config.mass.unsprung_mass_front,
            "unsprung_mass_rear": config.mass.unsprung_mass_rear
        },
        "tires": {
            "radius_loaded": config.tires.radius_loaded,
            "mass": config.tires.mass,
            "mu_max": config.tires.mu_max,
            "mu_slip_optimal": config.tires.mu_slip_optimal,
            "rolling_resistance_coeff": config.tires.rolling_resistance_coeff
        },
        "powertrain": {
            "motor_torque_constant": config.powertrain.motor_torque_constant,
            "motor_max_current": config.powertrain.motor_max_current,
            "motor_max_speed": config.powertrain.motor_max_speed,
            "motor_efficiency": config.powertrain.motor_efficiency,
            "battery_voltage_nominal": config.powertrain.battery_voltage_nominal,
            "battery_internal_resistance": config.powertrain.battery_internal_resistance,
            "battery_max_current": config.powertrain.battery_max_current,
            "gear_ratio": config.powertrain.gear_ratio,
            "drivetrain_efficiency": config.powertrain.drivetrain_efficiency,
            "differential_ratio": config.powertrain.differential_ratio,
            "max_power_accumulator_outlet": config.powertrain.max_power_accumulator_outlet,
            "wheel_inertia": config.powertrain.wheel_inertia
        },
        "aerodynamics": {
            "cda": config.aerodynamics.cda,
            "cl_front": config.aerodynamics.cl_front,
            "cl_rear": config.aerodynamics.cl_rear,
            "air_density": config.aerodynamics.air_density
        },
        "suspension": {
            "anti_squat_ratio": config.suspension.anti_squat_ratio,
            "ride_height_front": config.suspension.ride_height_front,
            "ride_height_rear": config.suspension.ride_height_rear,
            "wheel_rate_front": config.suspension.wheel_rate_front,
            "wheel_rate_rear": config.suspension.wheel_rate_rear
        },
        "control": {
            "launch_torque_limit": config.control.launch_torque_limit,
            "target_slip_ratio": config.control.target_slip_ratio,
            "torque_ramp_rate": config.control.torque_ramp_rate,
            "traction_control_enabled": config.control.traction_control_enabled
        },
        "environment": {
            "air_density": config.environment.air_density,
            "ambient_temperature": config.environment.ambient_temperature,
            "track_grade": config.environment.track_grade,
            "wind_speed": config.environment.wind_speed,
            "surface_mu_scaling": config.environment.surface_mu_scaling
        },
        "simulation": {
            "dt": config.dt,
            "max_time": config.max_time,
            "target_distance": config.target_distance
        }
    }
    
    import json
    with open(output_path, 'w') as f:
        json.dump(config_dict, f, indent=2)


if __name__ == "__main__":
    result = main()

