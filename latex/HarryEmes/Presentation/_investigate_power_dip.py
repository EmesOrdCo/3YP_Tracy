"""End-to-end investigation of the end-of-run electrical-power dip.

Runs the simulation under a range of perturbations to localise the cause:

  Test 0  Baseline diagnostic (per-step V_dc, omega_m, motor capability).
  Test 1  Battery sanity-check (storage type flipped to constant-V battery).
  Test 2  Gear-ratio sweep (overall reduction 2.5 -> 7.0 in 0.25 steps).
  Test 3  Motor peak-current sweep (config 285 A -> 350 / 400 / 450 A).
  Test 4  Combined high-current + tuned gearing.
  Test 5  Supercap pack-size sweep (cells 200 -> 350).
  Energy budget: closed-form check of whether 80 kW is even feasible to the
  finish given the supercap energy and the motor's V_dc-dependent envelope.

The goal is to distinguish "this is a fixable control/tuning bug" from
"this hardware is energy-bound and the dip is unavoidable", and to give a
hardware-change recommendation that flips the answer.
"""

from __future__ import annotations

import copy
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver

CONFIG_PATH = ROOT / "config" / "vehicle_configs" / "base_vehicle.json"


@dataclass
class RunResult:
    label: str
    final_time: float
    final_velocity_kmh: float
    peak_p_elec_kw: float
    p_elec_at_finish_kw: float
    min_p_elec_in_phase_kw: float          # min P during 80-kW phase
    flatness_metric_kw: float              # std of P during 80-kW phase
    v_dc_start: float
    v_dc_end: float
    p_phase_start_t: Optional[float]       # time at which P first reached 80 kW (or 95% of cap)
    success: bool                          # True if fully reached target_distance
    target_distance: float


def _run(config_overrides: Optional[dict] = None, label: str = "") -> RunResult:
    """Run one simulation with overrides applied to the loaded config.

    ``config_overrides`` is a flat dict of dotted-paths under ``config``;
    e.g. {"powertrain.gear_ratio": 4.5, "powertrain.energy_storage_type":
    "battery"}.
    """
    cfg = load_config(CONFIG_PATH)
    if config_overrides:
        for path, value in config_overrides.items():
            obj = cfg
            parts = path.split(".")
            for p in parts[:-1]:
                obj = getattr(obj, p)
            setattr(obj, parts[-1], value)
    solver = DynamicsSolver(cfg)
    final = solver.solve()
    hist = solver.state_history

    t = np.array([s.time for s in hist])
    p = np.array([s.power_consumed for s in hist])
    vdc = np.array([s.dc_bus_voltage for s in hist])

    cap_w = cfg.powertrain.max_power_accumulator_outlet  # 80e3
    # Tight phase definition: from the moment P first reaches 99 % of the
    # cap, count *every* sample after as part of the phase. This skips the
    # FW-knee transient (where P briefly dips while the motor crosses base
    # speed) and captures the chronic dip we're investigating.
    above = np.where(p > 0.99 * cap_w)[0]
    if above.size:
        first_idx = int(above[0])
        phase_start_t = float(t[first_idx])
        p_phase = p[first_idx:]
        p_min_phase = float(p_phase.min())
        flatness = float(np.std(p_phase))
    else:
        phase_start_t = None
        p_min_phase = float(p.max())
        flatness = float("nan")

    success = bool(final.position >= cfg.target_distance - 1e-3)

    return RunResult(
        label=label,
        final_time=float(final.time),
        final_velocity_kmh=float(final.velocity * 3.6),
        peak_p_elec_kw=float(p.max() / 1e3),
        p_elec_at_finish_kw=float(p[-1] / 1e3),
        min_p_elec_in_phase_kw=p_min_phase / 1e3,
        flatness_metric_kw=flatness / 1e3,
        v_dc_start=float(vdc[1] if len(vdc) > 1 else vdc[0]),  # vdc[0] = 0 default
        v_dc_end=float(vdc[-1]),
        p_phase_start_t=phase_start_t,
        success=success,
        target_distance=float(cfg.target_distance),
    )


