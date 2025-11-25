# Mega Diagram: Complete System Data Flow (Text Version)

This is a text-based visualization that will render in any markdown viewer, including Cursor's built-in preview.

---

## Complete System Flow (ASCII Diagram)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          START: JSON/YAML Config File                        │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  config_loader.load_config(config_path: str/Path)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Reads JSON/YAML file                                                │   │
│  │ Extracts: mass, tires, powertrain, aero, suspension, control, env   │   │
│  │ Creates: VehicleConfig object                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VehicleConfig.validate()                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Checks:                                                              │   │
│  │ • Power limit ≤ 80kW (EV 2.2)                                       │   │
│  │ • Mass > 0                                                           │   │
│  │ • CG position within wheelbase                                       │   │
│  │ • Tire radius > 0                                                    │   │
│  │ • Gear ratio > 0                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  Returns: errors: List[str] (empty if valid)                                │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────┴───────────┐
                    │   Errors found?       │
                    └───────────┬───────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
    ┌───────────────────────┐   ┌───────────────────────────────────────┐
    │ Raise ValueError      │   │ VehicleConfig Object                  │
    │ (Configuration Error) │   │ ✓ Validated                           │
    └───────────────────────┘   └───────────────┬───────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AccelerationSimulation.__init__(config: VehicleConfig)                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Creates: DynamicsSolver(config)                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DynamicsSolver.__init__(config: VehicleConfig)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Initializes Vehicle Models:                                         │   │
│  │ • MassPropertiesModel(config.mass)                                  │   │
│  │ • TireModel(config.tires)                                           │   │
│  │ • PowertrainModel(config.powertrain)                                │   │
│  │ • AerodynamicsModel(config.aerodynamics)                            │   │
│  │ • SuspensionModel(config.suspension)                                │   │
│  │ • ChassisGeometry(config.mass)                                      │   │
│  │ • ControlStrategy(config.control)                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AccelerationSimulation.run(fastest_time: Optional[float])                  │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DynamicsSolver.solve()  [MAIN INTEGRATION LOOP]                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Initialize SimulationState                                       │   │
│  │    position=0, velocity=0, time=0, all zeros                        │   │
│  │                                                                      │   │
│  │ 2. Store initial state in state_history                             │   │
│  │                                                                      │   │
│  │ 3. LOOP: while position < 75m AND time < max_time:                  │   │
│  │    ┌────────────────────────────────────────────────────────────┐  │   │
│  │    │ A. Call _calculate_derivatives(state)                      │  │   │
│  │    │    → Returns: dstate_dt (derivatives/rates of change)      │  │   │
│  │    │                                                             │  │   │
│  │    │ B. Call _rk4_step(state, dstate_dt, dt)                    │  │   │
│  │    │    → Returns: new_state (integrated forward in time)       │  │   │
│  │    │                                                             │  │   │
│  │    │ C. Update state = new_state                                │  │   │
│  │    │                                                             │  │   │
│  │    │ D. Store state in state_history                            │  │   │
│  │    └────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  │ 4. Return final_state                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ Returns: final_state
┌─────────────────────────────────────────────────────────────────────────────┐
│  RULES CHECKING                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. check_power_limit(state_history, max_power=80e3)                 │   │
│  │    → Scans all states, finds max power_consumed                     │   │
│  │    → Returns: (compliant: bool, max_power: float, violation_time)   │   │
│  │                                                                      │   │
│  │ 2. check_time_limit(final_state, max_time=25.0)                     │   │
│  │    → Compares final_state.time with 25.0s                           │   │
│  │    → Returns: (compliant: bool, final_time: float)                  │   │
│  │                                                                      │   │
│  │ 3. If fastest_time provided:                                        │   │
│  │    calculate_acceleration_score(team_time, fastest_time, max_points)│   │
│  │    → Calculates Formula Student score                               │   │
│  │    → Returns: score: float                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SimulationResult                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • final_state: SimulationState                                      │   │
│  │ • compliant: bool (power_compliant AND time_compliant)              │   │
│  │ • power_compliant: bool                                             │   │
│  │ • time_compliant: bool                                              │   │
│  │ • max_power_used: float (W)                                         │   │
│  │ • final_time: float (s)                                             │   │
│  │ • final_distance: float (m)                                         │   │
│  │ • final_velocity: float (m/s)                                       │   │
│  │ • score: Optional[float] (points)                                   │   │
│  │ • fastest_time: Optional[float] (s)                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## DETAILED TIMESTEP BREAKDOWN: _calculate_derivatives()

