# Vehicle Configuration Parameters - Units Reference

This document lists all parameters in the vehicle configuration JSON files with their units.

## MASS PARAMETERS

```json
"mass": {
  "total_mass": 250.0,              // kg
  "cg_x": 1.2,                      // m (from front axle)
  "cg_z": 0.3,                      // m (height from ground)
  "wheelbase": 1.6,                 // m
  "front_track": 1.2,               // m
  "rear_track": 1.2,                // m
  "i_yaw": 100.0,                   // kg·m² (yaw moment of inertia)
  "i_pitch": 200.0,                 // kg·m² (pitch moment of inertia)
  "unsprung_mass_front": 15.0,      // kg
  "unsprung_mass_rear": 15.0        // kg
}
```

## TIRE PARAMETERS

```json
"tires": {
  "radius_loaded": 0.2286,          // m (loaded tire radius)
  "mass": 3.0,                      // kg (per tire)
  "mu_max": 1.5,                    // dimensionless (maximum friction coefficient)
  "mu_slip_optimal": 0.15,          // dimensionless (optimal slip ratio)
  "rolling_resistance_coeff": 0.015 // dimensionless (rolling resistance coefficient)
}
```

## POWERTRAIN PARAMETERS

```json
"powertrain": {
  "motor_torque_constant": 0.5,           // N·m/A (motor torque per amp)
  "motor_max_current": 200.0,             // A (amperes)
  "motor_max_speed": 1000.0,              // rad/s (radians per second)
  "motor_efficiency": 0.95,               // dimensionless (0-1, 95% = 0.95)
  "battery_voltage_nominal": 300.0,       // V (volts)
  "battery_internal_resistance": 0.01,    // Ω (ohms)
  "battery_max_current": 300.0,           // A (amperes)
  "gear_ratio": 10.0,                     // dimensionless (motor speed / wheel speed)
  "drivetrain_efficiency": 0.95,          // dimensionless (0-1, 95% = 0.95)
  "differential_ratio": 1.0,              // dimensionless (left/right wheel ratio)
  "max_power_accumulator_outlet": 80000.0, // W (watts) - Formula Student rule: 80kW max
  "wheel_inertia": 0.1                    // kg·m² (wheel rotational moment of inertia)
}
```

## AERODYNAMICS PARAMETERS

```json
"aerodynamics": {
  "cda": 0.8,                      // m² (drag coefficient × frontal area)
  "cl_front": 0.0,                 // dimensionless (front downforce coefficient)
  "cl_rear": 0.0,                  // dimensionless (rear downforce coefficient)
  "air_density": 1.225             // kg/m³ (at sea level, 15°C)
}
```

## SUSPENSION PARAMETERS

```json
"suspension": {
  "anti_squat_ratio": 0.0,         // dimensionless (0-1, suspension geometry effect)
  "ride_height_front": 0.1,        // m (front ride height from ground)
  "ride_height_rear": 0.1,         // m (rear ride height from ground)
  "wheel_rate_front": 30000.0,     // N/m (front spring rate)
  "wheel_rate_rear": 30000.0       // N/m (rear spring rate)
}
```

## CONTROL PARAMETERS

```json
"control": {
  "launch_torque_limit": 1000.0,          // N·m (wheel torque limit at launch)
  "target_slip_ratio": 0.15,              // dimensionless (traction control target slip)
  "torque_ramp_rate": 500.0,              // N·m/s (torque increase rate)
  "traction_control_enabled": true        // boolean (enable/disable traction control)
}
```

## ENVIRONMENT PARAMETERS

```json
"environment": {
  "air_density": 1.225,            // kg/m³ (atmospheric air density)
  "ambient_temperature": 20.0,     // °C (celsius)
  "track_grade": 0.0,              // dimensionless (slope ratio, 0 = flat, 0.1 = 10% uphill)
  "wind_speed": 0.0,               // m/s (headwind positive, tailwind negative)
  "surface_mu_scaling": 1.0        // dimensionless (grip multiplier, 1.0 = normal surface)
}
```

## SIMULATION PARAMETERS

```json
"simulation": {
  "dt": 0.001,                     // s (time step for numerical integration)
  "max_time": 30.0,                // s (maximum simulation time - safety limit)
  "target_distance": 75.0          // m (Formula Student acceleration event distance)
}
```

## Quick Reference Summary

### Length (m)
- cg_x, cg_z, wheelbase, front_track, rear_track
- radius_loaded, ride_height_front, ride_height_rear
- target_distance

### Mass (kg)
- total_mass, unsprung_mass_front, unsprung_mass_rear
- tires.mass

### Moment of Inertia (kg·m²)
- i_yaw, i_pitch, wheel_inertia

### Force/Torque (N, N·m)
- launch_torque_limit (N·m)
- motor_torque_constant (N·m/A)
- wheel_rate_front, wheel_rate_rear (N/m)

### Electrical (V, A, Ω, W)
- battery_voltage_nominal (V)
- motor_max_current, battery_max_current (A)
- battery_internal_resistance (Ω)
- max_power_accumulator_outlet (W)

### Angular Velocity (rad/s)
- motor_max_speed

### Dimensionless (unitless)
- mu_max, mu_slip_optimal, target_slip_ratio, rolling_resistance_coeff
- motor_efficiency, drivetrain_efficiency
- gear_ratio, differential_ratio, anti_squat_ratio
- cl_front, cl_rear, track_grade, surface_mu_scaling

### Density (kg/m³)
- air_density

### Time (s)
- dt, max_time

### Temperature (°C)
- ambient_temperature

### Velocity (m/s)
- wind_speed

### Rate (N·m/s)
- torque_ramp_rate

