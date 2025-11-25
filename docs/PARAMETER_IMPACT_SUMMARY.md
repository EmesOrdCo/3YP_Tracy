# Parameter Impact Level & Optimization Strategy - One-Line Justifications

## MASS PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `total_mass` | 🔴 Very High | ⬇️ MINIMIZE | Direct inverse relationship (a = F/m) means 10% lighter = 10% faster acceleration, affects all forces. |
| `cg_x` | 🔴 Very High | 🔄 OPTIMIZE | Controls load distribution; rearward = more rear grip for RWD, but too rearward loses front steering. |
| `cg_z` | 🔴 Very High | ⬇️ MINIMIZE | Directly in load transfer formula; lower = less pitch/lift, keeps front wheels planted during acceleration. |
| `wheelbase` | 🟡 Low | ⬇️ MINIMIZE | Longer wheelbase slightly reduces load transfer (small effect), primarily affects handling not acceleration. |
| `front_track` | 🟢 Zero | N/A | Only affects lateral dynamics (cornering), zero impact on straight-line acceleration. |
| `rear_track` | 🟢 Zero | N/A | Only affects lateral dynamics (cornering), zero impact on straight-line acceleration. |
| `i_yaw` | 🟢 Zero | N/A | Only affects rotation around vertical axis (cornering), zero impact on straight-line acceleration. |
| `i_pitch` | 🟡 Very Low | ⬇️ MINIMIZE | Secondary effect on pitch dynamics, but already captured by optimizing cg_z; computed parameter. |
| `unsprung_mass_front` | 🟡 Low | ⬇️ MINIMIZE | Affects wheel response dynamics, minimal impact (front wheels not driven), only 6% of total mass. |
| `unsprung_mass_rear` | 🟡 Low | ⬇️ MINIMIZE | Affects wheel response dynamics, minimal impact (slightly more important than front as driven wheels). |

## TIRE PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `radius_loaded` | 🔴 High | 🔄 OPTIMIZE | Force = torque/radius; smaller = more force but lower top speed, optimal balance needed. |
| `mass` | 🟡 Very Low | ⬇️ MINIMIZE | Part of unsprung mass (already covered), only 5% of total mass, fixed with tire choice. |
| `mu_max` | 🔴 Very High | ⬆️ MAXIMIZE | Direct multiplication (F = μ × Fz); 20% increase = 20% more grip = 15-20% faster. |
| `mu_slip_optimal` | 🟠 Medium | 🔄 OPTIMIZE | Shapes friction curve; must match target_slip_ratio for maximum grip during acceleration. |
| `rolling_resistance_coeff` | 🟡 Very Low | ⬇️ MINIMIZE | Small resistive force (~15N vs 3000-5000N drive force), only 0.3-0.5% impact, fixed with tire. |

## POWERTRAIN PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `motor_torque_constant` | 🔴 High | ⬆️ MAXIMIZE | Motor torque = kt × current; higher = more torque for same current, critical for motor selection. |
| `motor_max_current` | 🟠 Medium | ⬆️ MAXIMIZE | Limits max torque; with 200A @ 300V = 60kW, often not limiting due to 80kW power constraint. |
| `motor_max_speed` | 🟡 Very Low | ⬆️ MAXIMIZE | Not limiting for 75m acceleration (rarely reached), only matters for longer events. |
| `motor_efficiency` | 🟡 Low-Medium | ⬆️ MAXIMIZE | 5% efficiency loss = ~4kW more electrical power needed, but assumed constant in model. |
| `battery_voltage_nominal` | 🟠 Medium | ⬆️ MAXIMIZE | Higher voltage = lower current for same power = less voltage drop, but constrained by rules. |
| `battery_internal_resistance` | 🟡 Very Low | ⬇️ MINIMIZE | Very small voltage drop (~2.67V at 267A = 0.9% of 300V), negligible impact on performance. |
| `battery_max_current` | 🟠 Medium | ⬆️ MAXIMIZE | Usually not limiting (power limit more restrictive), but higher capability is better. |
| `gear_ratio` | 🔴 Very High | 🔄 OPTIMIZE | Direct torque multiplication; higher = more acceleration but lower top speed, optimal balance needed. |
| `drivetrain_efficiency` | 🟡 Low | ⬆️ MAXIMIZE | 5% loss = 5% less torque, but fixed by design (90-95% typical), minimal variation. |
| `differential_ratio` | 🟢 Zero | N/A | Only affects left/right wheel speed difference (cornering), zero impact on straight-line acceleration. |
| `max_power_accumulator_outlet` | 🔴 Very High | N/A (RULE) | Formula Student rule EV 2.2: fixed at 80kW maximum, not optimizable. |
| `wheel_inertia` | 🟠 Medium | ⬇️ MINIMIZE | Effective mass contribution (~3% of total mass), energy goes to spinning wheels, measurable impact. |

