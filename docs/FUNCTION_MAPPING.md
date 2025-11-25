# Complete Function Mapping for Mega Diagram

This document maps all functions, their inputs, outputs, and data flows for the mega diagram.

## 1. CONFIG LAYER

### `config_loader.load_config()`
- **Input**: `config_path: str | Path` (path to JSON/YAML file)
- **Output**: `VehicleConfig` object
- **Internal**: 
  - Reads JSON/YAML file
  - Creates all property objects (MassProperties, TireProperties, etc.)
  - Calls `VehicleConfig.validate()`
  - Returns validated config

### `VehicleConfig.validate()`
- **Input**: None (uses self properties)
- **Output**: `List[str]` (list of error messages, empty if valid)
- **Checks**: Power limit, mass > 0, CG position, tire radius, gear ratio

---

## 2. VEHICLE MODELS LAYER

### `MassPropertiesModel`

#### `calculate_static_load_distribution()`
- **Input**: None (uses self.config properties)
- **Output**: `Tuple[float, float]` = `(front_normal_force, rear_normal_force)` in N

#### `calculate_load_transfer(longitudinal_acceleration: float)`
- **Input**: `longitudinal_acceleration: float` (m/s²)
- **Output**: `Tuple[float, float]` = `(front_transfer, rear_transfer)` in N

#### `calculate_normal_forces(longitudinal_acceleration, front_downforce, rear_downforce)`
- **Input**: 
  - `longitudinal_acceleration: float` (m/s²)
  - `front_downforce: float = 0.0` (N)
  - `rear_downforce: float = 0.0` (N)
- **Output**: `Tuple[float, float]` = `(front_normal_force, rear_normal_force)` in N

---

### `TireModel`

#### `calculate_slip_ratio(wheel_angular_velocity, vehicle_velocity)`
- **Input**:
  - `wheel_angular_velocity: float` (rad/s)
  - `vehicle_velocity: float` (m/s)
- **Output**: `float` (slip ratio, 0-1)

#### `_calculate_friction_coefficient(slip_ratio)`
- **Input**: `slip_ratio: float`
- **Output**: `float` (friction coefficient μ)

#### `calculate_longitudinal_force(normal_force, slip_ratio, velocity)`
- **Input**:
  - `normal_force: float` (N)
  - `slip_ratio: float`
  - `velocity: float` (m/s)
- **Output**: `Tuple[float, float]` = `(longitudinal_force, rolling_resistance)` in N

---

### `PowertrainModel`

#### `calculate_motor_speed(wheel_angular_velocity)`
- **Input**: `wheel_angular_velocity: float` (rad/s)
- **Output**: `float` (motor angular velocity in rad/s)

#### `calculate_wheel_speed(motor_speed)`
- **Input**: `motor_speed: float` (rad/s)
- **Output**: `float` (wheel angular velocity in rad/s)

#### `calculate_torque(requested_torque, motor_speed, vehicle_velocity)`
- **Input**:
  - `requested_torque: float` (N·m at wheels)
  - `motor_speed: float` (rad/s)
  - `vehicle_velocity: float` (m/s)
- **Output**: `Tuple[float, float, float]` = `(wheel_torque, motor_current, power_consumed)`
  - `wheel_torque`: Actual torque at wheels (N·m)
  - `motor_current`: Motor current (A)
  - `power_consumed`: Power at accumulator outlet (W)

---

### `AerodynamicsModel`

#### `calculate_forces(velocity)`
- **Input**: `velocity: float` (m/s)
- **Output**: `Tuple[float, float, float]` = `(drag_force, downforce_front, downforce_rear)` in N

---

### `SuspensionModel`

#### `calculate_anti_squat_effect(longitudinal_acceleration, normal_force_rear)`
- **Input**:
  - `longitudinal_acceleration: float` (m/s²)
  - `normal_force_rear: float` (N)
- **Output**: `float` (additional normal force due to anti-squat in N)

---

### `ChassisGeometry`

#### `calculate_wheel_positions()`
- **Input**: None
- **Output**: `Tuple[Tuple, Tuple]` (wheel positions)

