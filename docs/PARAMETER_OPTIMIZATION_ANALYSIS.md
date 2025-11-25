# Complete Parameter Optimization Analysis

**Context: Building Formula Student Car from Scratch**  
This document analyzes every parameter for optimization when designing a Formula Student acceleration car from the ground up. All parameters are considered tunable design choices.

## Analysis Format

For each parameter:
- **Ideal Value:** Minimize / Maximize / Optimize (run script)
- **Currently Optimizing?** Yes/No
- **Should Optimize?** Yes/No/Maybe
- **Impact Level:** Low/Medium/High/Very High
- **Why Excluding?** (if not optimizing)
- **Physics Impact:** How it affects acceleration
- **Typical Range:** Expected values for Formula Student
- **Recommendation:** Specific guidance

---

## MASS PARAMETERS

### `total_mass`: 250.0 kg
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ✅ **YES**
- **Impact Level:** 🔴 **VERY HIGH**
- **Why Excluding?** Currently not in quick optimization - should be added
- **Physics Impact:**
  - **Direct inverse relationship**: `a = F/m`
  - **10% lighter = ~10% faster acceleration** (if force constant)
  - Affects everything: load transfer, inertia, rolling resistance, tire wear
  - Lightest possible while meeting structural/safety requirements
- **Typical Range:** 200-300 kg for Formula Student (rule-dependent minimums)
- **Constraints:**
  - Formula Student rules: Minimum weight requirements
  - Structural integrity: Must support loads safely
  - Safety: Must protect driver, battery enclosure
- **Recommendation:** ✅ **OPTIMIZE** - Minimize to absolute minimum allowed by rules/safety

---

### `cg_x`: 1.2 m (from front axle)
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ✅ **YES** - Range: (0.8, 1.4)
- **Should Optimize?** ✅ **YES**
- **Impact Level:** 🔴 **VERY HIGH**
- **Why Excluding?** N/A - Already optimizing
- **Physics Impact:**
  - **Controls static load distribution**: `rear_load = (cg_x / wheelbase) × total_weight`
  - **More rearward CG = more rear grip at launch** (critical for RWD)
  - **Trade-off**: Too rearward = front lift = loss of steering control
  - **Optimal balance**: Enough rear weight for traction, enough front for control
- **Typical Range:** 0.8-1.4 m (60-87% weight on rear)
- **Tunability:** Battery location, motor position, driver position, component layout
- **Recommendation:** ✅ **CONTINUE OPTIMIZING** - Critical parameter

---

### `cg_z`: 0.3 m (height from ground)
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ✅ **YES** - Range: (0.2, 0.4)
- **Should Optimize?** ✅ **YES**
- **Impact Level:** 🔴 **VERY HIGH**
- **Why Excluding?** N/A - Already optimizing
- **Physics Impact:**
  - **Directly in load transfer**: `ΔFz = (mass × acceleration × cg_z) / wheelbase`
  - **Lower CG = less load transfer** = more stable = front wheels stay planted
  - **Lower CG = better acceleration** (less pitch, better weight distribution)
  - Affects pitch stability during hard acceleration
- **Typical Range:** 0.2-0.4 m (constrained by ground clearance, tire radius)
- **Tunability:** Mount components lower, reduce ride height, optimize packaging
- **Recommendation:** ✅ **CONTINUE OPTIMIZING** - Minimize as much as possible

---

### `wheelbase`: 1.6 m
- **Ideal Value:** ⬇️ **MINIMIZE** (but with constraints)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE**
- **Impact Level:** 🟡 **LOW-MEDIUM**
- **Why Excluding?** 
  - **Small impact** compared to other parameters
  - **Formula Student rules**: Minimum wheelbase requirements (T 2.9.1: ≥1525mm)
  - **Packaging constraints**: Need space for driver, battery, powertrain
- **Physics Impact:**
  - In denominator of load transfer: **longer = slightly less load transfer** (small effect)
  - **Shorter = more load transfer** but potentially better weight distribution
  - Affects pitch moment of inertia (very minor)
  - Primarily affects handling (lateral dynamics), not acceleration
- **Typical Range:** 1.5-1.8 m (minimum rule compliance to packaging limits)
- **Constraints:** Driver accommodation, component packaging, minimum rule requirements
- **Recommendation:** ⚠️ **OPTIONAL** - Minimize within constraints, but low priority vs other parameters

---

### `front_track`: 1.2 m
- **Ideal Value:** N/A (no acceleration impact)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟢 **ZERO** (for acceleration)
- **Why Excluding?** Zero impact on straight-line acceleration
- **Physics Impact:**
  - **Only affects lateral dynamics** (cornering)
  - Zero effect on longitudinal acceleration
  - Affects roll moment of inertia (irrelevant for acceleration)