## AERODYNAMICS PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `cda` | 🟡 Low | ⬇️ MINIMIZE | Drag grows with v², but at low speeds (0-15 m/s) drag is only 1-5% of drive force. |
| `cl_front` | 🟡 Low | ⬆️ MAXIMIZE | Adds front normal force, but front wheels not driven (less critical), minimal at low speeds (v² relationship). |
| `cl_rear` | 🟠 Medium | ⬆️ MAXIMIZE | Adds rear normal force = more rear grip, more useful than front for RWD, but minimal at low speeds. |
| `air_density` | 🟠 Medium | N/A | Environmental variable (altitude/weather), cannot control, affects drag and downforce. |

## SUSPENSION PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `anti_squat_ratio` | 🟠 Medium | 🔄 OPTIMIZE | Affects load transfer during acceleration, can reduce rearward transfer, helps keep front planted. |
| `ride_height_front` | 🟡 Very Low | ⬇️ MINIMIZE | Only affects aero (if present), minimal direct impact, constrained by ground clearance rules. |
| `ride_height_rear` | 🟡 Very Low | ⬇️ MINIMIZE | Only affects aero (if present), minimal direct impact, constrained by ground clearance rules. |
| `wheel_rate_front` | 🟡 Very Low | 🔄 OPTIMIZE | Affects suspension compression, minimal effect on acceleration, secondary to other parameters. |
| `wheel_rate_rear` | 🟡 Very Low | 🔄 OPTIMIZE | Affects suspension compression, minimal effect on acceleration, secondary to other parameters. |

## CONTROL PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `launch_torque_limit` | 🔴 High | 🔄 OPTIMIZE | Critical for launch; too high = wheelspin, too low = slow start, must balance with tire grip. |
| `target_slip_ratio` | 🔴 High | 🔄 OPTIMIZE | Traction control target; maintains optimal slip for maximum grip, must match mu_slip_optimal. |
| `torque_ramp_rate` | 🟡 Low | 🔄 OPTIMIZE | Controls torque increase smoothness, secondary to slip control, minimal effect on final time. |
| `traction_control_enabled` | 🔴 High | ⬆️ MAXIMIZE | Always better than disabled; maintains optimal slip, prevents wheelspin (boolean, always true). |

## ENVIRONMENT PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `air_density` | 🟠 Medium | N/A | Environmental variable (altitude/weather), cannot control, affects drag and downforce. |
| `ambient_temperature` | 🟡 Low | N/A | Environmental variable, not modeled in current simulation (thermal effects not included). |
| `track_grade` | 🟠 Medium | N/A | Track property (slope), cannot control, uphill opposes motion, downhill helps. |
| `wind_speed` | 🟡 Very Low | N/A | Environmental variable, minimal impact at low speeds (0-15 m/s), cannot control. |
| `surface_mu_scaling` | 🔴 Very High | N/A | Track condition multiplier, cannot control (environmental), would scale all tire grip if variable. |

## SIMULATION PARAMETERS

| Parameter | Impact | Strategy | Justification |
|-----------|--------|----------|---------------|
| `dt` | N/A | ⬇️ MINIMIZE | Simulation accuracy parameter (not vehicle parameter), smaller = more accurate but slower computation. |
| `max_time` | N/A | N/A | Simulation safety limit (prevents infinite loops), Formula Student has 25s disqualification limit. |
| `target_distance` | N/A | N/A | Formula Student competition rule (exactly 75m), fixed requirement, not optimizable. |

---

## Summary Statistics

- **Very High Impact (Must Optimize)**: 6 parameters
- **High Impact (Should Optimize)**: 6 parameters  
- **Medium Impact (Consider Optimize)**: 8 parameters
- **Low Impact**: 13 parameters
- **Zero Impact**: 5 parameters
- **N/A (Rules/Environmental)**: 8 parameters

**Total Optimizable Parameters**: 20 (with 7 currently being optimized)