#### `calculate_cg_location()`
- **Input**: None
- **Output**: `Tuple[float, float, float]` = `(cg_x, cg_y, cg_z)`

#### `calculate_wheelbase_ratio()`
- **Input**: None
- **Output**: `float` (ratio 0-1)

#### `calculate_track_width_average()`
- **Input**: None
- **Output**: `float` (average track width)

#### `calculate_track_aspect_ratio()`
- **Input**: None
- **Output**: `float` (wheelbase / avg_track)

---

### `ControlStrategy`

#### `calculate_requested_torque(state, normal_force_rear, max_tire_force, tire_radius, dt)`
- **Input**:
  - `state: SimulationState`
  - `normal_force_rear: float` (N)
  - `max_tire_force: float` (N)
  - `tire_radius: float` (m)
  - `dt: float` (s)
- **Output**: `float` (requested torque at wheels in N·m)

#### `reset()`
- **Input**: None
- **Output**: None (resets internal state)

#### `calculate_optimal_launch_torque(normal_force_rear, mu_max, tire_radius)`
- **Input**:
  - `normal_force_rear: float` (N)
  - `mu_max: float`
  - `tire_radius: float` (m)
- **Output**: `float` (optimal torque at wheels in N·m)

---

### `LaunchControl` (separate class)

#### `get_launch_torque(time, dt)`
- **Input**:
  - `time: float` (s)
  - `dt: float` (s)
- **Output**: `float` (launch torque at wheels in N·m)

---

### `TractionControl` (separate class)

#### `calculate_torque_adjustment(current_slip_ratio, dt)`
- **Input**:
  - `current_slip_ratio: float`
  - `dt: float` (s)
- **Output**: `float` (adjustment factor 0.0-1.0)

---

## 3. DYNAMICS LAYER

### `SimulationState` (dataclass)
Contains all state variables:
- Position, velocity, acceleration
- Wheel speeds (front/rear)
- Motor state (speed, current, torque)
- Forces (drive, drag, rolling resistance)
- Normal forces (front/rear)
- Tire forces (front/rear)
- Power consumed
- Time

#### Methods:
- `to_dict() -> Dict`
- `copy() -> SimulationState`

---

### `DynamicsSolver`

#### `__init__(config: VehicleConfig)`
- **Input**: `config: VehicleConfig`
- **Output**: None
- **Creates**: All vehicle model instances

#### `solve() -> SimulationState`
- **Input**: None
- **Output**: `SimulationState` (final state)
- **Process**:
  1. Initialize state (all zeros)
  2. Loop until position >= 75m or time >= max_time:
     - Call `_calculate_derivatives(state)`
     - Call `_rk4_step(state, dstate_dt, dt)`
     - Store state in history
  3. Return final state

#### `_calculate_derivatives(state: SimulationState) -> SimulationState`
- **Input**: `state: SimulationState` (current state)
- **Output**: `SimulationState` (with derivatives/rates of change)
- **Process** (in order):
  1. Call `aero_model.calculate_forces(velocity)` → drag, downforce
  2. Call `mass_model.calculate_normal_forces(accel_guess, downforce)` → normal forces
  3. Calculate wheel speeds
  4. Call `tire_model.calculate_slip_ratio()` for front/rear
  5. Call `tire_model.calculate_longitudinal_force()` for front/rear
  6. Call `powertrain.calculate_motor_speed(wheel_speed_rear)`
  7. Call `_calculate_requested_torque()` → requested torque
  8. Call `powertrain.calculate_torque()` → actual torque, current, power
  9. Convert torque to force
  10. Calculate net force → acceleration
  11. Recalculate normal forces with actual acceleration
  12. Calculate wheel angular acceleration
  13. Create derivative state with all rates of change

#### `_calculate_requested_torque(state, normal_force_rear) -> float`
- **Input**:
  - `state: SimulationState`
  - `normal_force_rear: float` (N)
- **Output**: `float` (requested torque at wheels in N·m)

#### `_rk4_step(state, dstate_dt, dt) -> SimulationState`
- **Input**:
  - `state: SimulationState` (current state)
  - `dstate_dt: SimulationState` (derivatives)
  - `dt: float` (time step)
