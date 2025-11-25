# PowerPoint Presentation Generation Prompt

## Context
You are creating a technical presentation about a Formula Student vehicle acceleration simulation system developed as part of a 3rd Year Project (3YP). The system is a physics-based simulation tool for predicting Formula Student vehicle performance in the 0-75m acceleration event.

## Presentation Structure

### Slide 1: Title Slide
- **Title**: "Formula Student Acceleration Simulation System"
- **Subtitle**: "Physics-Based Performance Prediction for 0-75m Acceleration Event"
- **Author**: [Your Name]
- **Institution/Project**: 3rd Year Project
- **Date**: [Current Date]

### Slide 2: Problem Statement & Motivation
**Content to include:**
- Formula Student competition requires teams to optimize vehicle design for multiple events
- Acceleration event: 0-75m sprint, critical for overall score (75 points maximum)
- Need for predictive simulation tool to:
  - Evaluate design parameters before physical testing
  - Optimize powertrain, tire selection, and vehicle setup
  - Ensure compliance with Formula Student rules (80kW power limit, 25s time limit)
  - Predict competition scores
- Reduces costly physical testing iterations
- Enables rapid design space exploration

### Slide 3: System Overview
**Content to include:**
- **Purpose**: Physics-based simulation system for predicting Formula Student vehicle acceleration performance
- **Key Capabilities**:
  - Simulates 0-75m acceleration run
  - Models all major vehicle subsystems (tires, powertrain, aerodynamics, mass properties, suspension)
  - Enforces Formula Student rules compliance (EV 2.2: 80kW power limit, D 5.3: time limits and scoring)
  - Calculates competition scores
  - Parameterized design (all parameters in JSON/YAML configuration files)
- **Technology Stack**: Python, NumPy, SciPy, modular architecture

### Slide 4: Architecture Overview
**Visual**: Show layered architecture diagram
**Content to include:**
- **Modular Design Philosophy**: Each subsystem is a separate, interchangeable module
- **Architecture Layers**:
  1. **Configuration Layer**: JSON/YAML parameter files → VehicleConfig objects
  2. **Vehicle Model Layer**: Physics models for each subsystem
  3. **Dynamics Solver Layer**: RK4 numerical integration
  4. **Rules Compliance Layer**: Formula Student rules checking
  5. **Results Layer**: Simulation results and scoring
- **Key Design Principles**:
  - Modularity: Easy to swap models (e.g., simple tire model → Pacejka)
  - Parameterization: No hardcoded values, all in config files
  - Extensibility: Easy to add new subsystems or rules
  - Validation: Built-in configuration validation

### Slide 5: Vehicle Model Components
**Visual**: Diagram showing vehicle subsystems
**Content to include:**
- **Mass Properties Model**:
  - Total mass, CG location (x, z), inertia
  - Static load distribution
  - Longitudinal load transfer during acceleration
  - Normal force calculation (front/rear axles)
- **Tire Model**:
  - Simplified friction model (linear increase to optimal slip, then decrease)
  - Slip ratio calculation
  - Longitudinal force calculation: Fx = μ(λ) × Fz
  - Rolling resistance
  - Future: Pacejka model support (when tire data available)
- **Powertrain Model**:
  - Motor torque calculation (torque constant, current limits)
  - Battery voltage and current limits
  - Gear ratio and drivetrain efficiency
  - **Power limit enforcement (80kW at accumulator outlet - EV 2.2)**
  - Motor speed limits
- **Aerodynamics Model**:
  - Drag force: F_drag = -CdA × 0.5 × ρ × v²
  - Downforce (front/rear): F_downforce = -CL × 0.5 × ρ × v²
  - Air density effects
- **Suspension Model**:
  - Anti-squat effects
  - Load transfer geometry
  - Ride height parameters

### Slide 6: Dynamics Solver
**Visual**: Flowchart of integration loop
**Content to include:**
- **Integration Method**: 4th Order Runge-Kutta (RK4) for accuracy
- **State Vector**: 
  - Position, velocity, acceleration
  - Wheel angular velocities (front/rear)
  - Motor state (speed, current, torque)
  - Forces (drive, drag, rolling resistance, tire forces)
  - Normal forces, power consumption
- **Simulation Loop** (until 75m reached):
  1. Calculate aerodynamic forces (drag, downforce)
  2. Calculate normal forces (static + load transfer + downforce)
  3. Calculate slip ratios
  4. Calculate tire forces
  5. Calculate motor speed from wheel speed
  6. Calculate requested torque (control strategy)
  7. Calculate available torque (with power limit enforcement)
  8. Calculate net force and acceleration
  9. Integrate state using RK4
  10. Check termination (distance ≥ 75m or time ≥ max_time)
- **Time Step**: 0.001s (1ms) for accuracy

### Slide 7: Formula Student Rules Integration
**Content to include:**
- **EV 2.2 - Power Limit**:
  - Maximum power at accumulator outlet: 80 kW
  - Enforced during simulation by scaling torque when limit exceeded
  - Compliance checking: tracks maximum power used, violation time
  - Critical for competition legality