- **Typical Range:** 1.0-1.3 m (packaging and stability)
- **Recommendation:** ❌ **SKIP** - No impact on acceleration event

---

### `rear_track`: 1.2 m
- **Ideal Value:** N/A (no acceleration impact)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟢 **ZERO** (for acceleration)
- **Why Excluding?** Same as front_track - zero impact on acceleration
- **Recommendation:** ❌ **SKIP** - No impact on acceleration event

---

### `i_yaw`: 100.0 kg·m² (yaw moment of inertia)
- **Ideal Value:** N/A (no acceleration impact)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟢 **ZERO**
- **Why Excluding?** Only affects rotation around vertical axis (cornering)
- **Physics Impact:** None for straight-line acceleration
- **Recommendation:** ❌ **SKIP** - Irrelevant for acceleration event

---

### `i_pitch`: 200.0 kg·m² (pitch moment of inertia)
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** 
  - **Computed parameter**: Calculated from mass distribution (not independent)
  - **Secondary effect**: Already captured by CG position (cg_z) optimization
  - **Minimal direct impact**
- **Physics Impact:**
  - Affects how quickly vehicle pitches during acceleration
  - Lower pitch inertia = faster pitch response (usually better)
  - **Secondary to CG position effects**
- **Typical Range:** 150-300 kg·m² (depends on mass distribution)
- **Tunability:** Not directly tunable - optimized by optimizing CG position and mass distribution
- **Recommendation:** ❌ **SKIP** - Effect already captured by cg_z optimization

---

### `unsprung_mass_front`: 15.0 kg
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE**
- **Impact Level:** 🟡 **LOW**
- **Why Excluding?** 
  - **Small magnitude**: 15 kg front = 6% of 250 kg total
  - **Minimal impact**: Affects wheel acceleration dynamics (very minor)
  - **Lower priority** than other parameters
- **Physics Impact:**
  - Lower unsprung mass = slightly faster wheel response
  - Effect on acceleration is minimal (front wheels not driven)
  - More important for handling/comfort than acceleration
- **Typical Range:** 10-20 kg per axle (wheel + tire + brake + hub assembly)
- **Tunability:** Lighter wheels, tires, brake rotors, hubs
- **Recommendation:** ⚠️ **OPTIONAL** - Minimize if easy/cost-effective, but low priority

---

### `unsprung_mass_rear`: 15.0 kg
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE**
- **Impact Level:** 🟡 **LOW**
- **Why Excluding?** Same as front - minimal impact
- **Note:** Slightly more important than front (driven wheels) but still minimal
- **Physics Impact:**
  - Lower unsprung mass = slightly faster wheel response
  - Driven wheels slightly more critical than non-driven
- **Recommendation:** ⚠️ **OPTIONAL** - Minimize if easy/cost-effective, but low priority

---

## TIRE PARAMETERS

### `radius_loaded`: 0.2286 m (9 inches)
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ✅ **YES**
- **Impact Level:** 🔴 **HIGH**
- **Why Excluding?** Not currently in optimization - should be added
- **Physics Impact:**
  - **Force conversion**: `drive_force = wheel_torque / radius` (line 135)
  - **Smaller radius = more force** for same torque = better acceleration
  - **Effective gearing**: Smaller radius acts like higher gear ratio
  - **Trade-off**: Smaller = lower top speed, higher wheel speeds (motor limits)
  - **Optimal balance**: Enough torque multiplication without hitting motor speed limits
- **Typical Range:** 0.20-0.25 m (8-10 inches)
- **Tunability:** Choose tire size (within available options)
- **Constraints:** Tire availability, motor speed limits, ground clearance
- **Recommendation:** ✅✅ **ADD TO OPTIMIZATION** - High impact, tunable design choice

---

### `mass`: 3.0 kg (per tire)
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE** (low priority)
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** 
  - **Part of unsprung mass**: Already accounted for in unsprung_mass parameters
  - **Small magnitude**: 4 tires × 3 kg = 12 kg (5% of total mass)
  - **Fixed with tire choice**: Tire weight comes with tire selection
- **Physics Impact:**
  - Adds to unsprung mass (already covered)
  - Contributes to total mass (minimal)
  - Minimal direct impact on acceleration
- **Typical Range:** 2.5-4.0 kg per tire (tire size and compound dependent)
- **Tunability:** Fixed when tire is chosen (part of tire selection)
- **Recommendation:** ⚠️ **OPTIONAL** - Consider when selecting tires, but low priority standalone optimization

---

### `mu_max`: 1.5 (maximum friction coefficient)
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ✅✅ **YES** - **CRITICAL MISSING!**
- **Impact Level:** 🔴 **VERY HIGH**
- **Why Excluding?** Not currently in optimization - **MUST ADD**
- **Physics Impact:**
  - **Direct multiplication**: `tire_force = mu_max × normal_force` (line 57)
  - **20% increase in mu_max = 20% more grip = potentially 15-20% faster**
  - **Highest impact tire parameter**
  - More grip = more acceleration capability
