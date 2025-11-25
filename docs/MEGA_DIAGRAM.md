# Mega Diagram: Complete System Data Flow

This diagram shows the complete data flow through the Formula Student Acceleration Simulation system, with all functions, inputs, outputs, and data connections.

## Visual Legend

- **Boxes**: Functions/Classes
- **Arrows**: Data flow (→) shows direction
- **Labels on arrows**: Data being passed
- **Dashed boxes**: Optional/conditional paths
- **Loops**: Marked with iteration conditions

---

## Main System Flow (High Level)

```mermaid
flowchart TD
    START([Start]) --> LOAD_CONFIG["load_config<br/>config_path: string or Path"]
    
    LOAD_CONFIG --> |"Reads file"| PARSE["Parse JSON/YAML<br/>Extract all properties"]
    PARSE --> CREATE_CONFIG["Create VehicleConfig<br/>mass, tires, powertrain, aero, suspension, control, environment"]
    CREATE_CONFIG --> VALIDATE["VehicleConfig.validate<br/>Check: power limit, mass greater than 0, CG position, tire radius, gear ratio"]
    
    VALIDATE --> |"errors List"| CHECK_ERRORS{"Errors found?"}
    CHECK_ERRORS --> |"Yes"| ERROR([Raise ValueError])
    CHECK_ERRORS --> |"No"| CONFIG_READY["VehicleConfig Object<br/>Validated"]
    
    CONFIG_READY --> INIT_SIM["AccelerationSimulation.__init__<br/>config: VehicleConfig"]
    
    INIT_SIM --> CREATE_SOLVER["Create DynamicsSolver<br/>config: VehicleConfig"]
    
    CREATE_SOLVER --> INIT_MODELS["Initialize Vehicle Models:<br/>MassPropertiesModel<br/>TireModel<br/>PowertrainModel<br/>AerodynamicsModel<br/>SuspensionModel<br/>ChassisGeometry<br/>ControlStrategy"]
    
    INIT_MODELS --> SOLVER_READY["DynamicsSolver Ready"]
    SOLVER_READY --> RUN_SIM["AccelerationSimulation.run<br/>fastest_time: Optional"]
    
    RUN_SIM --> SOLVE["DynamicsSolver.solve<br/>Loop until position greater than or equal to 75m"]
    
    SOLVE --> |"Returns final_state"| CHECK_POWER["check_power_limit<br/>state_history: List of SimulationState<br/>max_power: 80e3 W"]
    
    CHECK_POWER --> |"Returns: compliant, max_power, violation_time"| CHECK_TIME["check_time_limit<br/>final_state: SimulationState<br/>max_time: 25.0s"]
    
    CHECK_TIME --> |"Returns: compliant, final_time"| CALC_SCORE{"fastest_time provided?"}
    
    CALC_SCORE --> |"Yes"| SCORE["calculate_acceleration_score<br/>team_time: final_state.time<br/>fastest_time: float<br/>max_points: 75.0"]
    CALC_SCORE --> |"No"| NO_SCORE["score = None"]
    
    SCORE --> |"Returns: score"| CREATE_RESULT["Create SimulationResult<br/>final_state, compliant flags, max_power,<br/>final_time, final_distance, final_velocity, score"]
    NO_SCORE --> CREATE_RESULT
    
    CREATE_RESULT --> END([End: Return SimulationResult])

    style START fill:#90EE90
    style END fill:#90EE90
    style ERROR fill:#FFB6C6
    style SOLVE fill:#87CEEB
    style INIT_MODELS fill:#FFE4B5
```

---

## Detailed Solver Loop Expansion

This shows what happens inside `DynamicsSolver.solve()` - the main integration loop:

```mermaid
flowchart TD
    SOLVE_START([DynamicsSolver.solve<br/>Starts]) --> INIT_STATE[Initialize SimulationState<br/>position=0, velocity=0, all zeros<br/>time=0]
    
    INIT_STATE --> STORE_INITIAL[Store initial state<br/>in state_history]
    
    STORE_INITIAL --> LOOP_CHECK{"position less than 75m<br/>AND<br/>time less than max_time?"}
    
    LOOP_CHECK --> |"Yes - Continue"| CALC_DERIV["_calculate_derivatives<br/>state: SimulationState"]
    LOOP_CHECK --> |"No - Exit loop"| SOLVE_END([Return final_state])
    
    CALC_DERIV --> |"Returns: dstate_dt"| RK4_STEP["_rk4_step<br/>state: SimulationState<br/>dstate_dt: SimulationState<br/>dt: float"]
    
    RK4_STEP --> |"Returns: new_state"| UPDATE_STATE["Update state<br/>state = new_state"]
    
    UPDATE_STATE --> STORE_STATE["Store state<br/>in state_history"]
    
    STORE_STATE --> LOOP_CHECK
    
    style SOLVE_START fill:#90EE90
    style SOLVE_END fill:#90EE90
    style LOOP_CHECK fill:#FFE4B5
    style CALC_DERIV fill:#87CEEB
    style RK4_STEP fill:#87CEEB
```