# ---------------------------------------------------------------------------
# TEST 0: baseline + per-step diagnostic table
# ---------------------------------------------------------------------------
def test_0_baseline() -> RunResult:
    print("=" * 88)
    print("TEST 0 — BASELINE DIAGNOSTIC")
    print("=" * 88)
    cfg = load_config(CONFIG_PATH)
    solver = DynamicsSolver(cfg)
    final = solver.solve()
    hist = solver.state_history
    motor = solver.powertrain.motor

    print(f"motor: peak_torque={motor.peak_torque:.1f} Nm  "
          f"peak_power={motor.peak_power/1e3:.1f} kW  "
          f"base_speed_at_rated={motor.base_speed_at_rated_voltage:.1f} rad/s  "
          f"rated_voltage={motor.rated_voltage:.0f} V")
    print(f"gear_ratio = {cfg.powertrain.gear_ratio} * "
          f"{cfg.powertrain.differential_ratio} = "
          f"{cfg.powertrain.gear_ratio * cfg.powertrain.differential_ratio}")
    print(f"motor_max_current = {cfg.powertrain.motor_max_current} A "
          f"(Kt = {cfg.powertrain.motor_torque_constant})")
    print(f"supercap: {cfg.powertrain.supercap_num_cells} cells, "
          f"V_init={cfg.powertrain.supercap_num_cells*cfg.powertrain.supercap_cell_voltage:.0f} V, "
          f"V_min={cfg.powertrain.supercap_min_voltage:.0f} V")

    print(f"\n{'t':>5}  {'v km/h':>6}  {'P_elec':>8}  {'V_dc':>7}  "
          f"{'omega_m':>9}  {'omega_b':>9}  "
          f"{'T_max':>7}  {'P_max_m':>8}  {'P_max_e':>8}  {'FW?':>4}")
    print("-" * 96)
    for s in hist[::200]:
        omega_w = s.velocity / cfg.tires.radius_loaded
        omega_m = omega_w * cfg.powertrain.gear_ratio * cfg.powertrain.differential_ratio
        V_dc = s.dc_bus_voltage  # per-step now, NOT live
        omega_base = motor.calculate_base_speed(V_dc)
        T_max, in_fw, _ = motor.calculate_max_torque(omega_m, V_dc, use_peak=True)
        P_max_mech = T_max * omega_m
        P_max_elec = P_max_mech / cfg.powertrain.motor_efficiency
        print(f"{s.time:5.2f}  {s.velocity*3.6:6.1f}  "
              f"{s.power_consumed/1e3:7.1f}  {V_dc:6.1f}  "
              f"{omega_m:8.1f}  {omega_base:8.1f}  "
              f"{T_max:6.1f}  {P_max_mech/1e3:7.1f}  {P_max_elec/1e3:7.1f}  "
              f"{'Y' if in_fw else 'N':>4}")

    res = _run(label="baseline")
    print(f"\nFINAL: t={res.final_time:.3f} s  v={res.final_velocity_kmh:.1f} km/h  "
          f"V_dc end={res.v_dc_end:.1f} V")
    print(f"P_elec phase start: t={res.p_phase_start_t:.3f} s")
    print(f"P_elec min in phase: {res.min_p_elec_in_phase_kw:.1f} kW")
    print(f"P_elec at finish:    {res.p_elec_at_finish_kw:.1f} kW")
    return res


# ---------------------------------------------------------------------------
# TEST 1: battery sanity check
# ---------------------------------------------------------------------------
def test_1_battery_sanity() -> RunResult:
    print("\n" + "=" * 88)
    print("TEST 1 — BATTERY SANITY CHECK (constant-V storage)")
    print("=" * 88)
    res = _run({"powertrain.energy_storage_type": "battery"}, label="battery-600V")
    print(f"final t        = {res.final_time:.3f} s "
          f"(baseline 3.78)")
    print(f"V_dc start/end = {res.v_dc_start:.1f} / {res.v_dc_end:.1f} V")
    print(f"P_elec peak    = {res.peak_p_elec_kw:.1f} kW")
    print(f"P_elec min in 80-kW phase = {res.min_p_elec_in_phase_kw:.1f} kW "
          f"(should be ~80 if voltage sag is the only cause)")
    print(f"P_elec at finish          = {res.p_elec_at_finish_kw:.1f} kW")
    return res