- **Typical Range:** 1.2-1.8 (soft slicks to hard compounds)
- **Tunability:** Teams select tire compound (major design choice)
- **Constraints:** Tire availability, cost, durability, regulations
- **Recommendation:** ✅✅ **MUST ADD** - Highest impact tire parameter, critical for performance

---

### `mu_slip_optimal`: 0.15 (optimal slip ratio)
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ✅ **YES**
- **Impact Level:** 🟠 **MEDIUM**
- **Why Excluding?** Not currently in optimization - should be added
- **Physics Impact:**
  - **Shapes friction curve**: Determines optimal slip for maximum grip
  - **Works with `target_slip_ratio`**: If mu_slip_optimal ≠ target_slip_ratio, losing grip
  - Different compounds have different optimal slip values
  - **Must match target_slip_ratio** for best performance
- **Typical Range:** 0.10-0.20
- **Tunability:** Varies with tire compound selection
- **Recommendation:** ✅ **ADD** - Works together with target_slip_ratio optimization

---

### `rolling_resistance_coeff`: 0.015
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** 
  - **Minimal impact**: Rolling resistance = coeff × normal_force
  - At 1000N normal force: ~15N resistance
  - Drive force ~3000-5000N → 0.3-0.5% impact
  - **Fixed property**: Determined by tire construction
- **Physics Impact:**
  - Small resistive force (opposes motion)
  - Negligible compared to acceleration forces
- **Typical Range:** 0.010-0.020
- **Tunability:** Fixed with tire selection (tire construction property)
- **Recommendation:** ❌ **SKIP** - Negligible impact, fixed with tire choice

---

## POWERTRAIN PARAMETERS

### `motor_torque_constant`: 0.5 N·m/A
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ✅ **YES** (if comparing motors)
- **Impact Level:** 🔴 **HIGH**
- **Why Excluding?** Currently not optimizing - should add if comparing motors
- **Physics Impact:**
  - **Motor torque = kt × current** (line 73)
  - **Higher kt = more torque** for same current = more acceleration
  - **With power limit**: Higher kt = can use more of available power as torque
  - **Critical for motor selection**
- **Typical Range:** 0.3-0.7 N·m/A (motor dependent)
- **Tunability:** Motor selection (design choice)
- **Trade-offs:** Higher kt motors may be larger/heavier/more expensive
- **Recommendation:** ✅ **OPTIMIZE** - Critical for motor selection, maximize within constraints

---

### `motor_max_current`: 200.0 A
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE** (if comparing motors)
- **Impact Level:** 🟠 **MEDIUM** (but usually not limiting)
- **Why Excluding?** 
  - **Often not limiting**: With 80kW power limit, current often not the constraint
  - **Power limit constraint**: P = V × I, so at 300V: max I = 80kW/300V = 267A
  - Current limit (200A) IS limiting at low speeds (60kW max)
- **Physics Impact:**
  - Limits maximum motor torque: max torque = kt × max_current
  - With 200A limit: max torque = 0.5 × 200 = 100 N·m
  - Could be a constraint if motor can't deliver full power
- **Typical Range:** 150-400 A (motor dependent)
- **Tunability:** Motor selection (motor specification)
- **Recommendation:** ⚠️ **OPTIONAL** - Maximize if comparing motors, but power limit often more restrictive

---

### `motor_max_speed`: 1000.0 rad/s
- **Ideal Value:** ⬆️ **MAXIMIZE** (but not critical)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW** (for 75m acceleration)
- **Why Excluding?** 
  - **Not limiting for 75m**: Rarely reached in short acceleration event
  - **Top speed parameter**: Only matters for longer events
- **Physics Impact:**
  - Limits maximum vehicle speed
  - For 75m acceleration: vehicle unlikely to reach limiting speed
- **Typical Range:** 500-1500 rad/s (motor dependent)
- **Recommendation:** ❌ **SKIP** - Not limiting for acceleration event

---

### `motor_efficiency`: 0.95 (95%)
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE** (if comparing motors)
- **Impact Level:** 🟡 **LOW-MEDIUM**
- **Why Excluding?** 
  - **Assumed constant**: Current simulation uses constant efficiency
  - **Motor characteristic**: Efficiency varies with speed/torque (not fully modeled)
- **Physics Impact:**
  - **Power conversion**: P_electrical = P_mechanical / efficiency (line 80)
  - Lower efficiency = more electrical power needed = hits 80kW limit sooner
  - **5% efficiency loss = ~4kW more electrical power needed**
