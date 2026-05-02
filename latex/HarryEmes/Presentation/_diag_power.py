"""Diagnose why simulated electrical power dips at the end of the run.

Re-runs the baseline simulation and prints, every 0.2 s, what the
powertrain is actually doing: motor speed, DC bus voltage *at that
instant* (read per-step from state history, not live from the
post-run powertrain object), whether field weakening is active, the
motor's capable mechanical/electrical power at that operating point,
and what the simulation actually delivered.

NOTE: the previous version of this script read ``V_dc`` live from the
post-run powertrain object and so reported the *same* (final)
voltage for every row. The motor capability columns it printed were
therefore evaluated at the wrong V_dc and gave a misleading picture.
The per-step values come off ``state.dc_bus_voltage``, which the
solver writes inside :meth:`DynamicsSolver._rk4_step` after the
energy storage update, so they are the true bus voltage at each
state-history sample.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver

cfg = load_config(ROOT / "config" / "vehicle_configs" / "base_vehicle.json")
solver = DynamicsSolver(cfg)
final = solver.solve()
hist = solver.state_history

t = np.array([s.time for s in hist])
v = np.array([s.velocity for s in hist])
p = np.array([s.power_consumed for s in hist])
vdc_arr = np.array([s.dc_bus_voltage for s in hist])

motor = solver.powertrain.motor
gear = cfg.powertrain.gear_ratio * cfg.powertrain.differential_ratio
print(f"motor: peak_torque={motor.peak_torque:.1f} Nm  "
      f"peak_power={motor.peak_power/1e3:.1f} kW  "
      f"base_speed_at_rated={motor.base_speed_at_rated_voltage:.1f} rad/s  "
      f"rated_voltage={motor.rated_voltage:.0f} V")
print(f"gear ratio overall = {gear}; "
      f"motor_max_current = {cfg.powertrain.motor_max_current:.0f} A "
      f"(Kt = {cfg.powertrain.motor_torque_constant})")

print(f"\n{'t':>5}  {'v':>6}  {'P_elec':>8}  {'V_dc':>7}  {'omega_m':>9}  "
      f"{'omega_b':>8}  {'T_max':>7}  {'P_max_m':>8}  {'P_max_e':>8}  {'FW?':>4}")
print("-" * 92)
for s in hist[::200]:  # ~every 0.2 s at 1 ms dt
    omega_w = s.velocity / cfg.tires.radius_loaded
    omega_m = omega_w * gear
    V_dc = s.dc_bus_voltage  # per-step, not live
    if motor is not None:
        omega_b = motor.calculate_base_speed(V_dc)
        T_max, in_fw, _ = motor.calculate_max_torque(
            omega_m, V_dc, use_peak=True
        )
        P_max_mech = T_max * omega_m
        P_max_elec = P_max_mech / cfg.powertrain.motor_efficiency
    else:
        omega_b = float("nan")
        T_max = P_max_mech = P_max_elec = float("nan")
        in_fw = False
    print(f"{s.time:5.2f}  {s.velocity*3.6:5.0f}  "
          f"{s.power_consumed/1e3:7.1f}  {V_dc:6.1f}  "
          f"{omega_m:8.1f}  {omega_b:7.1f}  {T_max:6.1f}  "
          f"{P_max_mech/1e3:7.1f}  {P_max_elec/1e3:7.1f}  "
          f"{'Y' if in_fw else 'N':>4}")

print(f"\nFinal: t={final.time:.3f} s, v={final.velocity*3.6:.1f} km/h")
print(f"V_dc start = {vdc_arr[1]:.1f} V (full charge), "
      f"V_dc end = {vdc_arr[-1]:.1f} V")
print(f"Peak P_elec      = {max(p)/1e3:.1f} kW")
print(f"P_elec at finish = {p[-1]/1e3:.1f} kW")