---

## Complete Timestep Detail: _calculate_derivatives()

This shows EVERY function call that happens during one timestep inside `_calculate_derivatives()`:

```mermaid
flowchart TD
    DERIV_START(["_calculate_derivatives<br/>Input: state: SimulationState"]) --> AERO["AerodynamicsModel.calculate_forces<br/>velocity: state.velocity"]
    
    AERO --> |Returns: drag_force, downforce_front, downforce_rear| MASS_GUESS[MassPropertiesModel.calculate_normal_forces<br/>acceleration: state.acceleration<br/>front_downforce: downforce_front<br/>rear_downforce: downforce_rear]
    
    MASS_GUESS --> |Returns: normal_front, normal_rear<br/>First approximation| WHEEL_SPEED[Calculate wheel speeds<br/>front: velocity / tire_radius<br/>rear: state.wheel_angular_velocity_rear]
    
    WHEEL_SPEED --> SLIP_FRONT[TireModel.calculate_slip_ratio<br/>wheel_speed_front, vehicle_velocity]
    WHEEL_SPEED --> SLIP_REAR[TireModel.calculate_slip_ratio<br/>wheel_speed_rear, vehicle_velocity]
    
    SLIP_FRONT --> |Returns: slip_front| TIRE_FRONT[TireModel.calculate_longitudinal_force<br/>normal_front, slip_front, velocity]
    SLIP_REAR --> |Returns: slip_rear| TIRE_REAR[TireModel.calculate_longitudinal_force<br/>normal_rear, slip_rear, velocity]
    
    TIRE_FRONT --> |Returns: tire_force_front, rr_front| TIRE_FORCES[Collect Tire Forces]
    TIRE_REAR --> |Returns: tire_force_rear, rr_rear| TIRE_FORCES
    
    TIRE_FORCES --> MOTOR_SPEED[PowertrainModel.calculate_motor_speed<br/>wheel_speed_rear]
    
    MOTOR_SPEED --> |Returns: motor_speed| REQ_TORQUE[_calculate_requested_torque<br/>state, normal_rear]
    
    REQ_TORQUE --> |Returns: requested_torque| POWERTRAIN[PowertrainModel.calculate_torque<br/>requested_torque, motor_speed, vehicle_velocity]
    
    POWERTRAIN --> |Returns: wheel_torque, motor_current, power_consumed| TORQUE_TO_FORCE[Convert torque to force<br/>drive_force = wheel_torque / tire_radius]
    
    TORQUE_TO_FORCE --> |drive_force_rear| NET_FORCE[Calculate Net Force<br/>net_force = drive_force + drag_force + rolling_resistance<br/>Note: drag and rolling_resistance are negative]
    
    NET_FORCE --> |net_force| ACCELERATION[Calculate Acceleration<br/>acceleration = net_force / mass]
    
    ACCELERATION --> |acceleration: float| MASS_ACTUAL[MassPropertiesModel.calculate_normal_forces<br/>acceleration: actual_acceleration<br/>front_downforce: downforce_front<br/>rear_downforce: downforce_rear<br/>Recalculate with actual acceleration]
    
    MASS_ACTUAL --> |Returns: normal_front, normal_rear<br/>Final values| WHEEL_ALPHA[Calculate Wheel Angular Acceleration<br/>wheel_alpha_rear = torque - tire_force / inertia]
    
    WHEEL_ALPHA --> |wheel_alpha_rear| CREATE_DSTATE[Create Derivative State<br/>dstate.velocity = acceleration<br/>dstate.position = velocity<br/>dstate.wheel_angular_velocity_rear = wheel_alpha_rear<br/>dstate.acceleration = acceleration<br/>All forces, currents, powers stored]
    
    CREATE_DSTATE --> DERIV_END([Return: dstate_dt<br/>SimulationState with derivatives])
    
    style DERIV_START fill:#90EE90
    style DERIV_END fill:#90EE90
    style AERO fill:#FFE4B5
    style TIRE_FRONT fill:#FFE4B5
    style TIRE_REAR fill:#FFE4B5
    style POWERTRAIN fill:#FFE4B5
    style MASS_ACTUAL fill:#FFE4B5
    style ACCELERATION fill:#FF6B6B
```

---

## RK4 Integration Step Detail

This shows how RK4 integration works:

```mermaid
flowchart TD
    RK4_START(["_rk4_step<br/>state, dstate_dt, dt"]) --> K1["Calculate k1<br/>k1 = dstate_dt"]
    
    K1 --> K2_STATE[state_k2 = state + 0.5×dt×k1]
    K2_STATE --> K2_CALC[_calculate_derivatives<br/>state_k2]
    K2_CALC --> K2[Calculate k2<br/>k2 = derivatives at midpoint]
    
    K2 --> K3_STATE[state_k3 = state + 0.5×dt×k2]
    K3_STATE --> K3_CALC[_calculate_derivatives<br/>state_k3]
    K3_CALC --> K3[Calculate k3<br/>k3 = derivatives at midpoint]
    
    K3 --> K4_STATE[state_k4 = state + dt×k3]
    K4_STATE --> K4_CALC[_calculate_derivatives<br/>state_k4]
    K4_CALC --> K4[Calculate k4<br/>k4 = derivatives at endpoint]
    
    K4 --> COMBINE[Combine k1, k2, k3, k4<br/>weighted_avg = k1 + 2×k2 + 2×k3 + k4 / 6]
    
    COMBINE --> UPDATE[new_state = state + dt × weighted_avg<br/>new_state.time = state.time + dt]
    
    UPDATE --> RK4_END([Return: new_state])
    
    style RK4_START fill:#90EE90
    style RK4_END fill:#90EE90
    style K2_CALC fill:#87CEEB
    style K3_CALC fill:#87CEEB
    style K4_CALC fill:#87CEEB
```

---

## Vehicle Model Function Details

### MassPropertiesModel

```mermaid
flowchart LR
    MASS_MODEL[MassPropertiesModel] --> STATIC[calculate_static_load_distribution<br/>Input: None<br/>Output: front_load, rear_load]
    
    MASS_MODEL --> LOAD_XFER[calculate_load_transfer<br/>Input: longitudinal_acceleration<br/>Output: front_transfer, rear_transfer]
    
    MASS_MODEL --> NORMAL[calculate_normal_forces<br/>Input: acceleration, front_downforce, rear_downforce<br/>Output: normal_front, normal_rear]
    
    style MASS_MODEL fill:#FFE4B5
```

### TireModel

```mermaid
flowchart LR
    TIRE_MODEL[TireModel] --> SLIP[calculate_slip_ratio<br/>Input: wheel_angular_velocity, vehicle_velocity<br/>Output: slip_ratio]
    
    TIRE_MODEL --> FRICTION[_calculate_friction_coefficient<br/>Internal<br/>Input: slip_ratio<br/>Output: mu]
    
    TIRE_MODEL --> FORCE[calculate_longitudinal_force<br/>Input: normal_force, slip_ratio, velocity<br/>Output: fx, rolling_resistance]
    
    style TIRE_MODEL fill:#FFE4B5
```

### PowertrainModel

```mermaid
flowchart LR
    PT_MODEL[PowertrainModel] --> MOTOR_SPEED[calculate_motor_speed<br/>Input: wheel_angular_velocity<br/>Output: motor_speed]
    
    PT_MODEL --> WHEEL_SPEED[calculate_wheel_speed<br/>Input: motor_speed<br/>Output: wheel_angular_velocity]
    
    PT_MODEL --> TORQUE[calculate_torque<br/>Input: requested_torque, motor_speed, vehicle_velocity<br/>Applies: current limit, speed limit, 80kW power limit<br/>Output: wheel_torque, motor_current, power_consumed]
    
    style PT_MODEL fill:#FFE4B5
```

### AerodynamicsModel

```mermaid
flowchart LR
    AERO_MODEL[AerodynamicsModel] --> FORCES[calculate_forces<br/>Input: velocity<br/>Calculates: q = 0.5 × ρ × v²<br/>Output: drag_force, downforce_front, downforce_rear]
    
    style AERO_MODEL fill:#FFE4B5
```

### ControlStrategy

```mermaid
flowchart LR
    CTRL_MODEL[ControlStrategy] --> REQ[calculate_requested_torque<br/>Input: state, normal_force_rear, max_tire_force, tire_radius, dt<br/>Applies: launch control ramp, traction control<br/>Output: requested_torque]
    
    CTRL_MODEL --> OPTIMAL[calculate_optimal_launch_torque<br/>Input: normal_force_rear, mu_max, tire_radius<br/>Output: optimal_torque]
    
    CTRL_MODEL --> RESET[reset<br/>Resets internal state]
    
    style CTRL_MODEL fill:#FFE4B5
```

---

## Rules Checking Flow

