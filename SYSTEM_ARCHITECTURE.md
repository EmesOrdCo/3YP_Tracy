# System Architecture Guide

## Overview

This document provides a detailed guide to building and extending the Formula Student acceleration simulation system. The architecture is designed to be modular, extensible, and compliant with Formula Student rules.

## System Components

### 1. Configuration Layer (`config/`)

**Purpose**: Load and validate vehicle parameters from JSON/YAML files.

**Key Files**:
- `vehicle_config.py`: Data classes for all vehicle parameters
- `config_loader.py`: Loader that parses JSON/YAML and creates configuration objects
- `vehicle_configs/base_vehicle.json`: Example configuration file

**Usage**:
```python
from config.config_loader import load_config

config = load_config("config/vehicle_configs/base_vehicle.json")
```

**Extending**: Add new parameters by:
1. Adding fields to the appropriate dataclass in `vehicle_config.py`
2. Updating the JSON schema in example config files
3. Adding validation in the `validate()` method

### 2. Vehicle Model Layer (`vehicle/`)

**Purpose**: Physics models for each vehicle subsystem.

#### Mass Properties (`mass_properties.py`)
- Calculates static load distribution
- Calculates longitudinal load transfer
- Calculates normal forces on axles

#### Tire Model (`tire_model.py`)
- Simplified friction model (linear increase to optimal slip, then decrease)
- Calculates longitudinal tire forces
- Calculates rolling resistance
- **Future**: Upgrade to Pacejka model when tire data available

#### Powertrain Model (`powertrain.py`)
- Motor torque calculation with current limits
- Battery voltage and current limits
- Power limit enforcement (80kW rule EV 2.2)
- Gear ratio and drivetrain efficiency
- **Future**: Add motor efficiency maps, field weakening

#### Aerodynamics Model (`aerodynamics.py`)
- Drag force calculation (CdA)
- Downforce calculation (front/rear CL)
- **Future**: Ride height sensitivity, ground effect

#### Suspension Model (`suspension.py`)
- Anti-squat effects
- **Future**: Full geometry model, compliance effects

**Extending**: Add new models by:
1. Creating a new class in `vehicle/`
2. Implementing the physics equations
3. Adding configuration parameters in `vehicle_config.py`
4. Integrating into the dynamics solver

### 3. Dynamics Solver Layer (`dynamics/`)

**Purpose**: Numerical integration of vehicle dynamics equations.

#### State Management (`state.py`)
- `SimulationState`: Dataclass containing all state variables
- Position, velocity, acceleration
- Wheel speeds, motor state
- Forces, normal forces, power

#### Solver (`solver.py`)
- RK4 integration method
- Time-stepping loop until 75m reached
- Force calculation aggregation
- Constraint application (power limits, slip control)

**Key Methods**:
- `solve()`: Main simulation loop
- `_calculate_derivatives()`: Calculate time derivatives of state
- `_rk4_step()`: Perform one RK4 integration step

**Extending**: 
- Add new state variables to `SimulationState`
- Modify `_calculate_derivatives()` to include new physics
- Change integration method (e.g., adaptive time stepping)

### 4. Rules Compliance Layer (`rules/`)

**Purpose**: Check Formula Student rules compliance and calculate scores.

#### Power Limit (`power_limit.py`)
- Checks 80kW power limit (EV 2.2)
- Returns compliance status and violation time

#### Time Limits (`time_limits.py`)
- Checks 25s disqualification limit (D 5.3.1)
- Returns compliance status

#### Scoring (`scoring.py`)
- Calculates acceleration event score (D 5.3.2)
- Formula: `M_ACCELERATION_SCORE = 0.95 * Pmax * ((Tmax / Tteam - 1) / 0.5) + 0.05 * Pmax`

**Extending**: Add new rule checks by:
1. Creating a new module in `rules/`
2. Implementing the check function
3. Integrating into `AccelerationSimulation.run()`

### 5. Simulation Layer (`simulation/`)

**Purpose**: High-level simulation interface.

#### Acceleration Simulation (`acceleration_sim.py`)
- Main simulation class
- Runs dynamics solver
- Checks rules compliance
- Calculates scores
- Returns `SimulationResult` object

**Usage**:
```python
from simulation.acceleration_sim import AccelerationSimulation

sim = AccelerationSimulation(config)
result = sim.run(fastest_time=4.5)
print(f"Time: {result.final_time:.3f} s")
print(f"Score: {result.score:.2f} points")
```

### 6. Analysis Layer (`analysis/`) - To Be Implemented

**Purpose**: Results processing, sensitivity analysis, visualization.

**Planned Features**:
- Parameter sensitivity analysis
- Batch processing for parameter sweeps
- Visualization (velocity vs time, force vs time, etc.)
- Validation against test data
- Optimization wrapper

## Data Flow

