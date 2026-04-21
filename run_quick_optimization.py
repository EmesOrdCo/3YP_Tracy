#!/usr/bin/env python3
"""Quick optimization against the real hardware (YASA P400R + BAMOCAR 700/400
+ 200-cell supercap), with wheelbase fixed at the chassis spec and wheelie,
power, time and under-distance penalties applied."""
import sys, json, copy, time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

PACKAGE_ROOT = Path(__file__).parent.resolve()
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from config.config_loader import load_config
from config.vehicle_config import VehicleConfig
from simulation.acceleration_sim import AccelerationSimulation

# Hardware-constrained fixed values (YASA P400R + BAMOCAR-PG-D3-700/400,
# 300 V pack) recorded in 3YP Parameters.xlsx. Changing these means changing
# the real car.
FIXED_WHEELBASE = 1.6

# Aspirational lower bounds for weight / drag / losses: the team targets these
# during the design cycle. Optimiser pins these as the "best plausible" value.
MINIMIZE_PARAMS = {
    'mass.total_mass': 200.0, 'mass.cg_z': 0.22,
    'mass.unsprung_mass_front': 10.0, 'mass.unsprung_mass_rear': 10.0,
    'mass.i_pitch': 120.0, 'tires.rolling_resistance_coeff': 0.010,
    'powertrain.battery_internal_resistance': 0.008,
    'powertrain.wheel_inertia': 0.05, 'aerodynamics.cda': 0.55,
}
MAXIMIZE_PARAMS = {
    'tires.mu_max': 1.8, 'powertrain.motor_efficiency': 0.96,
    'powertrain.drivetrain_efficiency': 0.97,
}
# Hardware-pinned: real motor, real inverter, real pack, FS rule, real chassis.
# All values sourced from the datasheets in the project root:
#   * yasa-p400rdatasheet-rev-14.pdf  (motor)
#   * BAMOCAR-PG-D3-700_EN.pdf       (inverter)
#   * Eaton/Maxwell C46W-3R0-0600     (supercap cells)
FIXED_PARAMS = {
    'powertrain.max_power_accumulator_outlet': 80000.0,  # FS EV 2.2 rule
    'simulation.target_distance': 75.0,                  # FS acceleration event
    'aerodynamics.cl_front': 0.0, 'aerodynamics.cl_rear': 0.0,
    # YASA P400R: 370 Nm peak @ 450 A => Kt = 0.822 Nm/A.
    'powertrain.motor_torque_constant': 0.822,
    # BAMOCAR-PG-D3-700/400 peak current rating (400 A peak AC = 285 A RMS).
    'powertrain.motor_max_current': 285.0,
    'powertrain.motor_max_speed': 838.0,          # 8000 rpm datasheet max
    'powertrain.battery_voltage_nominal': 600.0,  # 200-cell supercap @ 3V/cell
    'powertrain.battery_max_current': 300.0,
    'powertrain.battery_internal_resistance': 0.14,  # 200 * 0.7 mOhm stack ESR
    'powertrain.differential_ratio': 1.0,
    'powertrain.energy_storage_type': 'supercapacitor',
    'powertrain.supercap_cell_voltage': 3.0,
    'powertrain.supercap_cell_capacitance': 600.0,
    'powertrain.supercap_cell_esr': 0.0007,
    'powertrain.supercap_num_cells': 200,
    'powertrain.supercap_min_voltage': 350.0,
    'environment.air_density': 1.225, 'environment.ambient_temperature': 20.0,
    'environment.track_grade': 0.0, 'environment.wind_speed': 0.0,
    'environment.surface_mu_scaling': 1.0,
    'mass.wheelbase': FIXED_WHEELBASE,
    'mass.front_track': 1.2, 'mass.rear_track': 1.2,
    'mass.i_yaw': 100.0, 'tires.mass': 3.0,
    'suspension.ride_height_front': 0.05, 'suspension.ride_height_rear': 0.05,
    'suspension.wheel_rate_front': 35000.0, 'suspension.wheel_rate_rear': 35000.0,
    'control.traction_control_enabled': True,
    'simulation.dt': 0.001, 'simulation.max_time': 30.0,
}

