#!/usr/bin/env python3
"""Grid search optimization with fixed wheelbase=1.573m and wheelie checks."""
import sys, copy, json, time
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from config.config_loader import load_config
from simulation.acceleration_sim import AccelerationSimulation

base = load_config(str(ROOT / "config" / "vehicle_configs" / "base_vehicle.json"))

def make_config(cg_x_ratio, gear_ratio, radius=0.228):
    c = copy.deepcopy(base)
    c.mass.total_mass = 175.0
    c.mass.cg_z = 0.22
    c.mass.wheelbase = 1.573
    c.mass.cg_x = cg_x_ratio * 1.573
    c.mass.unsprung_mass_front = 10.0
    c.mass.unsprung_mass_rear = 10.0
    c.mass.i_pitch = 120.0
    c.tires.mu_max = 1.8
    c.tires.rolling_resistance_coeff = 0.010
    c.tires.radius_loaded = radius
    c.tires.mu_slip_optimal = 0.12
    c.powertrain.motor_torque_constant = 0.5
    c.powertrain.motor_max_current = 200.0
    c.powertrain.motor_max_speed = 1000.0
    c.powertrain.motor_efficiency = 0.96
    c.powertrain.battery_voltage_nominal = 300.0
    c.powertrain.battery_internal_resistance = 0.008
    c.powertrain.battery_max_current = 300.0
    c.powertrain.gear_ratio = gear_ratio
    c.powertrain.drivetrain_efficiency = 0.97
    c.powertrain.wheel_inertia = 0.05
    c.aerodynamics.cda = 0.55
    c.aerodynamics.cl_front = 0.0
    c.aerodynamics.cl_rear = 0.0
    c.suspension.anti_squat_ratio = 0.3
    c.control.launch_torque_limit = 1000.0
    return c

print("=" * 70, flush=True)
print("GRID SEARCH: CG ratio x Gear Ratio (wheelbase=1.573m)", flush=True)
print("=" * 70, flush=True)

# Ranges aligned with run_quick_optimization.py BOUNDS:
#   cg_ratio in [0.60, 0.95], gear_ratio in [8.0, 14.0].
cg_ratios = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
gear_ratios = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]

best = None
results = []

total = len(cg_ratios) * len(gear_ratios)
print("Testing %d x %d = %d combos..." % (len(cg_ratios), len(gear_ratios), total), flush=True)
print("%6s %6s %8s %8s %8s %8s" % ("CG%", "Gear", "Time", "Vel", "Wheelie", "Fmin"), flush=True)
print("-" * 55, flush=True)

t0 = time.time()
count = 0
for cg_r in cg_ratios:
    for gr in gear_ratios:
        count += 1
        try:
            c = make_config(cg_r, gr)
            sim = AccelerationSimulation(c)
            r = sim.run()
            w = "YES" if r.wheelie_detected else "no"
            marker = ""
            if not r.wheelie_detected and (best is None or r.final_time < best[2]):
                best = (cg_r, gr, r.final_time, r)
                marker = " *BEST*"
            print("%5.0f%% %6.1f %7.3fs %6.1fkph %8s %7.0fN%s" % (
                cg_r*100, gr, r.final_time, r.final_velocity*3.6, w,
                r.min_front_normal_force, marker), flush=True)
            results.append((cg_r, gr, r.final_time, r.wheelie_detected, r.min_front_normal_force))
        except Exception as e:
            print("%5.0f%% %6.1f  ERROR: %s" % (cg_r*100, gr, e), flush=True)

elapsed = time.time() - t0
print("\nGrid search completed in %.0fs (%d configs)" % (elapsed, len(results)), flush=True)

if best:
    cg_r, gr, t, r = best
    print("\n" + "=" * 70, flush=True)
    print("BEST NO-WHEELIE CONFIG:", flush=True)
    print("  CG ratio: %.0f%% (%.3fm from front axle)" % (cg_r*100, cg_r*1.573), flush=True)
    print("  Gear ratio: %.1f" % gr, flush=True)
    print("  Time: %.3fs" % t, flush=True)
    print("  Velocity: %.1f m/s (%.1f km/h)" % (r.final_velocity, r.final_velocity*3.6), flush=True)
    print("  Min front normal: %.1fN" % r.min_front_normal_force, flush=True)
    print("  Power compliant: %s" % r.power_compliant, flush=True)
    print("  Wheelie: %s" % r.wheelie_detected, flush=True)
    print("=" * 70, flush=True)

    c = make_config(cg_r, gr)
    config_dict = {
        "mass": {"total_mass": c.mass.total_mass, "cg_x": c.mass.cg_x, "cg_z": c.mass.cg_z,
                 "wheelbase": c.mass.wheelbase, "front_track": 1.2, "rear_track": 1.2,
                 "i_yaw": 100.0, "i_pitch": 120.0, "unsprung_mass_front": 10.0, "unsprung_mass_rear": 10.0},
        "tires": {"radius_loaded": c.tires.radius_loaded, "mass": 3.0, "mu_max": 1.8,
                  "mu_slip_optimal": 0.12, "rolling_resistance_coeff": 0.01,
                  "tire_model_type": "pacejka", "pacejka_C": 1.65, "pacejka_pDx1": 1.55,
                  "pacejka_pDx2": -0.10, "pacejka_pKx1": 40000.0, "pacejka_pKx2": -2500.0,
                  "pacejka_E": 0.05, "pacejka_Fz0": 1500.0},
        "powertrain": {"motor_torque_constant": 0.5, "motor_max_current": 200.0,
                       "motor_max_speed": 1000.0, "motor_efficiency": 0.96,
                       "battery_voltage_nominal": 300.0, "battery_internal_resistance": 0.008,
                       "battery_max_current": 300.0, "gear_ratio": gr,
                       "drivetrain_efficiency": 0.97, "differential_ratio": 1.0,
                       "max_power_accumulator_outlet": 80000.0, "wheel_inertia": 0.05},
        "aerodynamics": {"cda": 0.55, "cl_front": 0.0, "cl_rear": 0.0, "air_density": 1.225},
        "suspension": {"anti_squat_ratio": 0.3, "ride_height_front": 0.05,
                       "ride_height_rear": 0.05, "wheel_rate_front": 35000.0, "wheel_rate_rear": 35000.0},
        "control": {"launch_torque_limit": 1000.0, "traction_control_enabled": True},
        "environment": {"air_density": 1.225, "ambient_temperature": 20.0,
                        "track_grade": 0.0, "wind_speed": 0.0, "surface_mu_scaling": 1.0},
        "simulation": {"dt": 0.001, "max_time": 30.0, "target_distance": 75.0}
    }
    with open(ROOT / "config" / "vehicle_configs" / "optimized_vehicle.json", "w") as f:
        json.dump(config_dict, f, indent=2)
    print("Saved to optimized_vehicle.json", flush=True)

    report = {"best_time_seconds": t, "final_velocity_ms": r.final_velocity,
              "power_compliant": r.power_compliant, "wheelie_detected": r.wheelie_detected,
              "min_front_normal_force": r.min_front_normal_force,
              "optimized_parameters": {"wheelbase": 1.573, "cg_x_ratio": cg_r,
                                        "cg_x": cg_r*1.573, "gear_ratio": gr}}
    with open(ROOT / "optimization_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved to optimization_report.json", flush=True)
else:
    print("\nWARNING: All configurations had wheelie! No safe config found.", flush=True)