```mermaid
flowchart TD
    RULES_START([Rules Checking<br/>After solver completes]) --> POWER_CHECK["check_power_limit<br/>Input:<br/>• state_history: List of SimulationState<br/>• max_power: 80e3 W"]
    
    POWER_CHECK --> |Scans all states| FIND_MAX[Find maximum power_consumed<br/>in state_history]
    
    FIND_MAX --> POWER_RESULT[(compliant: bool,<br/>max_power_used: float,<br/>time_of_violation: float)]
    
    POWER_RESULT --> TIME_CHECK["check_time_limit<br/>Input:<br/>final_state: SimulationState<br/>max_time: 25.0s"]
    
    TIME_CHECK --> TIME_RESULT[(compliant: bool,<br/>final_time: float)]
    
    TIME_RESULT --> SCORE_CHECK{fastest_time<br/>provided?}
    
    SCORE_CHECK --> |Yes| CALC_SCORE[calculate_acceleration_score<br/>Input:<br/>• team_time: final_state.time<br/>• fastest_time: float<br/>• max_points: 75.0]
    
    CALC_SCORE --> SCORE_RESULT[(score: float)]
    
    SCORE_CHECK --> |No| NO_SCORE_RESULT[(score: None)]
    
    SCORE_RESULT --> CREATE_RESULT
    NO_SCORE_RESULT --> CREATE_RESULT
    
    CREATE_RESULT[SimulationResult<br/>Contains:<br/>• final_state<br/>• power_compliant<br/>• time_compliant<br/>• compliant<br/>• max_power_used<br/>• final_time<br/>• final_distance<br/>• final_velocity<br/>• score]
    
    style RULES_START fill:#90EE90
    style CREATE_RESULT fill:#90EE90
    style POWER_CHECK fill:#FFE4B5
    style TIME_CHECK fill:#FFE4B5
    style CALC_SCORE fill:#FFE4B5
```

---

## Complete System Overview (Combined)

This combines everything into one comprehensive view:

```mermaid
flowchart TB
    subgraph CONFIG["🔧 CONFIG LAYER"]
        JSON[JSON/YAML File] --> LOAD[load_config<br/>Returns: VehicleConfig]
        LOAD --> VALID[VehicleConfig.validate<br/>Returns: errors List]
    end
    
    subgraph SIM["🎯 SIMULATION LAYER (Orchestrator)"]
        INIT[AccelerationSimulation.__init__<br/>Creates DynamicsSolver]
        RUN[AccelerationSimulation.run<br/>Orchestrates entire simulation]
    end
    
    subgraph MODELS["🚗 VEHICLE MODELS LAYER"]
        MASS[MassPropertiesModel]
        TIRE[TireModel]
        PT[PowertrainModel]
        AERO[AerodynamicsModel]
        SUSP[SuspensionModel]
        CHASSIS[ChassisGeometry]
        CTRL[ControlStrategy]
    end
    
    subgraph DYNAMICS["⚙️ DYNAMICS LAYER"]
        SOLVER[DynamicsSolver<br/>Main integration loop]
        DERIV[_calculate_derivatives<br/>Calls all vehicle models]
        RK4[_rk4_step<br/>RK4 integration]
        STATE[SimulationState<br/>Contains all variables]
    end
    
    subgraph RULES["📋 RULES LAYER"]
        POWER[check_power_limit]
        TIME[check_time_limit]
        SCORE[calculate_acceleration_score]
    end
    
    CONFIG --> SIM
    SIM --> DYNAMICS
    DYNAMICS --> MODELS
    MODELS --> DYNAMICS
    DYNAMICS --> SIM
    SIM --> RULES
    RULES --> RESULT([SimulationResult])
    
    style CONFIG fill:#E1F5FF
    style SIM fill:#FFF4E1
    style MODELS fill:#E8F5E9
    style DYNAMICS fill:#F3E5F5
    style RULES fill:#FFE1F5
    style RESULT fill:#90EE90
```

---

## Key Data Structures

### SimulationState (Main State Container)
```python
SimulationState:
  - position: float (m)
  - velocity: float (m/s)
  - acceleration: float (m/s²)
  - wheel_angular_velocity_front/rear: float (rad/s)
  - motor_speed/current/torque: float
  - drive_force: float (N)
  - drag_force: float (N)
  - rolling_resistance: float (N)
  - normal_force_front/rear: float (N)
  - tire_force_front/rear: float (N)
  - power_consumed: float (W)
  - time: float (s)
```

### SimulationResult (Final Output)
```python
SimulationResult:
  - final_state: SimulationState
  - compliant: bool
  - power_compliant: bool
  - time_compliant: bool
  - max_power_used: float (W)
  - final_time: float (s)
  - final_distance: float (m)
  - final_velocity: float (m/s)
  - score: Optional[float]
  - fastest_time: Optional[float]
```

---

## Notes

1. **Loop Iteration**: The solver loop runs approximately every 0.001s (dt) until 75m is reached
2. **RK4 Calls**: Each timestep requires 4 calls to `_calculate_derivatives()` (for k1, k2, k3, k4)
3. **Normal Force Iteration**: Normal forces are calculated twice per timestep (guess, then actual)
4. **Power Limit**: Applied inside `powertrain.calculate_torque()` - automatically scales torque back
5. **State History**: Every state is stored in `state_history` for analysis and visualization

