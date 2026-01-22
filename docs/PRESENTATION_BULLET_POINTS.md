# Presentation Bullet Points - Ready to Use

This document contains all bullet points organized by slide, ready to copy into your presentation.

---

## SLIDE 2: Event Overview, Rules, and Objectives

### SECTION 1: Event Description
**Subheading**: "The Competition Event"

- Formula Student Acceleration Event (Rule D 5)
- 75-meter straight-line acceleration track
- Single run format per attempt
- Vehicle staged 0.30 meters behind starting line
- Track width: minimum 3 meters
- Cones placed along track at ~5 meter intervals

---

### SECTION 2: Key Rules & Constraints
**Subheading**: "Competition Rules"

**Power Limit (Rule EV 2.2):**
- **Maximum 80 kW at accumulator outlet**
- This is a hard limit - vehicles cannot exceed this power
- The simulation checks this throughout the run

**Time Limit (Rule D 5.3.1):**
- **Runs exceeding 25 seconds are disqualified**
- The simulation stops if this limit is reached

**Scoring Formula (Rule D 5.3.2):**
**Subheading**: "Manual Mode Scoring Formula"

```
M_ACCELERATION_SCORE = 0.95 × Pmax × ((Tmax/Tteam - 1) / 0.5) + 0.05 × Pmax
```

**Where:**
- Pmax = 75 points (maximum points for manual mode acceleration event)
- Tmax = 1.5 × fastest time (1.5 times the fastest vehicle's time in competition)
- Tteam = team's best time including penalties (capped at Tmax, cannot exceed Tmax)

**Explanation**: Teams get more points for faster times. The formula ensures that teams within 50% of the fastest time can still score points, with the fastest team getting close to the maximum 75 points.

---

### SECTION 3: Simulation Objectives
**Subheading**: "What This Simulation Does"

- Predict vehicle acceleration performance from 0 to 75 meters
- Optimize design parameters within rule constraints (80kW power limit, 25s time limit)
- Validate powertrain power consumption against 80kW limit throughout the run
- Calculate competition scores based on predicted performance time
- Enable rapid design iteration and parameter sensitivity analysis
- Help engineers understand which vehicle parameters most affect acceleration performance

---

## SLIDE 3: Main System Flow (High Level)

### Key Points (optional bullet list):
- Configuration-driven: All parameters in JSON/YAML files
- Validated: System checks parameters before simulation
- Physics-based: Uses realistic vehicle models
- Rule-compliant: Automatically checks competition rules
- Score-ready: Calculates Formula Student scores

**Brief Description:**
"The simulation starts with a configuration file containing all vehicle parameters. The system validates these parameters, initializes physics models, solves the vehicle dynamics until the vehicle completes 75 meters, checks Formula Student rule compliance, and calculates the competition score."

---

## SLIDE 4: Solver Loop Detail

### Key Technical Points (optional bullet list):
- **RK4 Integration**: 4th-order Runge-Kutta method for accurate numerical integration
- **State History**: Complete state stored at each timestep for analysis
- **Iterative Process**: Small timesteps (typically 0.001-0.01 seconds) for accuracy
- **Termination Conditions**: Stops when position ≥ 75m OR time ≥ 25s

**Main Explanation:**
"This diagram shows how the simulation advances through time. The solver uses RK4 (Runge-Kutta 4th order) numerical integration to solve the differential equations of motion. Each iteration calculates how the vehicle's state changes over a small time step, then updates the position, velocity, and other state variables. The loop continues until the vehicle completes 75 meters or exceeds the 25-second time limit."

---

## SLIDE 5: Timestep Calculation Detail

### Key Model Interactions (optional bullet list):
- **Aerodynamics Model**: Calculates drag (slows vehicle) and downforce (increases tire grip)
- **Mass Properties Model**: Calculates normal forces on front and rear tires, accounts for load transfer during acceleration
- **Tire Model**: Calculates slip ratio and longitudinal force based on normal force and wheel speed
- **Powertrain Model**: Calculates motor torque, enforces 80kW power limit, converts to wheel torque
- **Net Force Calculation**: Sums all forces (drive force positive, drag and rolling resistance negative)
- **Acceleration**: Net force divided by vehicle mass (F = ma)

**Main Explanation:**
"Each timestep requires calculating forces from all vehicle subsystems. The models interact: aerodynamics creates downforce which affects normal forces on tires, which affects tire grip, which affects acceleration. The powertrain model enforces the 80kW power limit. The process is iterative - an initial acceleration guess is refined using the actual calculated acceleration."

---

## SLIDE 6: System Overview

### Architecture Benefits (optional bullet list):
- **Modularity**: Each model can be updated independently
- **Separation of Concerns**: Each layer has a clear purpose
- **Maintainability**: Easy to understand and modify
- **Extensibility**: New models can be added without changing existing code
- **Rule Compliance**: Rules are enforced automatically at the Rules Layer

**Main Explanation:**
"The system uses a modular, layered architecture. Each layer has specific responsibilities, enabling easy updates and maintenance. The Config Layer handles input, the Simulation Layer orchestrates the process, the Vehicle Models Layer contains all physics, the Dynamics Layer performs numerical integration, and the Rules Layer ensures Formula Student compliance."

---

## SLIDE 7: Summary & Applications

### SECTION 1: Key Achievements
**Subheading**: "What We Built"

- Physics-based simulation with realistic vehicle models
  - Includes tire dynamics, powertrain, aerodynamics, mass properties
- Full Formula Student rule compliance
  - Automatic 80kW power limit checking
  - 25-second time limit enforcement
  - Competition score calculation
- Parameterized design for rapid iteration
  - All parameters in configuration files
  - Easy to test different vehicle designs
- Automated scoring calculation
  - Uses official Formula Student scoring formula
  - Predicts competition performance

---

### SECTION 2: Applications
**Subheading**: "How It's Used"

- **Design Optimization**: Find optimal vehicle parameters for best acceleration
- **Parameter Sensitivity Analysis**: Understand which parameters most affect performance
- **Powertrain Sizing**: Determine required motor power and torque characteristics
- **Performance Prediction**: Estimate competition times before building the vehicle
- **Competition Strategy**: Evaluate trade-offs between different design choices
- **Educational Tool**: Learn vehicle dynamics and simulation techniques

---

### SECTION 3: Future Work (Optional)
**Subheading**: "Potential Enhancements"

- Additional vehicle models (suspension dynamics, thermal effects)
- Real-time optimization during simulation
- Integration with CAD tools for automatic parameter extraction
- Multi-objective optimization (balance acceleration vs. other events)
- Driver model for more realistic control strategies

---

## Notes

- All bullet points are ready to copy directly into your presentation
- Adjust formatting as needed for your presentation software
- Some sections have optional bullet lists - include them if space allows
- Make sure to include the scoring formula on Slide 2 with proper mathematical notation
- Highlight key numbers: 80 kW, 25 s, 75 m throughout the presentation