- **Typical Range:** 0.90-0.97 (90-97%)
- **Tunability:** Motor selection (motor characteristic)
- **Current Model:** Constant efficiency (simplified)
- **Recommendation:** ⚠️ **OPTIONAL** - Maximize if comparing motors, but simplified model limits impact

---

### `battery_voltage_nominal`: 300.0 V
- **Ideal Value:** ⬆️ **MAXIMIZE** (with constraints)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE**
- **Impact Level:** 🟠 **MEDIUM**
- **Why Excluding?** Currently not optimizing - could add for battery design
- **Physics Impact:**
  - **Higher voltage = lower current** for same power = less voltage drop
  - **Power limit**: V × I = 80kW, so voltage determines max current
  - Higher voltage = more efficient power delivery
- **Typical Range:** 200-400 V (Formula Student rules dependent)
- **Tunability:** Battery pack configuration (series cells)
- **Constraints:** Formula Student rules, cell availability, safety systems
- **Recommendation:** ⚠️ **OPTIONAL** - Maximize within rules, but often constrained by regulations

---

### `battery_internal_resistance`: 0.01 Ω
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** 
  - **Very small impact**: Voltage drop = I × R
  - At 267A: ~2.67V drop (0.9% of 300V)
  - **Battery characteristic**: Fixed by cell type and configuration
- **Physics Impact:**
  - Causes voltage sag under load
  - Minimal effect on performance
- **Typical Range:** 0.005-0.02 Ω (cell dependent)
- **Tunability:** Battery cell selection and configuration
- **Recommendation:** ❌ **SKIP** - Negligible impact, fixed by cell choice

---

### `battery_max_current`: 300.0 A
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟠 **MEDIUM** (but usually not limiting)
- **Why Excluding?** 
  - **Often not limiting**: With 80kW @ 300V = 267A max, so battery can handle it
  - **Power limit constraint**: Usually power limit hits before battery current limit
- **Physics Impact:**
  - Limits maximum power draw from battery
  - Could be limiting if battery current limit < power limit allows
- **Typical Range:** 250-400 A (battery dependent)
- **Tunability:** Battery pack design (cell selection, parallel configuration)
- **Recommendation:** ❌ **SKIP** - Usually not limiting, power limit more restrictive

---

### `gear_ratio`: 10.0
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ✅ **YES** - Range: (8.0, 12.0)
- **Should Optimize?** ✅ **YES**
- **Impact Level:** 🔴 **VERY HIGH**
- **Why Excluding?** N/A - Already optimizing
- **Physics Impact:**
  - **Direct torque multiplication**: `wheel_torque = motor_torque × gear_ratio` (line 99)
  - **Highest impact powertrain parameter**
  - **Trade-off**: Higher ratio = more torque/acceleration, lower top speed
  - **Optimal balance**: Enough torque for acceleration without hitting motor speed limits too early
- **Typical Range:** 6.0-15.0 (motor and wheel speed dependent)
- **Tunability:** Easy to change (sprockets/gears)
- **Recommendation:** ✅ **CONTINUE OPTIMIZING** - Critical parameter

---

### `drivetrain_efficiency`: 0.95 (95%)
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **LOW**
- **Why Excluding?** 
  - **Fixed by design**: Gear/chain/belt efficiency (90-95% typical)
  - **Minimal variation**: Efficiency doesn't vary much with design
  - **5% loss = 5% less torque** - but this is inherent, not easily optimizable
- **Physics Impact:**
  - Reduces torque: `wheel_torque = ... × efficiency` (line 99)
  - Small constant loss
- **Typical Range:** 0.90-0.97 (90-97%)
- **Tunability:** Drivetrain type selection (chain vs belt vs direct), quality of components
- **Recommendation:** ⚠️ **OPTIONAL** - Maximize by choosing good drivetrain, but low priority optimization

---

### `differential_ratio`: 1.0
- **Ideal Value:** N/A (no acceleration impact)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟢 **ZERO** (straight-line)
- **Why Excluding?** 
  - **Only for cornering**: Affects left/right wheel speed difference
  - **Straight-line**: Both wheels same speed, ratio irrelevant
- **Physics Impact:** None for acceleration event
- **Recommendation:** ❌ **SKIP** - Irrelevant for acceleration

---

### `max_power_accumulator_outlet`: 80000.0 W (80 kW)
- **Ideal Value:** N/A (FORMULA STUDENT RULE)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO** (RULE!)
- **Impact Level:** 🔴 **VERY HIGH** (constraining)
- **Why Excluding?** 
  - **FORMULA STUDENT RULE EV 2.2**: Fixed at 80kW maximum
  - **Not optimizable**: This IS the rule, not a parameter to optimize
  - **Enforced**: Optimizer automatically penalizes violations
- **Physics Impact:**
  - **Limiting constraint**: Everything must stay under this
  - Enforced in powertrain model