BOUNDS = {
    'cg_x_ratio': (0.55, 0.90),     # less rear-biased than before to tame wheelies
    'gear_ratio': (4.0, 10.0),      # stronger motor -> shorter gears work
    'radius_loaded': (0.200, 0.260),  # 19" tyres ~ 0.247 m
    'target_slip_ratio': (0.08, 0.20),
    'mu_slip_optimal': (0.08, 0.20),
    'launch_torque_limit': (400.0, 1500.0),
    'anti_squat_ratio': (0.0, 0.6),
}

n_evals = 0
best_time = float('inf')

def set_param(config, path, value):
    parts = path.split('.')
    if len(parts) == 2:
        obj = getattr(config, parts[0], None)
        if obj: setattr(obj, parts[1], value)

def make_config(x, base, dt=0.005):
    config = copy.deepcopy(base)
    for p, v in FIXED_PARAMS.items(): set_param(config, p, v)
    for p, v in MINIMIZE_PARAMS.items(): set_param(config, p, v)
    for p, v in MAXIMIZE_PARAMS.items(): set_param(config, p, v)
    
    config.mass.wheelbase = FIXED_WHEELBASE
    config.mass.cg_x = x[0] * FIXED_WHEELBASE
    config.powertrain.gear_ratio = x[1]
    config.tires.radius_loaded = x[2]
    config.control.target_slip_ratio = x[3]
    config.tires.mu_slip_optimal = x[4]
    config.control.launch_torque_limit = x[5]
    config.suspension.anti_squat_ratio = x[6]
    config.dt = dt
    config.max_time = 10.0
    return config

def objective(x, base):
    global n_evals, best_time
    try:
        config = make_config(x, base, dt=0.005)
        errors = config.validate()
        if errors: return 1e6
        
        sim = AccelerationSimulation(config)
        result = sim.run()
        n_evals += 1
        
        penalty = 0.0
        if not result.power_compliant: penalty += 1e5
        if not result.time_compliant: penalty += 1e4
        if result.wheelie_detected: penalty += 1e3
        if result.final_distance < 75.0: penalty += 1e6
        
        val = result.final_time + penalty
        if val < best_time:
            best_time = val
        return val
    except:
        return 1e6


