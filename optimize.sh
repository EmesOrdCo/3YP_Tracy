#!/bin/bash
# Optimization script with proper PYTHONPATH setup

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd):$PYTHONPATH"

python3 << 'PYTHON_SCRIPT'
from config.config_loader import load_config
from simulation.multi_objective_optimizer import MultiObjectiveOptimizer
from pathlib import Path

print("=" * 70)
print("VEHICLE OPTIMIZATION - Finding Optimal Setup")
print("=" * 70)

# Load base config
config_path = Path("config/vehicle_configs/base_vehicle.json")
base_config = load_config(str(config_path))

print(f"\nBase configuration:")
print(f"  Mass: {base_config.mass.total_mass:.1f} kg")
print(f"  CG X: {base_config.mass.cg_x:.3f} m")
print(f"  CG Z: {base_config.mass.cg_z:.3f} m")
print(f"  Gear ratio: {base_config.powertrain.gear_ratio:.2f}")

# Define parameter bounds
parameter_bounds = {
    'mass.cg_x': (0.8, 1.4),
    'mass.cg_z': (0.2, 0.4),
    'powertrain.gear_ratio': (8.0, 12.0),
    'control.target_slip_ratio': (0.10, 0.20),
}

print(f"\nOptimizing {len(parameter_bounds)} parameters...")
print("Starting optimization (this will take a few minutes)...\n")

# Create optimizer
optimizer = MultiObjectiveOptimizer(
    base_config=base_config,
    parameter_bounds=parameter_bounds,
    objective='minimize_time_with_rules',
    enforce_rules=True
)

# Run optimization
result = optimizer.optimize(
    method='differential_evolution',
    max_iterations=30,
    population_size=20,
    verbose=True
)

# Display results
print("\n" + "=" * 70)
print("OPTIMIZATION RESULTS")
print("=" * 70)

print(f"\n✓ Best Time: {result.best_simulation_result.final_time:.3f} s")
print(f"✓ Power Compliant: {result.best_simulation_result.power_compliant}")
print(f"✓ Time Compliant: {result.best_simulation_result.time_compliant}")
print(f"✓ Total Evaluations: {len(result.all_evaluations)}")

print(f"\nOptimized Parameters:")
print(f"  CG X: {result.best_config.mass.cg_x:.3f} m (was {base_config.mass.cg_x:.3f} m)")
print(f"  CG Z: {result.best_config.mass.cg_z:.3f} m (was {base_config.mass.cg_z:.3f} m)")
print(f"  Gear Ratio: {result.best_config.powertrain.gear_ratio:.2f} (was {base_config.powertrain.gear_ratio:.2f})")
print(f"  Target Slip: {result.best_config.control.target_slip_ratio:.3f} (was {base_config.control.target_slip_ratio:.3f})")

print("\n" + "=" * 70)
print("Optimization complete!")
PYTHON_SCRIPT

