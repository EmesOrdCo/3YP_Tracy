# Formula Student Acceleration Simulation

A physics-based simulation system for predicting Formula Student vehicle acceleration performance (0-75m) with respect to design parameters, powertrain constraints, and Formula Student rules.

## Features

- **Modular Architecture**: Separate modules for tires, powertrain, aerodynamics, chassis, and control
- **Rule Compliance**: Built-in validation against Formula Student rules (EV 2.2: 80kW power limit, D 5.3: scoring)
- **Parameterized Design**: All vehicle parameters externalized in JSON/YAML configuration files
- **Physics-Based**: RK4 integration with realistic tire, powertrain, and aerodynamic models
- **Scoring Calculator**: Automatic calculation of Formula Student acceleration event scores

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

Run a basic simulation:

```bash
python examples/basic_run.py
```

## Configuration

Vehicle parameters are defined in JSON or YAML configuration files. See `config/vehicle_configs/base_vehicle.json` for an example.

Key parameters:
- **Mass Properties**: Total mass, CG location, inertia
- **Tires**: Radius, friction coefficients, rolling resistance
- **Powertrain**: Motor torque, battery voltage, gear ratio, power limit (80kW)
- **Aerodynamics**: Drag area (CdA), downforce coefficients
- **Control**: Launch strategy, traction control

## Architecture

See `ARCHITECTURE.md` for detailed system architecture documentation.

## Modules

- **config/**: Configuration loading and validation
- **vehicle/**: Vehicle model components (tires, powertrain, aero, etc.)
- **dynamics/**: Dynamics solver with RK4 integration
- **rules/**: Formula Student rules compliance checking
- **simulation/**: Main simulation runner
- **analysis/**: Results processing and visualization (to be implemented)

## Formula Student Rules Compliance

- **EV 2.2**: Power limit at accumulator outlet ≤ 80 kW
- **D 5.3.1**: Time limit ≤ 25 s (disqualification)
- **D 5.3.2**: Acceleration scoring formula

## Example Usage

```python
from config.config_loader import load_config
from simulation.acceleration_sim import AccelerationSimulation

# Load configuration
config = load_config("config/vehicle_configs/base_vehicle.json")

# Create simulation
sim = AccelerationSimulation(config)

# Run simulation
result = sim.run(fastest_time=4.5)

# Check results
print(f"Time: {result.final_time:.3f} s")
print(f"Score: {result.score:.2f} points")
print(f"Compliant: {result.compliant}")
```

## Next Steps

1. Calibrate tire model with test data
2. Add Pacejka tire model support
3. Implement advanced control strategies
4. Add sensitivity analysis tools
5. Create visualization tools
6. Add batch processing for parameter sweeps

## License

[Your License Here]

## Contributors

[Your Team Name]