- **Recommendation:** N/A - Rule constraint, cannot optimize

---

### `wheel_inertia`: 0.1 kg·m²
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE** (if comparing wheel designs)
- **Impact Level:** 🟠 **MEDIUM** (corrected - now properly modeled)
- **Why Excluding?** 
  - **Smaller impact than other parameters**: ~3% effective mass increase
  - **Design choice**: Usually optimized at wheel selection, not setup tuning
- **Physics Impact:**
  - **Effective mass contribution**: `m_effective = m_vehicle + (4 × I_wheel) / r²`
  - For current config: 0.1 kg·m² / (0.2286 m)² = 1.91 kg per wheel
  - All 4 wheels: +7.64 kg effective mass (3% of 250 kg total)
  - **Direct impact**: Higher inertia = slower acceleration (energy goes to spinning wheels)
  - **Formula**: `acceleration = net_force / (total_mass + rotational_inertia_contribution)`
  - **Now properly modeled!**
- **Typical Range:** 0.05-0.15 kg·m² (lighter wheels = lower inertia)
- **Tunability:** 
  - **Wheel/tire design**: Choose lighter wheels/tires to reduce inertia
  - **Design variable**: If comparing different wheel packages
- **Trade-offs:**
  - **Lighter wheels**: Lower inertia = faster acceleration, but usually weaker/more expensive
  - **Heavier wheels**: Higher inertia = slower acceleration, but stronger/cheaper
- **When to Optimize:**
  - ✅ **YES** if comparing different wheel/tire designs (wheel selection phase)
  - ❌ **NO** if wheel already chosen (setup optimization phase)
- **Recommendation:** ⚠️ **OPTIONAL** - Minimize when selecting wheels, impact is measurable (~3%) but smaller than other parameters

---

## AERODYNAMICS PARAMETERS

### `cda`: 0.8 (drag coefficient × area)
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE** (if have aero options)
- **Impact Level:** 🟡 **LOW** (for 75m acceleration)
- **Why Excluding?** 
  - **Low speeds**: Drag = 0.5 × ρ × CdA × v²
  - **At low speeds (0-15 m/s)**: Drag is small (~50-150N)
  - **Drive force ~3000-5000N**: Drag = 1-5% impact
- **Physics Impact:**
  - Opposing force (reduces acceleration)
  - Grows with velocity squared
  - Minimal for short acceleration event
- **Typical Range:** 0.6-1.2 (depends on bodywork)
- **Tunability:** Can adjust with bodywork/aero design
- **Recommendation:** ⚠️ **OPTIONAL** - Minimize if easy, but low priority for acceleration event

---

### `cl_front`: 0.0 (front downforce coefficient)
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE** (if have front aero)
- **Impact Level:** 🟡 **LOW** (at low speeds, for RWD)
- **Why Excluding?** 
  - **Zero in config**: No front aero currently
  - **RWD**: Front downforce less critical than rear
  - **Low speeds**: Downforce = 0.5 × ρ × CL × v² (minimal at low speeds)
- **Physics Impact:**
  - Adds normal force → more front grip
  - But front wheels not driven (less critical)
  - Helps keep front wheels planted
- **Typical Range:** 0.0-2.0
- **Tunability:** Add front wing/aero package
- **Recommendation:** ⚠️ **OPTIONAL** - Maximize if adding aero, but low priority for RWD acceleration

---

### `cl_rear`: 0.0 (rear downforce coefficient)
- **Ideal Value:** ⬆️ **MAXIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ⚠️ **MAYBE** (if have aero - in comprehensive version)
- **Impact Level:** 🟠 **MEDIUM** (at higher speeds, for RWD)
- **Why Excluding?** 
  - **Zero in config**: No rear aero currently
  - **Low speeds**: Downforce minimal (v² relationship)
  - **More useful than front**: Rear aero helps driven wheels
- **Physics Impact:**
  - Adds rear normal force → more rear grip
  - More useful for RWD than front aero
  - Helps maintain traction at speed
- **Typical Range:** 0.0-2.0
- **Tunability:** Add rear wing/aero package
- **Recommendation:** ⚠️ **OPTIONAL** - Maximize if adding aero, more useful than front for RWD

---