- **D 5.3.1 - Time Limit**:
  - Runs exceeding 25 seconds are disqualified
  - Simulation checks final time against limit
  - Non-compliant runs flagged in results
- **D 5.3.2 - Scoring Formula**:
  - Score = 0.95 × Pmax × ((Tmax / Tteam - 1) / 0.5) + 0.05 × Pmax
  - Where: Pmax = 75 points, Tmax = 1.5 × fastest_time, Tteam = team time
  - Automatically calculated if fastest time provided
  - Enables performance prediction and optimization

### Slide 8: Configuration System
**Visual**: Example JSON configuration snippet
**Content to include:**
- **Parameterization**: All vehicle parameters externalized in JSON/YAML files
- **Configuration Categories**:
  - Mass properties (mass, CG, wheelbase, track widths, inertia)
  - Tire properties (radius, friction coefficients, rolling resistance)
  - Powertrain (motor specs, battery, gear ratio, power limit)
  - Aerodynamics (CdA, downforce coefficients)
  - Suspension (anti-squat, ride height, wheel rates)
  - Control (launch torque limit, target slip, traction control)
  - Environment (air density, temperature, track grade)
  - Simulation parameters (time step, max time, target distance)
- **Benefits**:
  - Easy to test different vehicle configurations
  - No code changes needed for parameter sweeps
  - Human-readable format
  - Validation on load (checks power limits, physical constraints)

### Slide 9: Implementation Details
**Content to include:**
- **Language**: Python 3.x
- **Key Libraries**:
  - NumPy: Numerical computations, array operations
  - SciPy: Advanced numerical methods (if needed)
  - PyYAML: Configuration file parsing
  - JSON: Configuration file support
- **Code Structure**:
  - Modular package structure (config/, vehicle/, dynamics/, rules/, simulation/)
  - Object-oriented design with clear separation of concerns
  - Dataclasses for configuration and state management
  - Type hints for code clarity
- **State Management**:
  - `SimulationState` dataclass contains all state variables
  - State history tracked for analysis
  - Easy to log and visualize results
- **Error Handling**: Configuration validation, file loading error handling

### Slide 10: Example Usage & Results
**Visual**: Code snippet and output example
**Content to include:**
- **Simple Usage**:
  ```python
  from config.config_loader import load_config
  from simulation.acceleration_sim import AccelerationSimulation
  
  config = load_config("config/vehicle_configs/base_vehicle.json")
  sim = AccelerationSimulation(config)
  result = sim.run(fastest_time=4.5)
  
  print(f"Time: {result.final_time:.3f} s")
  print(f"Score: {result.score:.2f} points")
  print(f"Compliant: {result.compliant}")
  ```
- **Example Results**:
  - Final time: ~4.5-5.5 seconds (typical for Formula Student)
  - Power compliance: ✓ (max power ≤ 80kW)
  - Time compliance: ✓ (time ≤ 25s)
  - Score calculation based on fastest time
- **Output Information**:
  - Final time, distance, velocity
  - Maximum power used
  - Rules compliance status
  - Competition score (if fastest time provided)
  - State history available for detailed analysis

### Slide 11: Key Features & Capabilities
**Content to include:**
- **Physics-Based Modeling**:
  - Realistic tire force-slip relationship
  - Powertrain limitations (current, voltage, power)
  - Aerodynamic drag and downforce
  - Load transfer during acceleration
  - Rolling resistance
- **Rules Compliance**:
  - Automatic power limit enforcement
  - Time limit checking
  - Score calculation
- **Flexibility**:
  - Easy parameter modification via config files
  - Modular architecture allows model swapping
  - Extensible for new subsystems or rules
- **Validation**:
  - Configuration validation on load
  - Physical constraint checking
  - Rules compliance verification

### Slide 12: Technical Highlights
**Content to include:**
- **RK4 Integration**:
  - 4th order Runge-Kutta for high accuracy
  - Stable for stiff systems
  - Fixed time step (can be made adaptive)
- **Power Limit Enforcement**:
  - Real-time torque scaling when 80kW limit approached
  - Accounts for motor efficiency and drivetrain losses
  - Accurate representation of Formula Student constraints
- **Load Transfer Modeling**:
  - Longitudinal load transfer: ΔFz = (m × a × h_cg) / wheelbase
  - Accounts for CG height and position
  - Affects tire forces and acceleration
- **Slip Ratio Calculation**:
  - Accurate slip ratio: λ = (ω × r - v) / v
  - Handles near-zero velocity cases
  - Used for tire force calculation

### Slide 13: Current Limitations & Future Work
**Content to include:**
- **Current Limitations**:
  - Simplified tire model (linear friction, not Pacejka)
  - Constant motor efficiency (no efficiency maps)
  - No thermal effects (battery, motor, tires)
  - Fixed time step (not adaptive)
  - Simplified control strategy
  - No visualization tools yet