# ---------------------------------------------------------------------------
# TEST 2: gear-ratio sweep
# ---------------------------------------------------------------------------
def test_2_gear_sweep() -> List[RunResult]:
    print("\n" + "=" * 88)
    print("TEST 2 — GEAR RATIO SWEEP (overall reduction)")
    print("=" * 88)
    print(f"{'G':>5}  {'t_final':>8}  {'v_final':>8}  {'V_dc_end':>9}  "
          f"{'P_min':>7}  {'P_finish':>9}  {'phase_t0':>9}  ok?")
    print("-" * 80)
    results = []
    for g in np.arange(2.5, 7.01, 0.25):
        try:
            res = _run({"powertrain.gear_ratio": float(g)}, label=f"G={g}")
            results.append(res)
            ok = "Y" if res.success else "N"
            phase = f"{res.p_phase_start_t:.2f}" if res.p_phase_start_t else "  -- "
            print(f"{g:5.2f}  {res.final_time:8.3f}  "
                  f"{res.final_velocity_kmh:7.1f}  {res.v_dc_end:8.1f}  "
                  f"{res.min_p_elec_in_phase_kw:6.1f}  "
                  f"{res.p_elec_at_finish_kw:8.1f}  {phase:>9}  {ok}")
        except Exception as e:  # noqa: BLE001
            print(f"{g:5.2f}  ERROR: {e}")
    return results


# ---------------------------------------------------------------------------
# TEST 3: motor peak-current sweep
# ---------------------------------------------------------------------------
def test_3_current_sweep() -> List[RunResult]:
    print("\n" + "=" * 88)
    print("TEST 3 — MOTOR PEAK-CURRENT SWEEP (note: NOT a free fix — see commentary)")
    print("Convention: YASA's Kt=0.822 is Nm/A_RMS (datasheet '370 Nm @ 450 A_RMS').")
    print("BAMOCAR-PG-D3-700/400 peak rating: 400 A_peak phase = 285 A_RMS (same point).")
    print("So config 285 A is the correct A_RMS at the BAMOCAR's peak operating point;")
    print("raising it would require a different inverter, not a config tweak.")
    print("=" * 88)
    print(f"{'I_peak':>7}  {'T_peak':>7}  {'t_final':>8}  {'V_dc_end':>9}  "
          f"{'P_min':>7}  {'P_finish':>9}  ok?")
    print("-" * 72)
    results = []
    kt = 0.822
    for i_peak in [285.0, 320.0, 350.0, 380.0, 400.0, 425.0, 450.0]:
        res = _run({"powertrain.motor_max_current": i_peak},
                   label=f"I={i_peak:.0f}A")
        results.append(res)
        ok = "Y" if res.success else "N"
        print(f"{i_peak:7.0f}  {kt*i_peak:7.1f}  {res.final_time:8.3f}  "
              f"{res.v_dc_end:8.1f}  {res.min_p_elec_in_phase_kw:6.1f}  "
              f"{res.p_elec_at_finish_kw:8.1f}  {ok}")
    return results


# ---------------------------------------------------------------------------
# TEST 4: pack-size sweep (cells)
# ---------------------------------------------------------------------------
def test_4_pack_sweep() -> List[RunResult]:
    print("\n" + "=" * 88)
    print("TEST 4 — SUPERCAP PACK-SIZE SWEEP (cells)")
    print("(rated_voltage in motor scales with cell count via battery_voltage_nominal)")
    print("=" * 88)
    print(f"{'cells':>6}  {'V_init':>7}  {'t_final':>8}  {'V_dc_end':>9}  "
          f"{'P_min':>7}  {'P_finish':>9}  ok?")
    print("-" * 72)
    results = []
    for n in [200, 220, 240, 260, 280, 300, 320, 350]:
        v_init = 3.0 * n
        res = _run({
            "powertrain.supercap_num_cells": int(n),
            "powertrain.battery_voltage_nominal": float(v_init),
        }, label=f"N={n}")
        results.append(res)
        ok = "Y" if res.success else "N"
        print(f"{n:6d}  {v_init:7.0f}  {res.final_time:8.3f}  "
              f"{res.v_dc_end:8.1f}  {res.min_p_elec_in_phase_kw:6.1f}  "
              f"{res.p_elec_at_finish_kw:8.1f}  {ok}")
    return results


