# API Documentation

This document provides detailed API documentation for the Formula Student Acceleration Simulation system.

## Table of Contents

- [Configuration](#configuration)
- [Vehicle Models](#vehicle-models)
- [Dynamics](#dynamics)
- [Simulation](#simulation)
- [Rules & Scoring](#rules--scoring)
- [Analysis](#analysis)

## Configuration

### `config.config_loader.load_config`

Load vehicle configuration from JSON or YAML file.

```python
from config.config_loader import load_config

config = load_config("config/vehicle_configs/base_vehicle.json")
```

**Parameters:**
- `config_path` (str | Path): Path to configuration file

**Returns:**
- `VehicleConfig`: Configuration object

**Raises:**
- `FileNotFoundError`: If config file doesn't exist
- `ValueError`: If config is invalid

### `config.vehicle_config.VehicleConfig`

Main configuration dataclass containing all vehicle parameters.

**Properties:**
- `mass`: MassProperties
- `tires`: TireProperties
- `powertrain`: PowertrainProperties
- `aerodynamics`: AerodynamicsProperties
- `suspension`: SuspensionProperties
- `control`: ControlProperties
- `environment`: EnvironmentProperties
- `dt`: float (simulation time step, default: 0.001 s)
- `max_time`: float (max simulation time, default: 30.0 s)
- `target_distance`: float (target distance, default: 75.0 m)

**Methods:**
- `validate() -> List[str]`: Validate configuration, returns list of errors

## Vehicle Models

### `vehicle.tire_model.TireModel`

Tire force model for longitudinal acceleration.

**Methods:**
- `calculate_slip_ratio(wheel_angular_velocity, vehicle_velocity) -> float`: Calculate slip ratio
- `calculate_longitudinal_force(normal_force, slip_ratio, velocity) -> Tuple[float, float]`: Calculate tire force and rolling resistance

### `vehicle.powertrain.PowertrainModel`

Powertrain model including motor, battery, and drivetrain.

**Methods:**
- `calculate_torque(requested_torque, motor_speed, vehicle_velocity) -> Tuple[float, float, float]`: Calculate available torque with limits
- `calculate_motor_speed(wheel_angular_velocity) -> float`: Convert wheel speed to motor speed

### `vehicle.aerodynamics.AerodynamicsModel`

Aerodynamic drag and downforce model.

**Methods:**
- `calculate_forces(velocity) -> Tuple[float, float, float]`: Calculate drag and downforce

### `vehicle.mass_properties.MassPropertiesModel`

Mass properties and load transfer calculations.

**Methods:**
- `calculate_normal_forces(longitudinal_acceleration, front_downforce, rear_downforce) -> Tuple[float, float]`: Calculate normal forces with load transfer

## Dynamics

### `dynamics.solver.DynamicsSolver`

Main dynamics solver using RK4 integration.

**Methods:**
- `solve() -> SimulationState`: Run simulation until target distance reached

### `dynamics.state.SimulationState`

State vector dataclass containing all simulation variables.

**Properties:**
- `position`: float (m)
- `velocity`: float (m/s)
- `acceleration`: float (m/s²)
- `wheel_angular_velocity_front/rear`: float (rad/s)
- `motor_speed/current/torque`: float
- `drive_force`, `drag_force`, `rolling_resistance`: float (N)
- `normal_force_front/rear`: float (N)
- `tire_force_front/rear`: float (N)
- `power_consumed`: float (W)
- `time`: float (s)

**Methods:**
- `to_dict() -> Dict`: Convert to dictionary
- `copy() -> SimulationState`: Create copy

## Simulation

### `simulation.acceleration_sim.AccelerationSimulation`

Main simulation class.

**Methods:**
- `run(fastest_time: Optional[float] = None) -> SimulationResult`: Run simulation
- `get_state_history() -> List[SimulationState]`: Get full state history

### `simulation.acceleration_sim.SimulationResult`

Simulation result dataclass.

**Properties:**
- `final_state`: SimulationState
- `compliant`: bool (overall compliance)
- `power_compliant`: bool
- `time_compliant`: bool
- `max_power_used`: float (W)
- `final_time`: float (s)
- `final_distance`: float (m)
- `final_velocity`: float (m/s)
- `score`: Optional[float] (points)
- `fastest_time`: Optional[float] (s)

### `simulation.batch_runner.BatchRunner`

Batch simulation runner for parameter sweeps.

**Methods:**
- `parameter_sweep(parameter_path, values, fastest_time) -> List[SimulationResult]`: Run parameter sweep
- `multi_parameter_sweep(parameters, fastest_time) -> List[SimulationResult]`: Run full factorial sweep
- `run_batch(configs, fastest_time, labels) -> List[SimulationResult]`: Run batch of simulations

### `simulation.optimizer.VehicleOptimizer`

Optimize vehicle parameters.

**Methods:**
- `optimize(parameter_bounds, objective, fastest_time, method) -> Tuple[VehicleConfig, SimulationResult, Dict]`: Optimize parameters

## Rules & Scoring

### `rules.power_limit.check_power_limit`

Check power limit compliance (EV 2.2).

```python
from rules.power_limit import check_power_limit

compliant, max_power, violation_time = check_power_limit(state_history, max_power=80e3)
```

**Returns:**
- `Tuple[bool, float, float]`: (compliant, max_power_used, time_of_violation)

### `rules.time_limits.check_time_limit`

Check time limit compliance (D 5.3.1).

```python
from rules.time_limits import check_time_limit

compliant, final_time = check_time_limit(final_state, max_time=25.0)
```

### `rules.scoring.calculate_acceleration_score`

Calculate Formula Student acceleration score (D 5.3.2).

```python
from rules.scoring import calculate_acceleration_score

score = calculate_acceleration_score(team_time=5.0, fastest_time=4.5, max_points=75.0)
```

## Analysis

### Results Processing

```python
from analysis.results import (
    extract_time_series_data,
    save_results_to_json,
    compare_results,
    calculate_performance_metrics
)
```

**Functions:**
- `extract_time_series_data(state_history) -> Dict`: Extract time series arrays
- `save_results_to_json(result, output_path, include_state_history, state_history)`: Save results
- `compare_results(results, labels) -> pd.DataFrame`: Compare multiple results

### Visualization

```python
from analysis.visualization import (
    plot_velocity_vs_time,
    plot_position_vs_time,
    plot_forces_vs_time,
    plot_power_vs_time,
    create_comprehensive_plot
)
```

**Functions:**
- `plot_velocity_vs_time(state_history, ax, label) -> plt.Axes`: Plot velocity
- `create_comprehensive_plot(state_history, result, power_limit, save_path) -> plt.Figure`: Create multi-panel plot

### Sensitivity Analysis

```python
from analysis.sensitivity import (
    parameter_sweep,
    multi_parameter_sensitivity,
    rank_sensitivities
)
```

**Functions:**
- `parameter_sweep(base_config, parameter_path, values, fastest_time) -> SensitivityResult`: Run parameter sweep
- `rank_sensitivities(sensitivity_results, output_metric) -> pd.DataFrame`: Rank parameters by sensitivity

### Validation

```python
from analysis.validation import (
    ValidationData,
    validate_simulation,
    plot_validation
)
```

**Functions:**
- `validate_simulation(sim_state_history, test_data, metrics) -> Dict[str, ValidationResult]`: Validate simulation
- `ValidationData.from_csv(file_path, ...) -> ValidationData`: Load test data from CSV

## Examples

### Basic Simulation

```python
from config.config_loader import load_config
from simulation.acceleration_sim import AccelerationSimulation

config = load_config("config/vehicle_configs/base_vehicle.json")
sim = AccelerationSimulation(config)
result = sim.run(fastest_time=4.5)

print(f"Time: {result.final_time:.3f} s")
print(f"Score: {result.score:.2f} points")
```

### Parameter Sweep

```python
from simulation.batch_runner import BatchRunner

runner = BatchRunner(base_config)
gear_ratios = [8.0, 9.0, 10.0, 11.0, 12.0]
results = runner.parameter_sweep('powertrain.gear_ratio', gear_ratios, fastest_time=4.5)
```

### Visualization

```python
from analysis.visualization import create_comprehensive_plot

state_history = sim.get_state_history()
fig = create_comprehensive_plot(
    state_history,
    result=result,
    power_limit=80000.0,
    save_path="results/simulation.png"
)
```

## Error Handling

Most functions raise standard exceptions:
- `ValueError`: Invalid parameter values
- `FileNotFoundError`: Missing configuration files
- `TypeError`: Incorrect argument types

## Version

Current version: 0.1.0