- **Planned Improvements**:
  - **Pacejka Tire Model**: When tire test data available
  - **Motor Efficiency Maps**: More accurate powertrain modeling
  - **Advanced Control**: Launch control, traction control algorithms
  - **Sensitivity Analysis**: Parameter sweep tools
  - **Visualization**: Velocity vs time, force plots, power curves
  - **Validation**: Compare with test data, calibrate models
  - **Optimization**: Design parameter optimization wrapper
  - **Batch Processing**: Run multiple simulations in parallel

### Slide 14: Validation & Testing Strategy
**Content to include:**
- **Unit Testing**:
  - Test each model independently
  - Known input/output validation
  - Edge case testing (zero velocity, max power, etc.)
- **Integration Testing**:
  - Full simulation with known configuration
  - Comparison with analytical solutions (where possible)
  - Rules compliance verification
- **Validation** (Future):
  - Compare simulation results with physical test data
  - Calibrate tire model with tire test data
  - Validate against previous season competition data
  - Sensitivity analysis to identify critical parameters

### Slide 15: Applications & Use Cases
**Content to include:**
- **Design Optimization**:
  - Evaluate different powertrain configurations
  - Test tire selection impact
  - Optimize gear ratios
  - Evaluate aerodynamic changes
- **Rules Compliance**:
  - Verify power limit compliance before testing
  - Predict time performance
  - Estimate competition scores
- **Parameter Studies**:
  - Sensitivity analysis (which parameters matter most?)
  - Design space exploration
  - Trade-off analysis (e.g., mass vs. power)
- **Educational Tool**:
  - Understand vehicle dynamics
  - Learn Formula Student rules
  - Physics-based learning

### Slide 16: Project Impact & Benefits
**Content to include:**
- **For Formula Student Team**:
  - Reduces physical testing iterations (cost and time savings)
  - Enables rapid design exploration
  - Predicts competition performance
  - Ensures rules compliance
- **Technical Skills Developed**:
  - Vehicle dynamics modeling
  - Numerical integration methods
  - Software architecture and design
  - Python programming
  - Formula Student rules knowledge
- **Extensibility**:
  - Foundation for future enhancements
  - Can be extended to other events (skidpad, autocross, endurance)
  - Modular design allows easy maintenance

### Slide 17: Code Quality & Architecture
**Content to include:**
- **Modular Design**:
  - Clear separation of concerns
  - Each subsystem is independent module
  - Easy to test and maintain
- **Configuration-Driven**:
  - No hardcoded values
  - Easy to modify without code changes
  - Human-readable parameter files
- **Type Safety**:
  - Type hints throughout codebase
  - Dataclasses for structured data
  - Clear interfaces between modules
- **Documentation**:
  - Comprehensive architecture documentation
  - Code comments and docstrings
  - Example usage files

### Slide 18: Conclusion
**Content to include:**
- **Summary**:
  - Successfully developed physics-based acceleration simulation
  - Modular, extensible architecture
  - Formula Student rules compliance built-in
  - Configuration-driven design
- **Key Achievements**:
  - Complete vehicle dynamics model
  - RK4 integration solver
  - Rules compliance checking
  - Scoring calculator
- **Future Directions**:
  - Model calibration with test data
  - Advanced tire and powertrain models
  - Visualization and analysis tools
  - Design optimization capabilities
- **Value**:
  - Practical tool for Formula Student team
  - Educational resource
  - Foundation for future development

### Slide 19: Questions & Discussion
- **Title**: "Questions & Discussion"
- **Content**: Thank you slide with contact information or Q&A prompt

## Visual Guidelines
- Use professional, clean design
- Include diagrams for architecture and data flow
- Use code snippets with syntax highlighting
- Include example outputs/results
- Use consistent color scheme
- Formula Student branding/colors if appropriate
- Technical diagrams should be clear and labeled

## Technical Depth
- Balance between high-level overview and technical details
- Include enough detail to show understanding of physics and implementation
- Use technical terminology appropriately
- Explain complex concepts clearly
- Show both "what" and "how"

## Presentation Style
- Professional academic/engineering presentation
- Clear, concise bullet points
- Visual aids where helpful
- Code examples to show implementation
- Results/output examples
- Future work to show forward thinking

## Additional Notes
- Emphasize the practical application to Formula Student competition
- Highlight the modular, extensible architecture as a key strength
- Show understanding of vehicle dynamics and numerical methods
- Demonstrate rules compliance integration
- Balance current capabilities with future potential

---

**Instructions for AI Presentation Generator:**
Use this detailed outline to create a professional PowerPoint presentation. Each slide should be well-designed with appropriate visuals, clear text, and professional formatting. Include diagrams where specified, code snippets with proper formatting, and ensure the presentation flows logically from problem statement through implementation to conclusions. The presentation should be suitable for an academic/engineering audience and demonstrate both technical competence and practical application.