def main():
    print("=" * 70, flush=True)
    print(f"QUICK OPTIMIZATION \u2014 Wheelbase fixed at {FIXED_WHEELBASE:.3f} m", flush=True)
    print("=" * 70, flush=True)
    
    base = load_config(str(PACKAGE_ROOT / "config" / "vehicle_configs" / "base_vehicle.json"))
    
    global n_evals, best_time
    n_evals = 0
    best_time = float('inf')
    t0 = time.time()
    
    bounds_list = list(BOUNDS.values())
    mid = np.array([(lo+hi)/2 for lo, hi in bounds_list])
    
    rng = np.random.RandomState(42)
    starts = [mid]
    for _ in range(4):
        starts.append(np.array([rng.uniform(lo, hi) for lo, hi in bounds_list]))
    
    best_x = None
    best_val = float('inf')
    
    for i, x0 in enumerate(starts):
        print(f"\n  Start {i+1}/5: cg_ratio={x0[0]:.2f}, gear={x0[1]:.1f}, "
              f"radius={x0[2]:.3f}, slip={x0[3]:.3f}", flush=True)
        
        res = minimize(objective, x0, args=(base,), method='Nelder-Mead',
                       options={'maxiter': 200, 'xatol': 0.002, 'fatol': 0.01})
        
        print(f"    → obj={res.fun:.4f}s ({res.nfev} evals)", flush=True)
        
        if res.fun < best_val:
            best_val = res.fun
            best_x = res.x
    
    elapsed = time.time() - t0
    
    # Final run with full accuracy
    print(f"\nRunning final verification (dt=0.001)...", flush=True)
    final_config = make_config(best_x, base, dt=0.001)
    final_config.max_time = 30.0
    sim = AccelerationSimulation(final_config)
    result = sim.run()
    
    print(f"\n{'='*70}", flush=True)
    print("OPTIMIZATION RESULTS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"\n✓ Best Time: {result.final_time:.4f} seconds", flush=True)
    print(f"✓ Final Velocity: {result.final_velocity:.2f} m/s "
          f"({result.final_velocity * 3.6:.1f} km/h)", flush=True)
    print(f"✓ Power Compliant: {result.power_compliant}", flush=True)
    print(f"✓ Time Compliant: {result.time_compliant}", flush=True)
    print(f"✓ Wheelie Detected: {result.wheelie_detected}", flush=True)
    if result.wheelie_detected:
        print(f"  ⚠️  Wheelie at t={result.wheelie_time:.3f}s", flush=True)
    else:
        print(f"  Min Front Normal Force: {result.min_front_normal_force:.1f} N", flush=True)
    print(f"✓ Total Evaluations: {n_evals}", flush=True)
    print(f"✓ Optimization Time: {elapsed:.1f} seconds", flush=True)
    
    cg_x = best_x[0] * FIXED_WHEELBASE
    rear_pct = best_x[0] * 100
    
    print(f"\n{'='*70}", flush=True)
    print("OPTIMIZED PARAMETERS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"\n  Chassis Geometry:", flush=True)
    print(f"    Wheelbase:           {FIXED_WHEELBASE:.4f} m (FIXED)", flush=True)
    print(f"    CG X (absolute):     {cg_x:.4f} m from front axle", flush=True)
    print(f"    CG X (ratio):        {rear_pct:.1f}% of wheelbase (rearward)", flush=True)
    print(f"    Weight Distribution:  {100-rear_pct:.1f}% front / {rear_pct:.1f}% rear", flush=True)
    print(f"\n  Powertrain:", flush=True)
    print(f"    Gear Ratio:          {best_x[1]:.3f}", flush=True)
    print(f"\n  Tires:", flush=True)
    print(f"    Loaded Radius:       {best_x[2]:.4f} m ({best_x[2]*1000:.1f} mm)", flush=True)
    print(f"    Optimal Slip Ratio:  {best_x[4]:.4f}", flush=True)
    print(f"\n  Control Strategy:", flush=True)
    print(f"    Target Slip Ratio:   {best_x[3]:.4f}", flush=True)
    print(f"    Launch Torque Limit: {best_x[5]:.1f} N·m", flush=True)
    print(f"\n  Suspension:", flush=True)
    print(f"    Anti-Squat Ratio:    {best_x[6]:.4f}", flush=True)
    
    # Save config
    config_dict = {
        'mass': {
            'total_mass': final_config.mass.total_mass,
            'cg_x': final_config.mass.cg_x,
            'cg_z': final_config.mass.cg_z,
            'wheelbase': final_config.mass.wheelbase,
            'front_track': final_config.mass.front_track,
            'rear_track': final_config.mass.rear_track,
            'i_yaw': final_config.mass.i_yaw,
            'i_pitch': final_config.mass.i_pitch,
            'unsprung_mass_front': final_config.mass.unsprung_mass_front,
            'unsprung_mass_rear': final_config.mass.unsprung_mass_rear,
        },
        'tires': {
            'radius_loaded': final_config.tires.radius_loaded,
            'mass': final_config.tires.mass,
            'mu_max': final_config.tires.mu_max,
            'mu_slip_optimal': final_config.tires.mu_slip_optimal,
            'rolling_resistance_coeff': final_config.tires.rolling_resistance_coeff,
            'tire_model_type': final_config.tires.tire_model_type,
            # Pass the Pacejka coefficients the optimiser actually saw; hard-
            # coding them here desynchronises the saved config from the run.
            'pacejka_C': final_config.tires.pacejka_C,
            'pacejka_pDx1': final_config.tires.pacejka_pDx1,
            'pacejka_pDx2': final_config.tires.pacejka_pDx2,
            'pacejka_pKx1': final_config.tires.pacejka_pKx1,
            'pacejka_pKx2': final_config.tires.pacejka_pKx2,
            'pacejka_E': final_config.tires.pacejka_E,
            'pacejka_Fz0': final_config.tires.pacejka_Fz0,
        },
        'powertrain': {
            'motor_torque_constant': final_config.powertrain.motor_torque_constant,
            'motor_max_current': final_config.powertrain.motor_max_current,
            'motor_max_speed': final_config.powertrain.motor_max_speed,
            'motor_efficiency': final_config.powertrain.motor_efficiency,
            'battery_voltage_nominal': final_config.powertrain.battery_voltage_nominal,
            'battery_internal_resistance': final_config.powertrain.battery_internal_resistance,
            'battery_max_current': final_config.powertrain.battery_max_current,
            'gear_ratio': final_config.powertrain.gear_ratio,
            'drivetrain_efficiency': final_config.powertrain.drivetrain_efficiency,
            'differential_ratio': final_config.powertrain.differential_ratio,
            'max_power_accumulator_outlet': final_config.powertrain.max_power_accumulator_outlet,
            'wheel_inertia': final_config.powertrain.wheel_inertia,
            'energy_storage_type': final_config.powertrain.energy_storage_type,
            'supercap_cell_voltage': final_config.powertrain.supercap_cell_voltage,
            'supercap_cell_capacitance': final_config.powertrain.supercap_cell_capacitance,
            'supercap_cell_esr': final_config.powertrain.supercap_cell_esr,
            'supercap_num_cells': final_config.powertrain.supercap_num_cells,
            'supercap_min_voltage': final_config.powertrain.supercap_min_voltage,
        },
        'aerodynamics': {
            'cda': final_config.aerodynamics.cda,
            'cl_front': 0.0, 'cl_rear': 0.0, 'air_density': 1.225,
        },
        'suspension': {
            'anti_squat_ratio': final_config.suspension.anti_squat_ratio,
            'ride_height_front': 0.05, 'ride_height_rear': 0.05,
            'wheel_rate_front': 35000.0, 'wheel_rate_rear': 35000.0,
        },
        'control': {
            'launch_torque_limit': final_config.control.launch_torque_limit,
            'traction_control_enabled': True,
        },
        'environment': {
            'air_density': 1.225, 'ambient_temperature': 20.0,
            'track_grade': 0.0, 'wind_speed': 0.0, 'surface_mu_scaling': 1.0,
        },
        'simulation': {'dt': 0.001, 'max_time': 30.0, 'target_distance': 75.0},
    }
    
    out = PACKAGE_ROOT / "config" / "vehicle_configs" / "optimized_vehicle.json"
    with open(out, 'w') as f:
        json.dump(config_dict, f, indent=2)
    print(f"\n✓ Saved to: {out}", flush=True)
    
    report = {
        'best_time_seconds': float(result.final_time),
        'final_velocity_ms': float(result.final_velocity),
        'power_compliant': bool(result.power_compliant),
        'wheelie_detected': bool(result.wheelie_detected),
        'min_front_normal_force': float(result.min_front_normal_force),
        'n_evaluations': int(n_evals),
        'optimization_time_seconds': float(elapsed),
        'optimized_parameters': {
            'wheelbase': FIXED_WHEELBASE,
            'cg_x_ratio': float(best_x[0]),
            'cg_x': float(cg_x),
            'gear_ratio': float(best_x[1]),
            'radius_loaded': float(best_x[2]),
            'target_slip_ratio': float(best_x[3]),
            'mu_slip_optimal': float(best_x[4]),
            'launch_torque_limit': float(best_x[5]),
            'anti_squat_ratio': float(best_x[6]),
        },
    }
    with open(PACKAGE_ROOT / "optimization_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    print(f"✓ Report saved to: optimization_report.json", flush=True)
    
    print(f"\n{'='*70}", flush=True)
    print("OPTIMIZATION COMPLETE", flush=True)
    print(f"{'='*70}", flush=True)


if __name__ == "__main__":
    main()