### `air_density`: 1.225 kg/m³
- **Ideal Value:** N/A (environmental)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟠 **MEDIUM** (if variable, but it's environmental)
- **Why Excluding?** 
  - **Environmental parameter**: Cannot control (altitude/weather)
  - **Fixed assumption**: Standard sea-level conditions
- **Physics Impact:**
  - Affects drag and downforce
  - Lower density (high altitude) = less drag, less downforce
- **Tunability:** Cannot control
- **Recommendation:** ❌ **SKIP** - Environmental variable, cannot optimize

---

## SUSPENSION PARAMETERS

### `anti_squat_ratio`: 0.0
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ✅ **YES** (in comprehensive version)
- **Impact Level:** 🟠 **MEDIUM**
- **Why Excluding?** Included in comprehensive_optimization.py but not quick version
- **Physics Impact:**
  - **Affects load transfer**: Can reduce or increase rear load transfer during acceleration
  - **Suspension geometry effect**: Higher anti-squat = less rearward load transfer
  - Can help keep front wheels planted
  - **Trade-off**: Optimal value depends on other parameters
- **Typical Range:** 0.0-1.0 (0 = no effect, 1.0 = perfect anti-squat)
- **Tunability:** Adjust suspension geometry (instant centers, link angles)
- **Recommendation:** ✅ **ADD** - Medium impact, tunable, should optimize

---

### `ride_height_front`: 0.1 m
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** 
  - **Minimal direct impact**: Only affects aero (but no aero in base config)
  - **Ground clearance**: Must meet minimum clearance rules
  - **Secondary effect**: Could affect CG height slightly
- **Physics Impact:**
  - Could affect aero (if had aero)
  - Minimal effect on acceleration
- **Typical Range:** 0.05-0.15 m (ground clearance dependent)
- **Tunability:** Adjust suspension ride height
- **Recommendation:** ❌ **SKIP** - Minimal impact, constrained by ground clearance rules

---

### `ride_height_rear`: 0.1 m
- **Ideal Value:** ⬇️ **MINIMIZE**
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** Same as front - minimal impact
- **Recommendation:** ❌ **SKIP** - Minimal impact

---

### `wheel_rate_front`: 30000.0 N/m
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** 
  - **Minimal impact**: Affects suspension compression during load transfer
  - **Secondary effect**: Could slightly change effective CG height
  - **Very small effect** on acceleration
- **Physics Impact:**
  - Stiffer springs = less compression = CG stays higher (minimal)
  - Minimal effect for acceleration
- **Typical Range:** 20000-40000 N/m
- **Tunability:** Change spring rates
- **Recommendation:** ❌ **SKIP** - Negligible impact for acceleration

---

### `wheel_rate_rear`: 30000.0 N/m
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** Same as front - minimal impact
- **Recommendation:** ❌ **SKIP** - Negligible impact

---

## CONTROL PARAMETERS

### `launch_torque_limit`: 1000.0 N·m
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ✅ **YES** (in comprehensive version)
- **Impact Level:** 🔴 **HIGH**
- **Why Excluding?** Included in comprehensive_optimization.py but not quick version
- **Physics Impact:**
  - **Controls initial torque**: Limits torque at launch to prevent wheelspin
  - **Critical for launch**: Too high = spin, too low = slow start
  - **Balance with mu_max**: Must match tire grip capability
  - **Optimal value**: Depends on tire grip, surface conditions, vehicle dynamics
- **Typical Range:** 500-1500 N·m
- **Tunability:** Software control parameter (easy to adjust)
- **Recommendation:** ✅✅ **ADD TO OPTIMIZATION** - High impact, software tunable, critical for launch

---

### `target_slip_ratio`: 0.15
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ✅ **YES** - Range: (0.10, 0.20)
- **Should Optimize?** ✅ **YES**
- **Impact Level:** 🔴 **HIGH**
- **Why Excluding?** N/A - Already optimizing
- **Physics Impact:**
  - **Traction control target**: Maintains optimal slip for maximum grip
  - **Works with mu_slip_optimal**: Should match tire's optimal slip
  - Critical for maximizing tire grip during acceleration
  - **Optimal value**: Depends on tire characteristics
- **Recommendation:** ✅ **CONTINUE OPTIMIZING** - Critical parameter

---

### `torque_ramp_rate`: 500.0 N·m/s
- **Ideal Value:** 🔄 **OPTIMIZE** (run script)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **LOW**
- **Why Excluding?** 
  - **Smoothness parameter**: Controls how quickly torque increases
  - **Secondary to slip control**: Traction control handles grip, this is just smoothness
  - **Minimal impact**: Affects launch smoothness, not peak performance
- **Physics Impact:**
  - Slower ramp = smoother, potentially more controlled
  - Faster ramp = more aggressive, risk of wheelspin
  - Minimal effect on final time
- **Typical Range:** 300-800 N·m/s
- **Tunability:** Software parameter
- **Recommendation:** ❌ **SKIP** - Minimal impact

---

### `traction_control_enabled`: true
- **Ideal Value:** ⬆️ **MAXIMIZE** (always true)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO** (discrete parameter)
- **Impact Level:** 🔴 **HIGH** (but always on)
- **Why Excluding?** 
  - **Discrete parameter**: Boolean (on/off) - not optimizable
  - **Obviously enabled**: Traction control always better than none
- **Physics Impact:**
  - Enabled = maintains optimal slip
  - Disabled = risk of wheelspin
- **Recommendation:** N/A - Always enable (not optimizable)

---

## ENVIRONMENT PARAMETERS

### `air_density`: 1.225 kg/m³ (duplicate?)
- **Ideal Value:** N/A (environmental)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** N/A - Environmental
- **Why Excluding?** Cannot control weather/altitude
- **Note:** Duplicate of aerodynamics.air_density - should be consolidated
- **Recommendation:** ❌ **SKIP** - Environmental

---

### `ambient_temperature`: 20.0 °C
- **Ideal Value:** N/A (environmental)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **LOW** (not modeled)
- **Why Excluding?** 
  - **Environmental**: Cannot control weather
  - **Not modeled**: Current simulation doesn't include thermal effects
  - **Potential impact**: Could affect battery/motor performance (not modeled)
- **Recommendation:** ❌ **SKIP** - Not modeled, environmental

---

### `track_grade`: 0.0 (0%)
- **Ideal Value:** N/A (track property)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟠 **MEDIUM** (if variable, but it's environmental)
- **Why Excluding?** 
  - **Track property**: Cannot control track slope
  - **Fixed assumption**: Flat track
- **Physics Impact:**
  - Uphill = component of weight opposes motion
  - Downhill = helps acceleration
  - But track is what it is
- **Recommendation:** ❌ **SKIP** - Environmental/track property

---

### `wind_speed`: 0.0 m/s
- **Ideal Value:** N/A (environmental)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🟡 **VERY LOW**
- **Why Excluding?** 
  - **Environmental**: Cannot control wind
  - **Minimal at low speeds**: Wind effect is small for acceleration event
- **Physics Impact:**
  - Headwind = drag, tailwind = assistance
  - Minimal at low speeds
- **Recommendation:** ❌ **SKIP** - Environmental, minimal impact

---

### `surface_mu_scaling`: 1.0
- **Ideal Value:** N/A (track condition)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** 🔴 **VERY HIGH** (if variable, but it's environmental)
- **Why Excluding?** 
  - **Track condition**: Cannot control track grip
  - **Environmental variable**: Track surface changes with conditions
- **Physics Impact:**
  - **Multiplies all tire grip**: Would scale mu_max
  - **High impact if variable**: But it's track condition, not vehicle setup
- **Recommendation:** ❌ **SKIP** - Environmental/track condition

---

## SIMULATION PARAMETERS

### `dt`: 0.001 s
- **Ideal Value:** ⬇️ **MINIMIZE** (for accuracy)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** N/A - Simulation accuracy parameter
- **Why Excluding?** 
  - **Not a performance parameter**: Only affects simulation accuracy
  - **Fixed for accuracy**: Smaller = more accurate but slower computation
- **Recommendation:** ❌ **SKIP** - Simulation parameter, not vehicle parameter

---

### `max_time`: 30.0 s
- **Ideal Value:** N/A (simulation limit)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** N/A - Simulation limit
- **Why Excluding?** 
  - **Safety limit**: Maximum simulation time (prevents infinite loops)
  - **Rule reference**: Formula Student has 25s disqualification limit
- **Recommendation:** ❌ **SKIP** - Simulation constraint

---

### `target_distance`: 75.0 m
- **Ideal Value:** N/A (competition rule)
- **Currently Optimizing?** ❌ **NO**
- **Should Optimize?** ❌ **NO**
- **Impact Level:** N/A - Competition rule
- **Why Excluding?** 
  - **Formula Student rule**: Acceleration event is exactly 75m
  - **Fixed**: This is the competition rule, not a parameter
- **Recommendation:** ❌ **SKIP** - Rule constraint

---

## SUMMARY & RECOMMENDATIONS

### Currently Optimizing (4 parameters):
1. ✅ `mass.cg_x` - Very High impact - **OPTIMIZE**
2. ✅ `mass.cg_z` - Very High impact - **MINIMIZE**
3. ✅ `powertrain.gear_ratio` - Very High impact - **OPTIMIZE**
4. ✅ `control.target_slip_ratio` - High impact - **OPTIMIZE**

### Should ADD to Optimization (High Priority):
1. ✅✅ `tires.mu_max` - **VERY HIGH** - **MAXIMIZE** - **CRITICAL MISSING!**
2. ✅ `tires.radius_loaded` - High impact - **OPTIMIZE**
3. ✅ `tires.mu_slip_optimal` - Medium impact - **OPTIMIZE** (works with target_slip_ratio)
4. ✅ `control.launch_torque_limit` - High impact - **OPTIMIZE**
5. ✅ `mass.total_mass` - Very High impact - **MINIMIZE**
6. ✅ `suspension.anti_squat_ratio` - Medium impact - **OPTIMIZE**

### Could ADD (Medium Priority):
7. ⚠️ `powertrain.motor_torque_constant` - High impact - **MAXIMIZE** (if comparing motors)
8. ⚠️ `powertrain.wheel_inertia` - Medium impact - **MINIMIZE** (if comparing wheels)
9. ⚠️ `aerodynamics.cl_rear` - Medium impact - **MAXIMIZE** (if have aero)
10. ⚠️ `aerodynamics.cda` - Low impact - **MINIMIZE** (if have aero options)
11. ⚠️ `mass.wheelbase` - Low-Medium impact - **MINIMIZE** (within constraints)

### Should NOT Optimize:
- Environmental variables (weather, track) - cannot control
- Fixed rules (80kW, 75m) - competition constraints
- Zero impact parameters (track widths, yaw inertia, differential ratio)
- Negligible impact parameters (rolling resistance, battery resistance)
- Simulation parameters - not vehicle design choices

---

## Recommended Optimization Set

### Quick Optimization (8-9 parameters):
1. `mass.total_mass` ✅ **MINIMIZE**
2. `mass.cg_x` ✅ **OPTIMIZE**
3. `mass.cg_z` ✅ **MINIMIZE**
4. `tires.mu_max` ✅✅ **MAXIMIZE** - **ADD THIS!**
5. `tires.radius_loaded` ✅ **OPTIMIZE** - **ADD THIS!**
6. `tires.mu_slip_optimal` ✅ **OPTIMIZE** - **ADD THIS!**
7. `powertrain.gear_ratio` ✅ **OPTIMIZE**
8. `control.target_slip_ratio` ✅ **OPTIMIZE**
9. `control.launch_torque_limit` ✅ **OPTIMIZE** - **ADD THIS!**

### Comprehensive Optimization (15+ parameters):
Add the above, plus:
10. `suspension.anti_squat_ratio` - **OPTIMIZE**
11. `powertrain.motor_torque_constant` - **MAXIMIZE** (if comparing motors)
12. `powertrain.wheel_inertia` - **MINIMIZE** (if comparing wheels)
13. `aerodynamics.cl_rear` - **MAXIMIZE** (if have aero)
14. `aerodynamics.cda` - **MINIMIZE** (if have aero)
15. `mass.wheelbase` - **MINIMIZE** (within constraints)

---

## Impact Ranking (All Parameters)

### Very High Impact (Must Optimize):
1. `mass.total_mass` - **MINIMIZE** (inverse relationship: a = F/m)
2. `tires.mu_max` - **MAXIMIZE** (direct multiplication: F = μ × Fz)
3. `powertrain.gear_ratio` - **OPTIMIZE** (torque multiplication)
4. `mass.cg_x`, `mass.cg_z` - **OPTIMIZE/MINIMIZE** (load distribution)

### High Impact (Should Optimize):
5. `tires.radius_loaded` - **OPTIMIZE** (force conversion)
6. `control.target_slip_ratio` - **OPTIMIZE** (traction control)
7. `control.launch_torque_limit` - **OPTIMIZE** (launch strategy)
8. `powertrain.motor_torque_constant` - **MAXIMIZE** (motor selection)

### Medium Impact (Consider Optimizing):
9. `tires.mu_slip_optimal` - **OPTIMIZE**
10. `suspension.anti_squat_ratio` - **OPTIMIZE**
11. `powertrain.wheel_inertia` - **MINIMIZE** (3% effect)
12. `aerodynamics.cl_rear` - **MAXIMIZE** (at speed)
13. `mass.wheelbase` - **MINIMIZE** (low priority)

### Low Impact:
- Everything else...

---

## Ideal Value Summary by Category

### Minimize:
- `mass.total_mass`, `mass.cg_z`, `mass.unsprung_mass_*`, `mass.i_pitch`
- `tires.rolling_resistance_coeff`
- `powertrain.battery_internal_resistance`, `powertrain.wheel_inertia`
- `aerodynamics.cda`
- `suspension.ride_height_*`

### Maximize:
- `tires.mu_max`
- `powertrain.motor_torque_constant`, `powertrain.motor_max_current`, `powertrain.motor_efficiency`, `powertrain.battery_voltage_nominal`, `powertrain.battery_max_current`, `powertrain.drivetrain_efficiency`
- `aerodynamics.cl_front`, `aerodynamics.cl_rear`
- `control.traction_control_enabled` (always true)

### Optimize (Run Script):
- `mass.cg_x`, `mass.wheelbase`
- `tires.radius_loaded`, `tires.mu_slip_optimal`
- `powertrain.gear_ratio`
- `suspension.anti_squat_ratio`, `suspension.wheel_rate_*`
- `control.launch_torque_limit`, `control.target_slip_ratio`, `control.torque_ramp_rate`
