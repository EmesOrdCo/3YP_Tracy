# Acceleration Simulation System Architecture

## System Overview

A modular, physics-based simulation system for predicting Formula Student vehicle acceleration performance (0-75m) with respect to design parameters, powertrain constraints, and Formula Student rules.

## Architecture Principles

1. **Modularity**: Each vehicle subsystem (tires, powertrain, chassis, aero) is a separate module
2. **Parameterization**: All design parameters are externalized in configuration files
3. **Rule Compliance**: Built-in validation against Formula Student rules (EV 2.2, D 5.3)
4. **Extensibility**: Easy to add new models or modify existing ones
5. **Validation**: Built-in comparison with test data and sensitivity analysis

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                       │
│  (Vehicle Config JSON/YAML, Parameter Files)                │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Vehicle Model Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Mass    │  │  Tires   │  │Powertrain│  │   Aero   │   │
│  │  Props   │  │  Model   │  │  Model   │  │  Model   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │Suspension│  │ Control  │  │  Chassis │                 │
│  │  Model   │  │ Strategy │  │ Geometry │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                Dynamics Solver Layer                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Integration Loop (RK4/Forward Euler)                │  │
│  │  - State: [x, v, ω_wheel, ...]                       │  │
│  │  - Forces: F_drive, F_aero, F_tire, F_rr             │  │
│  │  - Constraints: Power limit, slip control             │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│              Rule Compliance & Scoring Layer                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Power Limit  │  │ Time Limits  │  │   Scoring    │     │
│  │  Checker     │  │   (25s DQ)   │  │  Calculator  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Results & Analysis Layer                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Results    │  │  Sensitivity │  │  Validation  │     │
│  │  Processor   │  │   Analysis   │  │   Compare    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Module Breakdown

### 1. Configuration System (`config/`)
- **Purpose**: Load and validate vehicle parameters
- **Components**:
  - `vehicle_config.py`: Vehicle configuration class
  - `config_loader.py`: JSON/YAML loader with validation
  - Example config files: `vehicle_configs/`

### 2. Vehicle Model Modules (`vehicle/`)
- **mass_properties.py**: Mass, CG, inertia calculations
- **tire_model.py**: Tire force models (Pacejka, empirical)
- **powertrain.py**: Motor, battery, drivetrain models
- **aerodynamics.py**: Drag and downforce models
- **suspension.py**: Load transfer, geometry effects
- **chassis.py**: Wheelbase, track, geometry parameters
- **control.py**: Launch strategy, traction control

### 3. Dynamics Solver (`dynamics/`)
- **solver.py**: Main integration loop
- **state.py**: State vector management
- **forces.py**: Force calculation aggregator
- **constraints.py**: Power limits, slip constraints

### 4. Rules & Scoring (`rules/`)
- **power_limit.py**: 80kW power limit enforcement (EV 2.2)
- **time_limits.py**: 25s disqualification check (D 5.3.1)
- **scoring.py**: Acceleration scoring formula (D 5.3.2)

### 5. Results & Analysis (`analysis/`)
- **results.py**: Result processing and storage
- **sensitivity.py**: Parameter sensitivity analysis
- **validation.py**: Compare simulation vs. test data
- **visualization.py**: Plotting and reporting

### 6. Main Simulation (`simulation/`)
- **acceleration_sim.py**: Main simulation runner
- **batch_runner.py**: Batch simulations for parameter sweeps
- **optimizer.py**: Design optimization wrapper

## Data Flow

```
1. Load Configuration
   └─> VehicleConfig object

2. Initialize Vehicle Models
   └─> TireModel, PowertrainModel, AeroModel, etc.

3. Initialize Solver
   └─> State vector: [x, v, ω_front, ω_rear, ...]
   └─> Time: t = 0

4. Integration Loop (until x >= 75m)
   ├─> Calculate forces (tire, aero, drag, etc.)
   ├─> Apply constraints (power limit, slip control)
   ├─> Integrate state: d(state)/dt = f(state, forces)
   ├─> Update state: state = state + dt * d(state)/dt
   └─> Check rules (power < 80kW, time < 25s)

5. Post-Process Results
   ├─> Extract final time, distance, velocity
   ├─> Calculate score using Formula Student formula
   └─> Generate reports/plots
```