- **Output**: `SimulationState` (new state after integration)
- **Process**: Runge-Kutta 4th order integration (4 evaluations)

#### Helper methods:
- `_add_states(s1, s2) -> SimulationState`
- `_scale_state(state, scale) -> SimulationState`

---

## 4. RULES LAYER

### `check_power_limit(state_history, max_power)`
- **Input**:
  - `state_history: List[SimulationState]`
  - `max_power: float = 80e3` (W)
- **Output**: `Tuple[bool, float, float]` = `(compliant, max_power_used, time_of_violation)`

### `check_time_limit(final_state, max_time)`
- **Input**:
  - `final_state: SimulationState`
  - `max_time: float = 25.0` (s)
- **Output**: `Tuple[bool, float]` = `(compliant, final_time)`

### `calculate_acceleration_score(team_time, fastest_time, max_points)`
- **Input**:
  - `team_time: float` (s)
  - `fastest_time: float` (s)
  - `max_points: float = 75.0`
- **Output**: `float` (score in points)

### `calculate_tmax(fastest_time)`
- **Input**: `fastest_time: float` (s)
- **Output**: `float` (Tmax = 1.5 × fastest_time)

---

## 5. SIMULATION LAYER

### `AccelerationSimulation`

#### `__init__(config: VehicleConfig)`
- **Input**: `config: VehicleConfig`
- **Output**: None
- **Creates**: `DynamicsSolver(config)`

#### `run(fastest_time: Optional[float]) -> SimulationResult`
- **Input**: `fastest_time: Optional[float]` (s, for scoring)
- **Output**: `SimulationResult` object
- **Process**:
  1. Call `solver.solve()` → final_state
  2. Call `check_power_limit(state_history, max_power)` → power_compliant, max_power
  3. Call `check_time_limit(final_state, 25.0)` → time_compliant, final_time
  4. Calculate overall compliance
  5. If fastest_time provided: call `calculate_acceleration_score()` → score
  6. Create and return `SimulationResult`

#### `get_state_history() -> List[SimulationState]`
- **Input**: None
- **Output**: `List[SimulationState]` (full state history)

---

## DATA FLOW SUMMARY

### Main Flow:
```
JSON/YAML File
  ↓
load_config() → VehicleConfig
  ↓
AccelerationSimulation.__init__(config)
  ↓ Creates DynamicsSolver(config)
    ↓ Creates all VehicleModel instances
  ↓
AccelerationSimulation.run()
  ↓
DynamicsSolver.solve()
  ↓ Loop: until 75m reached
    ↓
    _calculate_derivatives(state)
      ↓ Calls all vehicle models
      ↓ Returns derivative state
    ↓
    _rk4_step(state, dstate_dt, dt)
      ↓ Integrates state forward
      ↓ Returns new state
    ↓
    Store state in history
  ↓ Returns final_state
  ↓
Check rules (power_limit, time_limit)
  ↓
Calculate score (if fastest_time provided)
  ↓
Return SimulationResult
```

### One Timestep Detail (inside _calculate_derivatives):
```
Current State
  ↓
aero_model.calculate_forces(velocity)
  → drag_force, downforce_front, downforce_rear
  ↓
mass_model.calculate_normal_forces(accel_guess, downforce)
  → normal_front, normal_rear
  ↓
tire_model.calculate_slip_ratio(wheel_speed, velocity) [front & rear]
  → slip_front, slip_rear
  ↓
tire_model.calculate_longitudinal_force(normal, slip, velocity) [front & rear]
  → tire_force_front, tire_force_rear, rolling_resistance
  ↓
powertrain.calculate_motor_speed(wheel_speed_rear)
  → motor_speed
  ↓
_calculate_requested_torque(state, normal_rear)
  → requested_torque
  ↓
powertrain.calculate_torque(requested, motor_speed, velocity)
  → wheel_torque, motor_current, power
  ↓
Calculate net force = drive_force + drag + rolling_resistance
  ↓
acceleration = net_force / mass
  ↓
Re-calculate normal forces with actual acceleration
  ↓
Calculate wheel angular acceleration
  ↓
Create derivative state (all rates of change)
```