This shows EVERY function call that happens during ONE timestep inside the solver loop:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  _calculate_derivatives(state: SimulationState)                             │
│  Input: Current state with position, velocity, wheel speeds, etc.           │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Aerodynamic Forces                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ AerodynamicsModel.calculate_forces(velocity: state.velocity)        │   │
│  │   Input: velocity                                                   │   │
│  │   Process:                                                          │   │
│  │     • q = 0.5 × ρ × v² (dynamic pressure)                          │   │
│  │     • drag_force = -CdA × q                                         │   │
│  │     • downforce_front = -CL_front × q                               │   │
│  │     • downforce_rear = -CL_rear × q                                 │   │
│  │   Output: (drag_force, downforce_front, downforce_rear)             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ drag_force, downforce_front, downforce_rear
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Normal Forces (First Approximation)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ MassPropertiesModel.calculate_normal_forces(                        │   │
│  │     acceleration: state.acceleration (or guess),                    │   │
│  │     front_downforce,                                                │   │
│  │     rear_downforce                                                  │   │
│  │ )                                                                   │   │
│  │   Process:                                                          │   │
│  │     • Static load distribution (weight × distance ratios)           │   │
│  │     • Load transfer: (mass × accel × CG_height) / wheelbase        │   │
│  │     • Add downforce                                                 │   │
│  │   Output: (normal_front, normal_rear)                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ normal_front, normal_rear
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Calculate Wheel Speeds                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ wheel_speed_front = velocity / tire_radius (free-rolling)          │   │
│  │ wheel_speed_rear = state.wheel_angular_velocity_rear               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ wheel_speed_front, wheel_speed_rear
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Calculate Slip Ratios                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TireModel.calculate_slip_ratio(wheel_speed_front, velocity)        │   │
│  │   Output: slip_front                                               │   │
│  │                                                                     │   │
│  │ TireModel.calculate_slip_ratio(wheel_speed_rear, velocity)         │   │
│  │   Output: slip_rear                                                │   │
│  │                                                                     │   │
│  │ Formula: slip = (wheel_velocity - vehicle_velocity) / vehicle_vel  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ slip_front, slip_rear
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Calculate Tire Forces                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TireModel.calculate_longitudinal_force(                             │   │
│  │     normal_front, slip_front, velocity                              │   │
│  │ )                                                                   │   │
│  │   Process:                                                          │   │
│  │     • Calculate μ(λ) from slip ratio                                │   │
│  │     • Fx = μ × Fz                                                   │   │
│  │     • Rolling resistance = Crr × Fz                                 │   │
│  │   Output: (tire_force_front, rr_front)                              │   │
│  │                                                                     │   │
│  │ TireModel.calculate_longitudinal_force(                             │   │
│  │     normal_rear, slip_rear, velocity                                │   │
│  │ )                                                                   │   │
│  │   Output: (tire_force_rear, rr_rear)                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ tire_force_front, tire_force_rear, rr_front, rr_rear
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Calculate Motor Speed                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PowertrainModel.calculate_motor_speed(wheel_speed_rear)            │   │
│  │   Formula: motor_speed = wheel_speed × gear_ratio                  │   │
│  │   Output: motor_speed (rad/s)                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ motor_speed
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: Calculate Requested Torque (Control Strategy)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ DynamicsSolver._calculate_requested_torque(                         │   │
│  │     state, normal_force_rear                                        │   │
│  │ )                                                                   │   │
│  │   Process:                                                          │   │
│  │     • Simple control: min(launch_limit, grip_limit)                │   │
│  │     • Grip limit = μ_max × normal_force_rear × tire_radius         │   │
│  │   Output: requested_torque (N·m at wheels)                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ requested_torque
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: Calculate Actual Torque (with Limits)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PowertrainModel.calculate_torque(                                   │   │
│  │     requested_torque, motor_speed, vehicle_velocity                 │   │
│  │ )                                                                   │   │
│  │   Process:                                                          │   │
│  │     1. Convert wheel torque → motor torque                          │   │
│  │     2. Limit by motor current: max = kt × max_current               │   │
│  │     3. Limit by motor speed (cutoff at max_speed)                   │   │
│  │     4. Calculate electrical power = voltage × current / efficiency  │   │
│  │     5. Apply 80kW power limit (EV 2.2): scale torque if exceeded   │   │
│  │     6. Convert motor torque → wheel torque                          │   │
│  │   Output: (wheel_torque, motor_current, power_consumed)             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ wheel_torque, motor_current, power_consumed
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 9: Convert Torque to Force                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ drive_force_rear = wheel_torque / tire_radius                       │   │
│  │ total_drive_force = drive_force_rear                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ drive_force
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 10: Calculate Net Force and Acceleration                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ total_resistive = drag_force + rr_front + rr_rear                   │   │
│  │ net_force = total_drive_force + total_resistive                     │   │
│  │   (Note: drag and rolling_resistance are negative)                  │   │
│  │                                                                     │   │
│  │ acceleration = net_force / mass                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ acceleration
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 11: Recalculate Normal Forces (with Actual Acceleration)              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ MassPropertiesModel.calculate_normal_forces(                        │   │
│  │     acceleration: actual_acceleration,                              │   │
│  │     front_downforce,                                                │   │
│  │     rear_downforce                                                  │   │
│  │ )                                                                   │   │
│  │   Output: (normal_front, normal_rear) [Final values]                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼ normal_front, normal_rear (final)
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 12: Calculate Wheel Angular Acceleration                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ wheel_alpha_rear = (wheel_torque - tire_force_rear × radius) /      │   │
│  │                    (wheel_inertia + ...)                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 13: Create Derivative State                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Create new SimulationState with all rates of change:                │   │
│  │ • dstate.velocity = acceleration                                    │   │
│  │ • dstate.position = velocity                                        │   │
│  │ • dstate.wheel_angular_velocity_rear = wheel_alpha_rear             │   │
│  │ • dstate.acceleration = acceleration                                │   │
│  │ • Store all forces, currents, powers                                │   │
│  │ • dstate.time = 1.0 (dt applied later in integration)               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
                    Returns: dstate_dt (SimulationState with derivatives)