# ---------------------------------------------------------------------------
# TEST 5: combined fix attempt (best from H1+H2)
# ---------------------------------------------------------------------------
def test_5_combined() -> RunResult:
    print("\n" + "=" * 88)
    print("TEST 5 — COMBINED: high current + retuned gearing (no hardware change)")
    print("=" * 88)
    cfg = load_config(CONFIG_PATH)
    # Try the BAMOCAR's actual peak (400 A peak ≈ 285 A RMS · sqrt(2)) +
    # leave gear ratio alone first, then try optimum from sweep.
    candidates = [
        {"powertrain.motor_max_current": 400.0,
         "powertrain.gear_ratio": 5.5},
        {"powertrain.motor_max_current": 400.0,
         "powertrain.gear_ratio": 4.5},
        {"powertrain.motor_max_current": 400.0,
         "powertrain.gear_ratio": 4.0},
        {"powertrain.motor_max_current": 450.0,
         "powertrain.gear_ratio": 5.0},
    ]
    best = None
    print(f"{'I':>5}  {'G':>4}  {'t_final':>8}  {'V_dc_end':>9}  "
          f"{'P_min':>7}  {'P_finish':>9}")
    print("-" * 60)
    for over in candidates:
        res = _run(over, label=str(over))
        print(f"{over['powertrain.motor_max_current']:5.0f}  "
              f"{over['powertrain.gear_ratio']:4.2f}  "
              f"{res.final_time:8.3f}  {res.v_dc_end:8.1f}  "
              f"{res.min_p_elec_in_phase_kw:6.1f}  "
              f"{res.p_elec_at_finish_kw:8.1f}")
        if best is None or (res.success and res.min_p_elec_in_phase_kw >
                            best.min_p_elec_in_phase_kw):
            best = res
    return best


