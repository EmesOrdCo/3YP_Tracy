"""Quick optimization example - minimal code to find optimal setup."""

from pathlib import Path
import sys

print("=" * 70, flush=True)
print("FORMULA STUDENT ACCELERATION - OPTIMIZATION", flush=True)
print("=" * 70, flush=True)
print("", flush=True)

# Add parent directory to path  
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

print("Loading configuration...", flush=True)
# Import using package structure (now that package is installed)
from config.config_loader import load_config
from simulation.multi_objective_optimizer import MultiObjectiveOptimizer

# Load base config
base_config = load_config("config/vehicle_configs/base_vehicle.json")
print(f"✓ Configuration loaded: {base_config.mass.total_mass} kg", flush=True)

# Define which parameters to optimize and their ranges
parameter_bounds = {
    'mass.cg_x': (0.8, 1.4),           # CG position (rear = more rear grip)
    'mass.cg_z': (0.2, 0.4),           # CG height (lower = less load transfer)
    'powertrain.gear_ratio': (8.0, 12.0),  # Gear ratio
    'control.target_slip_ratio': (0.10, 0.20),  # Optimal slip
}

# Create optimizer
optimizer = MultiObjectiveOptimizer(
    base_config=base_config,
    parameter_bounds=parameter_bounds,
    objective='minimize_time_with_rules',  # Find fastest time while staying within rules
    enforce_rules=True  # Penalize rule violations (80kW power, 25s time limit)
)

# Run optimization (this will test hundreds/thousands of configurations)
print("\n" + "=" * 70, flush=True)
print("STARTING OPTIMIZATION", flush=True)
print("=" * 70, flush=True)
print(f"Parameters to optimize: {len(parameter_bounds)}", flush=True)
for param, (min_val, max_val) in parameter_bounds.items():
    print(f"  - {param}: [{min_val}, {max_val}]", flush=True)
print(f"\nSettings: 30 iterations × 20 population = ~600 simulations", flush=True)
print("Estimated time: 2-5 minutes", flush=True)
print("Progress updates will appear every 10 evaluations...\n", flush=True)
print("-" * 70, flush=True)

result = optimizer.optimize(
    method='differential_evolution',
    max_iterations=30,  # Increase for better results (but slower)
    population_size=20,  # More = better exploration but slower
    verbose=True
)

# Results
print(f"\n✓ Optimization complete!")
print(f"  Best time: {result.best_simulation_result.final_time:.3f}s")
print(f"  Power compliant: {result.best_simulation_result.power_compliant}")
print(f"  Total evaluations: {len(result.all_evaluations)}")

# Best configuration is in result.best_config
print(f"\nOptimized parameters:")
print(f"  CG X: {result.best_config.mass.cg_x:.3f}m")
print(f"  CG Z: {result.best_config.mass.cg_z:.3f}m")
print(f"  Gear ratio: {result.best_config.powertrain.gear_ratio:.2f}")