```

---

## RK4 Integration Step Detail

RK4 (Runge-Kutta 4th Order) requires 4 evaluations per timestep:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  _rk4_step(state, dstate_dt, dt)                                            │
│  Input:                                                                      │
│    • state: Current state                                                    │
│    • dstate_dt: Derivatives (from _calculate_derivatives)                    │
│    • dt: Time step (0.001s)                                                  │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  k1 = dstate_dt (derivatives at current point)                              │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  state_k2 = state + 0.5 × dt × k1                                           │
│  ↓                                                                           │
│  _calculate_derivatives(state_k2) → k2 (derivatives at midpoint)            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  state_k3 = state + 0.5 × dt × k2                                           │
│  ↓                                                                           │
│  _calculate_derivatives(state_k3) → k3 (derivatives at midpoint)            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  state_k4 = state + dt × k3                                                 │
│  ↓                                                                           │
│  _calculate_derivatives(state_k4) → k4 (derivatives at endpoint)            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  weighted_avg = (k1 + 2×k2 + 2×k3 + k4) / 6                                │
│  ↓                                                                           │
│  new_state = state + dt × weighted_avg                                      │
│  new_state.time = state.time + dt                                           │
│  ↓                                                                           │
│  Returns: new_state                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Note**: Each RK4 step calls `_calculate_derivatives()` 4 times!

---

## Vehicle Models Summary

All models are initialized once and used repeatedly in the loop:

### MassPropertiesModel
- `calculate_static_load_distribution()` → front/rear loads
- `calculate_load_transfer(acceleration)` → transfer forces
- `calculate_normal_forces(acceleration, downforce)` → normal forces

### TireModel
- `calculate_slip_ratio(wheel_speed, vehicle_velocity)` → slip ratio
- `calculate_longitudinal_force(normal, slip, velocity)` → tire force, rolling resistance

### PowertrainModel
- `calculate_motor_speed(wheel_speed)` → motor speed
- `calculate_torque(requested, motor_speed, velocity)` → actual torque, current, power (with 80kW limit)

### AerodynamicsModel
- `calculate_forces(velocity)` → drag, downforce_front, downforce_rear

### SuspensionModel
- `calculate_anti_squat_effect(acceleration, normal_force)` → anti-squat force

### ChassisGeometry
- Geometry helper functions (used for visualization/analysis)

### ControlStrategy
- `calculate_requested_torque(state, normal_force, ...)` → requested torque with launch/traction control

---

## Data Flow Summary

```
JSON Config → VehicleConfig → DynamicsSolver → Loop:
  ├─ Aerodynamics → drag, downforce
  ├─ Mass Properties → normal forces
  ├─ Tire Model → tire forces
  ├─ Powertrain → drive torque (limited to 80kW)
  └─ Calculate acceleration → update state

Loop continues until 75m reached → Check rules → Calculate score → Result
```

