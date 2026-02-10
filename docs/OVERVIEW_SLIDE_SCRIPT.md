# Overview Slide Script

## Slide 2: Event Overview, Rules, and Objectives

### Opening Statement

"Good [morning/afternoon]. Today I'll be presenting our Formula Student Acceleration Simulation System—a physics-based computational tool we've developed to predict and optimize vehicle performance for the Formula Student Acceleration Event."

---

### Section 1: The Brief - What We're Building

"First, let me explain the brief. This project addresses a critical need in Formula Student racing: **how can we accurately predict a vehicle's acceleration performance before building it?**

Formula Student is an international engineering competition where university students design, build, and race formula-style race cars. In the Acceleration Event, teams must build a vehicle that can complete a 75-meter straight-line acceleration as quickly as possible—but under strict competition constraints.

The challenge is that building and testing multiple vehicle designs is expensive and time-consuming. Our solution is a **physics-based simulation system** that:

- Takes vehicle design parameters as input—things like mass, tire properties, motor specifications, and aerodynamic characteristics
- Simulates the complete physics of the vehicle accelerating from zero to 75 meters
- Validates that the design complies with Formula Student competition rules
- Calculates the predicted competition score based on performance

This enables engineers to rapidly iterate on designs, optimize parameters, and make informed decisions about powertrain sizing and vehicle configuration—all before committing to physical construction."

---

### Section 2: The Competition Context

"Now, let me set the context for what we're simulating. The **Formula Student Acceleration Event**, governed by Rule D 5, is a straight-line acceleration test over 75 meters.

Key event specifications:
- **Track length**: 75 meters from starting line to finish line
- **Track width**: Minimum 3 meters
- **Vehicle staging**: Positioned 0.30 meters behind the starting line
- **Run format**: Single run per attempt, with optional immediate second run in manual mode
- **Marking**: Cones placed at approximately 5-meter intervals along the track

But here's the critical constraint: vehicles must comply with strict competition rules that directly impact performance."

---

### Section 3: The Rules and Constraints

"The competition imposes two hard limits that our simulation must enforce:

**First, the Power Limit**—Rule EV 2.2 states that vehicles cannot exceed **80 kilowatts at the accumulator outlet**. This isn't just a design target; it's a hard technical limit that the simulation checks continuously throughout the entire run. If a vehicle exceeds this limit at any point, it's non-compliant.

**Second, the Time Limit**—Rule D 5.3.1 states that **runs exceeding 25 seconds are disqualified**. Our simulation stops immediately if this limit is reached.

**Third, the Scoring System**—Rule D 5.3.2 defines how teams are scored. The formula ensures that teams within 50% of the fastest time can still score points, with the fastest team receiving close to the maximum 75 points. The formula accounts for the fastest vehicle's time and calculates scores relative to that benchmark.

These rules aren't just constraints—they're integrated directly into our simulation logic, ensuring that every performance prediction is rule-compliant."

---

### Section 4: Simulation Objectives

"So what does our simulation actually do? It serves several critical engineering objectives:

**First, performance prediction**—we can predict how fast a vehicle will complete the 75-meter acceleration, given its design parameters.

**Second, design optimization**—we can find optimal vehicle parameters within the rule constraints, answering questions like: 'What's the best gear ratio?' or 'How much downforce should we target?'

**Third, rule validation**—we automatically check that powertrain power consumption never exceeds the 80-kilowatt limit throughout the entire run, and we verify that the predicted time is under the 25-second disqualification threshold.

**Fourth, score calculation**—if we know the fastest competitor's time, we can predict exactly how many competition points our design would score.

**Fifth, sensitivity analysis**—we can understand which vehicle parameters most affect acceleration performance. Is it mass, tire grip, or motor power? The simulation reveals these relationships.

**Finally, rapid iteration**—engineers can test hundreds of design variations in minutes, enabling data-driven decision-making during the design phase."

---

### Section 5: What We'll Cover Next

"In the following slides, I'll take you through how this system works technically.

**In Slide 3, we'll look at the Overall System Architecture**—this shows the high-level structure of our system, including the configuration layer, vehicle models layer, dynamics solver layer, and rules layer. You'll see how these components interact to create a modular, maintainable simulation framework.

**In Slide 4, we'll examine the Overall System Flow**—this is a detailed flowchart that walks you through the complete simulation process, from loading a configuration file to generating the final results. You'll see how validation, initialization, and simulation execution all come together.

**In Slide 5, we'll dive into the Dynamic Solver System and RK4**—this explains how we solve the physics equations. We use RK4, or Runge-Kutta 4th-order integration, which is a numerical method for solving differential equations. You'll see how the solver iteratively advances through time until the vehicle completes 75 meters.

**In Slide 6, we'll explore Calculate Derivatives and State Simulation**—this is the most detailed technical slide, showing all the physics calculations that happen in a single timestep. You'll see how aerodynamics, tire forces, powertrain torque, and net acceleration are all calculated and how these models interact with each other.

Finally, we'll conclude with a summary of what we've built and how it's applied in practice."

---

### Closing Transition

"So, to recap: we've built a physics-based simulation system that predicts Formula Student acceleration performance, enforces competition rules, and enables rapid design optimization. The rest of this presentation will show you exactly how it works under the hood.

Let's begin with the system architecture."

---

## Presentation Notes

### Timing Guide
- **Total slide time**: Approximately 3-4 minutes
- **Section 1 (Brief)**: 45-60 seconds
- **Section 2 (Competition Context)**: 30-40 seconds
- **Section 3 (Rules)**: 45-60 seconds
- **Section 4 (Objectives)**: 45-60 seconds
- **Section 5 (Preview)**: 30-40 seconds
- **Closing**: 15-20 seconds

### Key Points to Emphasize
1. **The problem**: Need to predict performance before building
2. **The solution**: Physics-based simulation
3. **The constraints**: 80kW power limit, 25s time limit
4. **The value**: Rapid iteration and optimization

### Visual Cues
- Point to the 75-meter track diagram when discussing event specifications
- Highlight the 80kW and 25s numbers when discussing constraints
- Reference the scoring formula box when explaining scoring
- Use hand gestures to indicate "flow" when previewing upcoming slides

### Audience Engagement
- Ask if anyone is familiar with Formula Student
- Pause after explaining the problem to let it sink in
- Make eye contact when explaining the value proposition

### Technical Depth
- Keep explanations accessible to both engineers and non-engineers
- Define acronyms when first used (RK4 will be explained in detail later)
- Use concrete examples (e.g., "testing hundreds of designs in minutes")