# ---------------------------------------------------------------------------
# Energy budget (closed-form bound)
# ---------------------------------------------------------------------------
def energy_budget() -> None:
    print("\n" + "=" * 88)
    print("CLOSED-FORM ENERGY BUDGET — can the supercap sustain 80 kW to finish?")
    print("=" * 88)
    cfg = load_config(CONFIG_PATH)
    pt = cfg.powertrain
    n = pt.supercap_num_cells
    v_init = 3.0 * n
    c_pack = pt.supercap_cell_capacitance / n
    e_init = 0.5 * c_pack * v_init ** 2

    # Motor envelope at full pack voltage
    kt = pt.motor_torque_constant
    i_peak = pt.motor_max_current
    t_peak = kt * i_peak
    eta_m = pt.motor_efficiency

    # In field weakening: omega_base(V_dc) = base_at_rated * V_dc / rated_V.
    # base_at_rated = (max_speed/2) * (rated_V / 700) [from create_motor_from_config]
    # => omega_base(V_dc) = (max_speed/2) * V_dc / 700 = 0.5 * 838 / 700 * V_dc
    #                     = 0.599 * V_dc. Independent of rated_V!
    omega_b_per_v = (pt.motor_max_speed / 2.0) / 700.0  # rad/s per volt
    p_cap_w = pt.max_power_accumulator_outlet  # 80 kW
    # P_elec required = P_mech / eta_m. Solving t_peak * omega_b * eta_m >= P_cap:
    v_min_for_cap = p_cap_w / (t_peak * omega_b_per_v * eta_m)

    # Energy at V_min_for_cap: motor can JUST deliver 80 kW
    e_min = 0.5 * c_pack * v_min_for_cap ** 2
    e_avail = e_init - e_min

    # Total energy required (rough): KE at finish + drag + rolling + ESR loss
    m = cfg.mass.total_mass
    v_finish_ms = 33.3  # ~120 km/h
    ke_finish = 0.5 * m * v_finish_ms ** 2
    cda = cfg.aerodynamics.cda
    rho = cfg.aerodynamics.air_density
    rr_coeff = cfg.tires.rolling_resistance_coeff
    avg_v = v_finish_ms / 2.0  # rough mean during run
    # Distance ~75 m; mean drag force at avg_v² ~ 0.5*rho*Cd*A*v_avg²
    drag_avg = 0.5 * rho * cda * (v_finish_ms ** 2) / 3.0  # rough integral
    e_drag = drag_avg * cfg.target_distance
    e_rr = rr_coeff * m * 9.81 * cfg.target_distance
    e_run_min = ke_finish + e_drag + e_rr
    # Add ~5% for ESR/efficiency losses
    e_run_with_losses = e_run_min / max(0.85, eta_m)

    print(f"Hardware:")
    print(f"  cells              = {n}")
    print(f"  V_init (3 V/cell)  = {v_init:.0f} V")
    print(f"  C_pack             = {c_pack:.3f} F")
    print(f"  E_init (0.5 C V²)  = {e_init/1e3:.1f} kJ")
    print(f"  T_peak             = Kt × I = {kt} × {i_peak} = {t_peak:.1f} Nm")
    print(f"  motor efficiency   = {eta_m}")
    print()
    print(f"Constraint to deliver {p_cap_w/1e3:.0f} kW electrical at the FINISH:")
    print(f"  omega_base required = P_cap / (T_peak·η) = {p_cap_w:.0f} / "
          f"({t_peak:.1f} × {eta_m}) = "
          f"{p_cap_w / (t_peak * eta_m):.1f} rad/s")
    print(f"  V_dc required        = omega_base / "
          f"{omega_b_per_v:.4f} = {v_min_for_cap:.1f} V")
    print(f"  E_min at this V_dc   = 0.5·C·V² = {e_min/1e3:.1f} kJ")
    print(f"  E_available (E_init - E_min) = {e_avail/1e3:.1f} kJ")
    print()
    print(f"Energy required to run the 75 m sprint:")
    print(f"  KE at finish (½·m·v²)    = {ke_finish/1e3:.1f} kJ")
    print(f"  Drag work (rough)        = {e_drag/1e3:.1f} kJ")
    print(f"  Rolling-resistance work  = {e_rr/1e3:.1f} kJ")
    print(f"  Sum (mech)               = {e_run_min/1e3:.1f} kJ")
    print(f"  /motor_efficiency (elec) = {e_run_with_losses/1e3:.1f} kJ")
    print()
    if e_run_with_losses > e_avail:
        deficit = e_run_with_losses - e_avail
        print(f"VERDICT: deficit of {deficit/1e3:.1f} kJ. With {n} cells the supercap")
        print(f"         CANNOT physically deliver the run while keeping V_dc ≥ "
              f"{v_min_for_cap:.0f} V at the end.")
        # Solve for minimum N such that E_avail >= E_run.
        # E_init = 0.5·(600/N)·(3N)² = 2700·N (J)
        # E_min  = 0.5·(600/N)·V_min² = 300·V_min²/N
        # E_avail = 2700 N - 300·V_min²/N >= e_run_with_losses
        # 2700 N² - e_run_with_losses N - 300·V_min² >= 0
        # NB: V_min for the cap is itself fixed by motor envelope, INDEPENDENT
        # of N (omega_b_per_v is just max_speed/2/700, independent of cells).
        a = 2700.0
        b = -e_run_with_losses
        c_ = -300.0 * v_min_for_cap ** 2
        n_min = (-b + (b ** 2 - 4 * a * c_) ** 0.5) / (2 * a)
        print(f"         Closed-form minimum cells (rough): "
              f"N >= {n_min:.0f} → recommend ~{int(np.ceil(n_min/10)*10)}.")
    else:
        print(f"VERDICT: feasibility OK on energy alone. The dip must come from")
        print(f"         a control/tuning issue — investigate launch profile.")


# ---------------------------------------------------------------------------
def main() -> None:
    test_0_baseline()
    test_1_battery_sanity()
    test_2_gear_sweep()
    test_3_current_sweep()
    test_4_pack_sweep()
    test_5_combined()
    energy_budget()


if __name__ == "__main__":
    main()
