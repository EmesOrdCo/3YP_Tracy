#!/usr/bin/env python3
"""Standalone optimization script that works around import issues."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import what we need using direct module loading
import importlib.util

def load_module(name, filepath):
    """Load a module from a file path."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load all dependencies we need
config_loader = load_module('config_loader', project_root / 'config' / 'config_loader.py')
vehicle_config = load_module('vehicle_config', project_root / 'config' / 'vehicle_config.py')

# Load config
load_config = config_loader.load_config
VehicleConfig = vehicle_config.VehicleConfig

# Load simulation dependencies
state = load_module('state', project_root / 'dynamics' / 'state.py')
solver = load_module('solver', project_root / 'dynamics' / 'solver.py')

# Now we can load acceleration_sim with its dependencies available
accel_sim = load_module('acceleration_sim', project_root / 'simulation' / 'acceleration_sim.py')
AccelerationSimulation = accel_sim.AccelerationSimulation
SimulationResult = accel_sim.SimulationResult

# Load optimizer
optimizer = load_module('multi_objective_optimizer', project_root / 'simulation' / 'multi_objective_optimizer.py')
MultiObjectiveOptimizer = optimizer.MultiObjectiveOptimizer

print("=" * 70)
print("VEHICLE OPTIMIZATION")
print("=" * 70)

# Load base config
config_path = project_root / "config" / "vehicle_configs" / "base_vehicle.json"
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
print("Starting optimization (this will take a few minutes)...")

# Create optimizer
opt = MultiObjectiveOptimizer(
    base_config=base_config,
    parameter_bounds=parameter_bounds,
    objective='minimize_time_with_rules',
    enforce_rules=True
)

# Run optimization
result = opt.optimize(
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