## File Structure

```
3YP_Code/
├── ARCHITECTURE.md           # This file
├── README.md                 # Project overview
├── requirements.txt          # Python dependencies
├── config/
│   ├── __init__.py
│   ├── vehicle_config.py     # Configuration classes
│   ├── config_loader.py      # Config file loader
│   └── vehicle_configs/      # Example config files
│       └── base_vehicle.json
├── vehicle/
│   ├── __init__.py
│   ├── mass_properties.py    # Mass, CG, inertia
│   ├── tire_model.py         # Tire force models
│   ├── powertrain.py         # Motor, battery, drivetrain
│   ├── aerodynamics.py       # Aero forces
│   ├── suspension.py         # Load transfer, geometry
│   ├── chassis.py            # Geometry parameters
│   └── control.py            # Control strategies
├── dynamics/
│   ├── __init__.py
│   ├── solver.py             # Main integration loop
│   ├── state.py              # State vector management
│   ├── forces.py             # Force calculations
│   └── constraints.py        # Constraints application
├── rules/
│   ├── __init__.py
│   ├── power_limit.py        # 80kW limit (EV 2.2)
│   ├── time_limits.py        # 25s DQ (D 5.3.1)
│   └── scoring.py            # Scoring formula (D 5.3.2)
├── analysis/
│   ├── __init__.py
│   ├── results.py            # Result processing
│   ├── sensitivity.py        # Sensitivity analysis
│   ├── validation.py         # Validation tools
│   └── visualization.py      # Plotting
├── simulation/
│   ├── __init__.py
│   ├── acceleration_sim.py   # Main simulation
│   ├── batch_runner.py       # Batch simulations
│   └── optimizer.py          # Optimization
├── tests/
│   ├── __init__.py
│   ├── test_tire_model.py
│   ├── test_powertrain.py
│   ├── test_dynamics.py
│   └── test_scoring.py
├── examples/
│   ├── basic_run.py          # Simple simulation example
│   ├── parameter_sweep.py    # Parameter study example
│   └── sensitivity_analysis.py
└── docs/
    └── API.md                # API documentation
```

## Implementation Phases

### Phase 1: Core Infrastructure
- [x] Architecture design
- [ ] Directory structure
- [ ] Configuration system
- [ ] Basic vehicle model classes

### Phase 2: Vehicle Models
- [ ] Mass properties model
- [ ] Tire model (start with simple, add Pacejka later)
- [ ] Powertrain model
- [ ] Aero model
- [ ] Suspension/load transfer

### Phase 3: Dynamics Solver
- [ ] State vector management
- [ ] Force calculation
- [ ] Integration loop (RK4)
- [ ] Constraint application

### Phase 4: Rules & Scoring
- [ ] Power limit enforcement
- [ ] Time limit checking
- [ ] Scoring calculator

### Phase 5: Analysis & Validation
- [ ] Results processing
- [ ] Sensitivity analysis
- [ ] Visualization
- [ ] Validation tools

### Phase 6: Optimization & Batch Processing
- [ ] Batch runner
- [ ] Parameter sweeps
- [ ] Optimization wrapper

## Key Design Decisions

1. **Integration Method**: Use RK4 for accuracy, with adaptive time stepping for stability
2. **Tire Model**: Start with simplified Fx = μ·Fz, upgrade to Pacejka when tire data available
3. **Power Limiting**: Apply at accumulator outlet (EV 2.2), clip torque to enforce limit
4. **State Vector**: [x, v, ω_front, ω_rear, ...] - extend as needed
5. **Configuration**: JSON/YAML for human-readable, Python classes for programmatic access

## Dependencies

- `numpy`: Numerical computations
- `scipy`: Integration, optimization
- `matplotlib`: Visualization
- `pandas`: Data handling
- `pyyaml`: Configuration file parsing
- `json`: JSON configuration support

## Next Steps

1. Set up directory structure
2. Create base vehicle configuration template
3. Implement core vehicle model classes
4. Build basic dynamics solver
5. Add rule compliance checking
6. Create scoring calculator
7. Test with known parameters
8. Validate against test data (when available)


