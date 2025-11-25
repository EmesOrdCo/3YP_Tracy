# Vehicle Optimization Guide

## Overview

This guide explains how to use the multi-objective optimization system to find the optimal vehicle configuration within Formula Student regulations.

## The Challenge

With dozens of parameters (mass distribution, powertrain, aerodynamics, suspension, control), there are potentially **millions** of combinations. Brute-force testing all combinations is impractical.

## Solution: Intelligent Search Algorithms

Instead of testing all combinations, we use **evolutionary algorithms** (genetic algorithms) that:
- Start with a random population of configurations
- "Evolve" better solutions over generations
- Focus search on promising regions
- Handle constraints automatically (Formula Student rules)

## How It Works

### 1. Define Parameter Bounds

You specify which parameters to optimize and their ranges:

```python
parameter_bounds = {
    'mass.cg_x': (0.8, 1.4),      # CG position range
    'mass.cg_z': (0.2, 0.4),      # CG height range
    'powertrain.gear_ratio': (8.0, 12.0),
    'control.target_slip_ratio': (0.10, 0.20),
    # ... more parameters
}
```

### 2. Choose Objective

The optimizer minimizes an objective function:
- **`minimize_time`**: Find fastest 75m time
- **`maximize_score`**: Maximize Formula Student score
- **`minimize_time_with_rules`**: Fastest time while staying within rules

### 3. Constraint Handling

The optimizer automatically:
- Checks power limit (80kW, EV 2.2)
- Checks time limit (25s, D 5.3.1)
- Validates all parameters (mass > 0, CG within wheelbase, etc.)
- **Penalizes** invalid configurations instead of rejecting them
  - This allows the algorithm to learn what NOT to do
  - Invalid configs get large penalties, so optimizer avoids them

### 4. Parallel Execution

The optimizer uses multiple CPU cores to run simulations in parallel, speeding up the search significantly.

## Usage Example

See `examples/comprehensive_optimization.py` for a complete example.

Basic usage:

```python
from config.config_loader import load_config
from simulation.multi_objective_optimizer import MultiObjectiveOptimizer

# Load base config
base_config = load_config("config/vehicle_configs/base_vehicle.json")

# Define what to optimize
parameter_bounds = {
    'mass.cg_x': (0.8, 1.4),
    'mass.cg_z': (0.2, 0.4),
    'powertrain.gear_ratio': (8.0, 12.0),
    # ... more parameters
}

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
    max_iterations=50,
    population_size=30
)

# Best configuration is in result.best_config
print(f"Best time: {result.best_simulation_result.final_time:.3f}s")
```

## Optimization Strategies

### 1. Start Broad, Then Narrow

**Phase 1: Explore the design space**
- Include many parameters
- Wide bounds
- Fewer iterations (20-30)
- Larger population (30-50)

**Phase 2: Refine around best**
- Narrow bounds around best result
- More iterations (50-100)
- Smaller population (15-25)

### 2. Parameter Selection

Optimize parameters that have significant impact:
- **High impact**: CG position (cg_x, cg_z), gear ratio, launch torque
- **Medium impact**: Slip ratio, aero balance, anti-squat
- **Low impact**: Track width, wheel inertia (unless critical)

### 3. Multi-Stage Optimization

1. **Stage 1**: Mass distribution only
2. **Stage 2**: Powertrain parameters
3. **Stage 3**: Control strategy
4. **Stage 4**: Everything together (fine-tuning)

## Key Parameters

### Differential Evolution Settings

- **`max_iterations`**: Number of generations (more = better, slower)
  - Start: 30-50
  - Final: 100-200
- **`population_size`**: Solutions per generation (more = better exploration)
  - Rule of thumb: 5-10x number of parameters
  - More = slower but better results
- **`method`**: Algorithm
  - `differential_evolution`: Best for global search (recommended)
  - `minimize`: Local optimization (faster, may miss global optimum)

## Formula Student Rule Compliance

The optimizer automatically enforces:

1. **Power Limit (EV 2.2)**: 80kW maximum
   - Violations get large penalty (1e5)

2. **Time Limit (D 5.3.1)**: 25s disqualification
   - Violations get penalty (1e4)

3. **Parameter Validation**:
   - Mass > 0
   - CG within wheelbase
   - Positive tire radius
   - Positive gear ratio
   - etc.

## Performance Considerations

### Computation Time

- Each simulation takes ~0.1-1 seconds
- With 50 iterations × 30 population = 1500 simulations
- On 8-core machine: ~3-5 minutes
- On single core: ~15-25 minutes

### Speeding Up

1. **Parallel execution**: Use all CPU cores (default)
2. **Reduce iterations**: Start with 20-30, increase if needed
3. **Smaller population**: Fewer candidates per generation
4. **Fewer parameters**: Optimize only critical ones first

### Accuracy vs Speed Trade-off

- **Fast exploration**: 20-30 iterations, 20-30 population
- **Balanced**: 50 iterations, 30 population (recommended)
- **Thorough**: 100+ iterations, 50+ population

## Interpreting Results

### Best Configuration

`result.best_config` contains the optimized vehicle configuration. Compare to base:

```python
print(f"CG X: {base_config.mass.cg_x:.3f} → {result.best_config.mass.cg_x:.3f}")
print(f"Gear ratio: {base_config.powertrain.gear_ratio:.2f} → {result.best_config.powertrain.gear_ratio:.2f}")
```

### All Evaluations

`result.all_evaluations` contains ALL tested configurations. Useful for:
- Understanding parameter sensitivities
- Finding near-optimal alternatives
- Analyzing trade-offs

### Optimization Info

`result.optimization_info` contains:
- Number of function evaluations
- Success status
- Convergence information

## Advanced: Custom Objectives

You can define custom objectives by modifying the objective function:

```python
def custom_objective(result: SimulationResult) -> float:
    # Minimize time, but penalize high power usage
    time_penalty = result.final_time
    power_penalty = 0.001 * max(0, result.max_power - 75000)  # Prefer < 75kW
    return time_penalty + power_penalty
```

## Troubleshooting

### "No improvement found"

- Increase `max_iterations`
- Increase `population_size`
- Check parameter bounds aren't too restrictive
- Try different starting point (different base_config)

### "All configurations invalid"

- Check parameter bounds are reasonable
- Verify base_config is valid
- Rule penalties might be too strict - check power/time limits

### "Takes too long"

- Reduce `max_iterations`
- Reduce `population_size`
- Optimize fewer parameters at once
- Use faster simulation settings (larger dt)

## Next Steps

1. Run `examples/comprehensive_optimization.py` to see it in action
2. Modify parameter bounds for your specific vehicle
3. Experiment with different objectives
4. Analyze results to understand parameter sensitivities

