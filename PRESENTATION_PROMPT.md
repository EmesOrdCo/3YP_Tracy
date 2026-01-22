# Presentation Creation Prompt for AI

## Context: What This Project Is

This is a **Formula Student Acceleration Simulation System**. Formula Student is an international engineering competition where university students design, build, and race formula-style race cars. This specific project is a computer simulation that predicts how fast a Formula Student vehicle will accelerate over a 75-meter straight track.

The simulation is a physics-based computer program written in Python that:
- Takes vehicle design parameters as input (mass, tire properties, motor specs, aerodynamics, etc.)
- Simulates the physics of the vehicle accelerating from 0 to 75 meters
- Checks if the vehicle complies with Formula Student competition rules
- Calculates the competition score based on performance

The user will provide 4 diagram images that show how the simulation system works internally. Your job is to create a professional presentation explaining this system.

## Task

Create a professional 7-slide presentation about this Formula Student Acceleration Simulation system. The user will provide 4 diagram images that you should include on slides 3, 4, 5, and 6. Make the presentation visually appealing, technically accurate, and suitable for an engineering audience.

## Slide-by-Slide Instructions

### SLIDE 1: Title/Introduction Slide

**Layout**: Center-aligned title slide

**Exact Content to Include:**

**Main Title (large, bold, centered):**
"Formula Student Acceleration Simulation System"

**Subtitle (medium size, centered, below title):**
"Physics-Based Performance Prediction and Optimization"

**Optional elements (smaller, bottom of slide):**
- Date (current date or "2025")
- Author/Team name (if provided by user)

**Design Requirements:**
- Clean, professional design
- Use colors that suggest racing/engineering: consider dark backgrounds with bright accents, or light backgrounds with bold colors
- Formula Student colors are often red, white, and black, but you can use blues, grays, or other professional color schemes
- Ensure high contrast for readability
- Use a modern, sans-serif font for the title (e.g., Arial, Helvetica, Calibri, or similar)
- Make the title prominent (at least 44pt font)
- Leave adequate white space

---

### SLIDE 2: Event Overview, Rules, and Objectives

**Title (top of slide, large and bold):**
"Formula Student Acceleration Event: Rules & Objectives"

**Layout**: Divide the slide into clear sections. Use a 2-column or 3-section layout.

**SECTION 1: Event Description**
**Subheading**: "The Competition Event"

**Bullet points (include exactly these):**
- Formula Student Acceleration Event (Rule D 5)
- 75-meter straight-line acceleration track
- Single run format per attempt
- Vehicle staged 0.30 meters behind starting line
- Track width: minimum 3 meters
- Cones placed along track at ~5 meter intervals

**SECTION 2: Key Rules & Constraints**
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

Display this formula clearly (use proper mathematical notation):

```
M_ACCELERATION_SCORE = 0.95 × Pmax × ((Tmax/Tteam - 1) / 0.5) + 0.05 × Pmax
```

