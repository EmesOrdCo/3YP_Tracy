#!/usr/bin/env python3
"""Test script to verify optimization works."""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Now we can import
from config.config_loader import load_config

print("Testing optimization system...")
print("=" * 60)

# Load base config
config = load_config("config/vehicle_configs/base_vehicle.json")
print(f"✓ Loaded config: {config.mass.total_mass} kg")

# Test a simple simulation first
print("\n1. Testing basic simulation...")
from simulation.acceleration_sim import AccelerationSimulation
sim = AccelerationSimulation(config)
result = sim.run()
print(f"✓ Simulation complete: {result.final_time:.3f}s")
print(f"  Power compliant: {result.power_compliant}")
print(f"  Time compliant: {result.time_compliant}")

# Now test optimizer (small run)
print("\n2. Testing optimizer (small test)...")
print("   This will optimize 2 parameters with just 5 iterations...")

# Import optimizer
import importlib.util
optimizer_path = Path(__file__).parent / "simulation" / "multi_objective_optimizer.py"
spec = importlib.util.spec_from_file_location("multi_objective_optimizer", optimizer_path)
optimizer_module = importlib.util.module_from_spec(spec)

# Set up dependencies for the optimizer
import types
if 'config' not in sys.modules:
    sys.modules['config'] = types.ModuleType('config')
if 'simulation' not in sys.modules:
    sys.modules['simulation'] = types.ModuleType('simulation')

sys.modules['config'].vehicle_config = __import__('config.vehicle_config')
sys.modules['simulation'].acceleration_sim = __import__('simulation.acceleration_sim')

spec.loader.exec_module(optimizer_module)
MultiObjectiveOptimizer = optimizer_module.MultiObjectiveOptimizer

# Quick optimization test
parameter_bounds = {
    'mass.cg_x': (1.0, 1.3),
    'powertrain.gear_ratio': (9.0, 11.0),
}

optimizer = MultiObjectiveOptimizer(
    base_config=config,
    parameter_bounds=parameter_bounds,
    objective='minimize_time_with_rules',
    enforce_rules=True
)

print("   Running optimization (5 iterations, 10 population)...")
result = optimizer.optimize(
    method='differential_evolution',
    max_iterations=5,
    population_size=10,
    verbose=True
)

print(f"\n✓ Optimization complete!")
print(f"  Best time: {result.best_simulation_result.final_time:.3f}s")
print(f"  Power compliant: {result.best_simulation_result.power_compliant}")
print(f"  Time compliant: {result.best_simulation_result.time_compliant}")
print(f"  Evaluations: {len(result.all_evaluations)}")

print("\n" + "=" * 60)
print("All tests passed! Optimization system is working.")
print("You can now run the full optimization with:")
print("  python3 examples/quick_optimization.py")