```
1. Load Configuration (JSON/YAML)
   ↓
2. Initialize Vehicle Models
   - TireModel
   - PowertrainModel
   - AerodynamicsModel
   - MassPropertiesModel
   - SuspensionModel
   ↓
3. Initialize Dynamics Solver
   - State: [x=0, v=0, ω=0, ...]
   - Time: t=0
   ↓
4. Integration Loop (until x >= 75m)
   ├─> Calculate Forces
   │   ├─> Aerodynamic forces (drag, downforce)
   │   ├─> Normal forces (load transfer)
   │   ├─> Tire forces (slip, friction)
   │   └─> Powertrain torque (with power limit)
   ├─> Apply Constraints
   │   ├─> Power limit (80kW)
   │   └─> Slip control
   ├─> Calculate Derivatives
   │   └─> d(state)/dt = f(state, forces)
   ├─> Integrate State (RK4)
   │   └─> state = state + dt * d(state)/dt
   └─> Check Termination
       └─> x >= 75m or t >= max_time
   ↓
5. Post-Process Results
   ├─> Check Rules Compliance
   │   ├─> Power limit (EV 2.2)
   │   └─> Time limit (D 5.3.1)
   ├─> Calculate Score (D 5.3.2)
   └─> Return SimulationResult
```

## Key Design Decisions

### 1. Modularity
- Each subsystem is a separate module
- Easy to swap models (e.g., simple tire model → Pacejka)
- Easy to add new subsystems

### 2. Parameterization
- All parameters in configuration files
- No hardcoded values
- Easy to test different vehicle configurations

### 3. Rule Compliance
- Built into the simulation
- Automatic checking and reporting
- Prevents invalid designs

### 4. Integration Method
- RK4 for accuracy
- Fixed time step (can be made adaptive)
- Stable for stiff systems

### 5. State Management
- Single state object contains all variables
- Easy to log and analyze
- Clear data flow

## Extending the System

### Adding a New Vehicle Subsystem

1. **Create Model Class**:
```python
# vehicle/new_subsystem.py
from ..config.vehicle_config import NewSubsystemProperties

class NewSubsystemModel:
    def __init__(self, config: NewSubsystemProperties):
        self.config = config
    
    def calculate_effect(self, state):
        # Your physics here
        return effect
```

2. **Add Configuration**:
```python
# config/vehicle_config.py
@dataclass
class NewSubsystemProperties:
    parameter1: float
    parameter2: float = 0.0
```

3. **Integrate into Solver**:
```python
# dynamics/solver.py
def __init__(self, config):
    self.new_subsystem = NewSubsystemModel(config.new_subsystem)

def _calculate_derivatives(self, state):
    effect = self.new_subsystem.calculate_effect(state)
    # Use effect in force calculations
```

### Adding a New Rule Check

1. **Create Rule Module**:
```python
# rules/new_rule.py
def check_new_rule(state_history):
    # Check rule
    compliant = ...
    return compliant, violation_info
```

2. **Integrate into Simulation**:
```python
# simulation/acceleration_sim.py
from ..rules.new_rule import check_new_rule

def run(self):
    # ... existing code ...
    compliant, info = check_new_rule(self.solver.state_history)
    # Add to result
```

### Adding Visualization

1. **Create Visualization Module**:
```python
# analysis/visualization.py
import matplotlib.pyplot as plt

def plot_velocity_vs_time(state_history):
    times = [s.time for s in state_history]
    velocities = [s.velocity for s in state_history]
    plt.plot(times, velocities)
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.show()
```

2. **Use in Analysis**:
```python
from analysis.visualization import plot_velocity_vs_time

result = sim.run()
plot_velocity_vs_time(sim.get_state_history())
```

## Testing Strategy

### Unit Tests
- Test each model independently
- Test with known inputs/outputs
- Test edge cases (zero velocity, max power, etc.)

### Integration Tests
- Test full simulation with known configuration
- Compare results with analytical solutions (if available)
- Test rules compliance checking

### Validation Tests
- Compare simulation results with test data
- Calibrate models using test data
- Validate against previous season data

## Performance Considerations

### Optimization Opportunities
1. **Vectorization**: Use NumPy arrays for batch simulations
2. **Caching**: Cache expensive calculations (e.g., tire force lookup tables)
3. **Adaptive Time Stepping**: Reduce time step when needed, increase when stable
4. **Parallel Processing**: Run multiple simulations in parallel for parameter sweeps

### Current Limitations
- Fixed time step (may be inefficient for stiff systems)
- Simple tire model (may not be accurate for high slip)
- No motor efficiency maps (constant efficiency assumed)
- No thermal effects (battery, motor, tires)

## Next Steps

1. **Calibration**: Calibrate models with test data
2. **Advanced Models**: Add Pacejka tire model, motor efficiency maps
3. **Control Strategy**: Implement advanced launch control, traction control
4. **Sensitivity Analysis**: Analyze which parameters have biggest impact
5. **Optimization**: Optimize vehicle parameters for best score
6. **Validation**: Compare simulation with actual test data
7. **Visualization**: Create comprehensive plotting tools
8. **Documentation**: Add API documentation, user guide

## Resources

- Formula Student Rules 2025: `FS-Rules_2025_v1.0.pdf`
- Architecture Documentation: `ARCHITECTURE.md`
- API Documentation: `docs/API.md` (to be created)
- Examples: `examples/`