**Where:**
- Pmax = 75 points (maximum points for manual mode acceleration event)
- Tmax = 1.5 × fastest time (1.5 times the fastest vehicle's time in competition)
- Tteam = team's best time including penalties (capped at Tmax, cannot exceed Tmax)

**Explanation**: Teams get more points for faster times. The formula ensures that teams within 50% of the fastest time can still score points, with the fastest team getting close to the maximum 75 points.

**SECTION 3: Simulation Objectives**
**Subheading**: "What This Simulation Does"

**Bullet points (include exactly these):**
- Predict vehicle acceleration performance from 0 to 75 meters
- Optimize design parameters within rule constraints (80kW power limit, 25s time limit)
- Validate powertrain power consumption against 80kW limit throughout the run
- Calculate competition scores based on predicted performance time
- Enable rapid design iteration and parameter sensitivity analysis
- Help engineers understand which vehicle parameters most affect acceleration performance

**Visual Elements (if space allows):**
- Simple diagram showing a 75m straight line with start and finish
- Text boxes highlighting key numbers: "80 kW", "25 s", "75 m"
- Consider a small flowchart showing: Design Parameters → Simulation → Performance Prediction → Score Calculation

**Design Notes:**
- Use clear section dividers
- Make the formula stand out (larger font, different color, or boxed)
- Use consistent bullet point styling
- Ensure all text is readable (minimum 18pt font for body text)

---

### SLIDE 3: Main System Flow (High Level)

**Title (top of slide, large and bold):**
"System Architecture: High-Level Flow"

**Layout**: 
- Title at top
- Large diagram image in center (user will provide this)
- Optional: Brief explanatory text below or beside the diagram

**Diagram Image:**
The user will provide an image showing a flowchart. This diagram shows the complete flow from configuration file to simulation result. The diagram includes these key stages (you don't need to list these, but understand what the diagram shows):
1. Start: JSON/YAML configuration file input
2. Load and parse configuration
3. Create VehicleConfig object
4. Validate configuration (check for errors)
5. Initialize simulation
6. Create dynamics solver
7. Initialize vehicle models (tires, powertrain, aerodynamics, etc.)
8. Run simulation loop
9. Solve dynamics (integrate until vehicle reaches 75m)
10. Check power limit compliance
11. Check time limit compliance
12. Calculate score (if fastest time provided)
13. Create and return simulation result

**Text to Include (below or beside diagram, if space allows):**

**Brief Description:**
"The simulation starts with a configuration file containing all vehicle parameters. The system validates these parameters, initializes physics models, solves the vehicle dynamics until the vehicle completes 75 meters, checks Formula Student rule compliance, and calculates the competition score."

**Key Points (optional bullet list):**
- Configuration-driven: All parameters in JSON/YAML files
- Validated: System checks parameters before simulation
- Physics-based: Uses realistic vehicle models
- Rule-compliant: Automatically checks competition rules
- Score-ready: Calculates Formula Student scores

**Design Notes:**
- Make the diagram image large and clear (should take up most of the slide)
- If the diagram is complex, ensure it's readable
- Add a brief caption or explanation
- Use consistent colors with the rest of the presentation

---

### SLIDE 4: Solver Loop Detail

**Title (top of slide, large and bold):**
"Dynamics Solver: Integration Loop"

**Layout**: 
- Title at top
- Large diagram image in center (user will provide this)
- Brief explanatory text

**Diagram Image:**
The user will provide an image showing a flowchart. This diagram shows the detailed solver loop that runs during simulation. The diagram shows:
1. Solver starts
2. Initialize state (position=0, velocity=0, time=0, all zeros)
3. Store initial state in history
4. Loop condition check: Is position < 75m AND time < max_time?
5. If yes: Calculate derivatives
6. Perform RK4 integration step
7. Update state with new values
8. Store state in history
9. Loop back to condition check
10. If no: Return final state

**Text to Include:**

**Main Explanation:**
"This diagram shows how the simulation advances through time. The solver uses RK4 (Runge-Kutta 4th order) numerical integration to solve the differential equations of motion. Each iteration calculates how the vehicle's state changes over a small time step, then updates the position, velocity, and other state variables. The loop continues until the vehicle completes 75 meters or exceeds the 25-second time limit."

**Key Technical Points (optional bullet list):**
- **RK4 Integration**: 4th-order Runge-Kutta method for accurate numerical integration
- **State History**: Complete state stored at each timestep for analysis
- **Iterative Process**: Small timesteps (typically 0.001-0.01 seconds) for accuracy
- **Termination Conditions**: Stops when position ≥ 75m OR time ≥ 25s

**Design Notes:**
- Diagram should be prominent
- Explain what RK4 is briefly (it's a numerical method for solving differential equations)
- Highlight the iterative/loop nature
- Use technical but accessible language

---

### SLIDE 5: Timestep Calculation Detail

**Title (top of slide, large and bold):**
"Physics Calculation: Complete Timestep"

**Layout**: 
- Title at top
- Large diagram image (user will provide this - this is the most complex diagram)
- Brief explanatory text

**Diagram Image:**
The user will provide an image showing a detailed flowchart. This is the most complex diagram showing all physics calculations performed in a single timestep. The diagram shows the sequence of calculations:
1. Start with current vehicle state
2. Calculate aerodynamics (drag force, downforce front, downforce rear)
3. Calculate normal forces (using mass properties model)
4. Calculate wheel speeds
5. Calculate tire slip ratios (front and rear)
6. Calculate tire longitudinal forces (front and rear)
7. Calculate motor speed from wheel speed
8. Calculate requested torque
9. Calculate actual torque from powertrain (applies 80kW power limit)
10. Convert torque to drive force
11. Calculate net force (drive force - drag - rolling resistance)
12. Calculate acceleration (net force / mass)
13. Recalculate normal forces with actual acceleration
14. Calculate wheel angular acceleration
15. Create derivative state (rate of change of all variables)
16. Return derivatives for integration

**Text to Include:**

**Main Explanation:**
"Each timestep requires calculating forces from all vehicle subsystems. The models interact: aerodynamics creates downforce which affects normal forces on tires, which affects tire grip, which affects acceleration. The powertrain model enforces the 80kW power limit. The process is iterative - an initial acceleration guess is refined using the actual calculated acceleration."

**Key Model Interactions (optional bullet list):**
- **Aerodynamics Model**: Calculates drag (slows vehicle) and downforce (increases tire grip)
- **Mass Properties Model**: Calculates normal forces on front and rear tires, accounts for load transfer during acceleration
- **Tire Model**: Calculates slip ratio and longitudinal force based on normal force and wheel speed
- **Powertrain Model**: Calculates motor torque, enforces 80kW power limit, converts to wheel torque
- **Net Force Calculation**: Sums all forces (drive force positive, drag and rolling resistance negative)
- **Acceleration**: Net force divided by vehicle mass (F = ma)

**Design Notes:**
- This is the most complex diagram - ensure it's readable
- Consider adding callouts or annotations if the diagram is too dense
- Explain the interconnected nature of the models
- Emphasize that this happens thousands of times per simulation (once per timestep)

---

### SLIDE 6: System Overview

**Title (top of slide, large and bold):**
"Complete System Architecture"

**Layout**: 
- Title at top
- Large diagram image (user will provide this)
- Brief explanatory text

**Diagram Image:**
The user will provide an image showing a system architecture diagram with colored boxes/layers. This diagram shows the layered architecture:
- **Config Layer** (typically blue/light blue): Configuration loading and validation
- **Simulation Layer** (typically yellow/beige): Main simulation orchestration
- **Vehicle Models Layer** (typically green): All physics models (MassPropertiesModel, TireModel, PowertrainModel, AerodynamicsModel, SuspensionModel, ChassisGeometry, ControlStrategy)
- **Dynamics Layer** (typically purple): Solver, derivative calculation, RK4 integration, state management
- **Rules Layer** (typically pink/red): Power limit checking, time limit checking, scoring

**Text to Include:**

**Main Explanation:**
"The system uses a modular, layered architecture. Each layer has specific responsibilities, enabling easy updates and maintenance. The Config Layer handles input, the Simulation Layer orchestrates the process, the Vehicle Models Layer contains all physics, the Dynamics Layer performs numerical integration, and the Rules Layer ensures Formula Student compliance."

**Architecture Benefits (optional bullet list):**
- **Modularity**: Each model can be updated independently
- **Separation of Concerns**: Each layer has a clear purpose
- **Maintainability**: Easy to understand and modify
- **Extensibility**: New models can be added without changing existing code
- **Rule Compliance**: Rules are enforced automatically at the Rules Layer

**Design Notes:**
- The diagram should show the layered structure clearly
- Explain how data flows between layers
- Emphasize the modularity and clean architecture
- Use consistent terminology

---

### SLIDE 7: Conclusion/Outro Slide

**Title (top of slide, large and bold):**
"Summary & Applications"

**Layout**: 
- Title at top
- Two or three columns/sections
- Clean, professional closing

**SECTION 1: Key Achievements**
**Subheading**: "What We Built"

**Bullet points (include exactly these):**
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

**SECTION 2: Applications**
**Subheading**: "How It's Used"

**Bullet points (include exactly these):**
- **Design Optimization**: Find optimal vehicle parameters for best acceleration
- **Parameter Sensitivity Analysis**: Understand which parameters most affect performance
- **Powertrain Sizing**: Determine required motor power and torque characteristics
- **Performance Prediction**: Estimate competition times before building the vehicle
- **Competition Strategy**: Evaluate trade-offs between different design choices
- **Educational Tool**: Learn vehicle dynamics and simulation techniques

**SECTION 3: Future Work (Optional)**
**Subheading**: "Potential Enhancements"

**Bullet points (suggestions - can be modified):**
- Additional vehicle models (suspension dynamics, thermal effects)
- Real-time optimization during simulation
- Integration with CAD tools for automatic parameter extraction
- Multi-objective optimization (balance acceleration vs. other events)
- Driver model for more realistic control strategies

**Closing (bottom of slide, optional):**
- "Thank you" or "Questions?"
- Contact information (if applicable)
- Project repository or website (if applicable)

**Design Notes:**
- Professional closing slide
- Summarize key points clearly
- Show the value and applications
- Leave room for questions/discussion
- Use consistent styling with rest of presentation

---

## General Design Guidelines

### Color Scheme
- **Primary Colors**: Professional colors (blues, grays, whites) for backgrounds and main content
- **Accent Colors**: Formula Student theme colors (red, white, black) or other bold colors for highlights
- **Consistency**: Use the same color scheme throughout all slides
- **Contrast**: Ensure high contrast between text and background for readability
- **Accessibility**: Avoid color combinations that are difficult for colorblind viewers

### Typography
- **Headings**: Large, bold, sans-serif font (e.g., Arial, Helvetica, Calibri)
  - Title slides: 44-60pt
  - Section headings: 32-40pt
- **Body Text**: Clear, readable sans-serif or serif font
  - Minimum 18pt for body text
  - 24pt or larger preferred for readability
- **Formulas**: Use proper mathematical notation
  - Consider using equation editor or LaTeX-style formatting
  - Ensure subscripts, superscripts, and symbols are clear
- **Consistency**: Use the same font family throughout (can vary size and weight)

### Layout Principles
- **White Space**: Don't overcrowd slides - leave adequate margins and spacing
- **Alignment**: Align elements consistently (left, center, or right, but be consistent)
- **Balance**: Balance text and images - don't let one dominate
- **Hierarchy**: Use size, color, and position to show importance
- **Grid**: Use an invisible grid to align elements consistently

### Technical Accuracy Requirements
- **Formulas**: All formulas must be exactly correct
  - M_ACCELERATION_SCORE = 0.95 × Pmax × ((Tmax/Tteam - 1) / 0.5) + 0.05 × Pmax
  - Pmax = 75 points
  - Tmax = 1.5 × fastest time
- **Rules**: All rule references must be accurate
  - EV 2.2: 80 kW power limit
  - D 5.3.1: 25 second time limit
  - D 5.3.2: Scoring formula
- **Terminology**: Use correct technical terms
  - "RK4" or "Runge-Kutta 4th order" (not "RK4 method" as redundant)
  - "Normal forces" (not "normal force" when referring to front and rear)
  - "Accumulator outlet" (not "battery" - Formula Student uses "accumulator")
- **Units**: Include units where appropriate
  - 80 kW (not just "80")
  - 75 m (not just "75")
  - 25 s (not just "25")

### Image Handling
- **User-Provided Images**: The user will provide 4 diagram images
  - Slide 3: Main System Flow diagram
  - Slide 4: Solver Loop Detail diagram
  - Slide 5: Timestep Calculation diagram
  - Slide 6: System Overview diagram
- **Image Quality**: Ensure images are high-resolution and readable
- **Image Placement**: Center images or align consistently
- **Image Sizing**: Make images large enough to be readable, but leave room for text
- **Captions**: Consider adding brief captions below images if helpful

### Slide Transitions and Animation (Optional)
- Keep transitions simple and professional
- Avoid distracting animations
- If using animations, use them to reveal content progressively (e.g., bullet points appear one at a time)
- Ensure animations don't slow down the presentation

## What the User Will Provide

The user will provide 4 diagram images:
1. **Main System Flow** - A flowchart showing the complete simulation process from config to result
2. **Solver Loop Detail** - A flowchart showing the RK4 integration loop
3. **Timestep Calculation** - A detailed flowchart showing all physics calculations in one timestep
4. **System Overview** - A layered architecture diagram showing the system structure

You should incorporate these images into slides 3, 4, 5, and 6 respectively.

## Deliverable

Create a professional presentation with:
- **7 slides total**: 1 intro, 5 content slides, 1 outro
- **4 user-provided diagram images** incorporated into slides 3-6
- **Professional design**: Clean, modern, engineering-appropriate
- **Accurate technical content**: All formulas, rules, and technical details correct
- **Clear narrative flow**: Each slide builds on the previous
- **Readable**: All text and diagrams clearly visible
- **Consistent styling**: Same fonts, colors, and layout principles throughout

## Final Notes

- Assume the audience has engineering background but may not know Formula Student rules
- Explain technical terms when first introduced
- Make the presentation suitable for both technical and non-technical audiences
- Focus on clarity and readability over complexity
- The goal is to explain what the simulation does and how it works, not to show off complexity
