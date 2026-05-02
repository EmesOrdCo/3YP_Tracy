"""Produce the remaining report assets: time decomposition, energy
budget, Monte Carlo histogram, and optimiser convergence trace.

Outputs:
    figures/mc_histogram.pdf
    figures/optim_convergence.pdf
    extras.json   (all numerical values referenced by main.tex)
"""

from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import minimize

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

BASE_CFG = REPO / "config" / "vehicle_configs" / "base_vehicle.json"


# ----------------------------------------------------------------------
def run_sim(cfg) -> Dict:
    """Run a single simulation and return the trace + headline metrics."""
    solver = DynamicsSolver(cfg)
    final = solver.solve()
    hist = solver.state_history
    t = np.array([s.time for s in hist])
    return dict(
        final_time=float(final.time),
        final_velocity=float(final.velocity),
        peak_power=float(max(s.power_consumed for s in hist)),
        min_fz_front=float(min(s.normal_force_front for s in hist)),
        wheelie=any(s.normal_force_front <= 0 for s in hist),
        t=t,
        v=np.array([s.velocity for s in hist]),
        fdrag=np.array([getattr(s, "drag_force", 0.0) for s in hist]),
        frr=np.array([getattr(s, "rolling_resistance_front", 0.0)
                      + getattr(s, "rolling_resistance_rear", 0.0)
                      for s in hist]),
        fx=np.array([getattr(s, "tire_force_rear", 0.0) for s in hist]),
        p=np.array([s.power_consumed for s in hist]),
    )


# ----------------------------------------------------------------------
# 1. Energy budget and time decomposition
# ----------------------------------------------------------------------
print("--- 1. Energy budget and time decomposition ---")
cfg = load_config(BASE_CFG)
base = run_sim(cfg)
t = base["t"]; v = base["v"]; p = base["p"]
fdrag = np.abs(base["fdrag"]); frr = np.abs(base["frr"]); fx = np.abs(base["fx"])

# Trapezoidal integration of power vs time = energy.
def trap(y, x):
    return float(np.trapz(y, x))

m_v = cfg.mass.total_mass
P_max = cfg.powertrain.max_power_accumulator_outlet
eta_drv = cfg.powertrain.drivetrain_efficiency

E_elec = trap(p, t)                       # total electrical energy in
E_drag = trap(fdrag * v, t)               # drag dissipation
E_rr   = trap(frr * v, t)                 # rolling dissipation
E_mech = trap(fx * v, t)                  # mechanical work into tractive force
KE_final = 0.5 * m_v * v[-1] ** 2         # kinetic energy at 75 m
E_drv_loss = E_elec - (E_mech)            # everything from accumulator to wheel
# Alternative decomposition: power-budget from lower bound.
# Lower bound assumes all P_max is converted to KE. Reality:
#   KE_final = E_elec - E_drv_loss - E_drag - E_rr - energy not delivered to car during traction phase
# We can express each loss as an "equivalent extra time" over P_max:
dt_drag = E_drag / P_max
dt_rr   = E_rr   / P_max
dt_drv  = (1.0 - eta_drv) * E_mech / P_max  # alternatively E_drv_loss / P_max
# Traction-limited deficit:
#   integral of (P_max - P_elec) over the traction-limited phase
#   (when p < 0.95 P_max).
mask_tl = p < 0.95 * P_max
deficit = np.where(mask_tl, P_max - p, 0.0)
E_traction_deficit = trap(deficit, t)
dt_traction = E_traction_deficit / P_max
# Sum of decomposed extras:
dt_sum = dt_drag + dt_rr + dt_drv + dt_traction
# Baseline time minus analytical bound.
t_sim = base["final_time"]
t_cp = (75.0 / ((2.0 / 3.0) * math.sqrt(2.0 * P_max / m_v))) ** (2.0 / 3.0)
gap = t_sim - t_cp

# Residual = gap not explained by the four categories above.
dt_residual = gap - dt_sum

print(f"  Sim time       = {t_sim:.3f} s")
print(f"  Analytical     = {t_cp:.3f} s")
print(f"  Gap            = {gap*1000:.1f} ms")
print(f"  Drag           = {dt_drag*1000:+.1f} ms")
print(f"  Rolling        = {dt_rr*1000:+.1f} ms")
print(f"  Drivetrain     = {dt_drv*1000:+.1f} ms")
print(f"  Traction-lim   = {dt_traction*1000:+.1f} ms")
print(f"  Residual       = {dt_residual*1000:+.1f} ms")
print(f"  Sum (check)    = {dt_sum*1000:+.1f} ms")
print(f"  Energy budget: E_elec={E_elec/1e3:.1f} kJ, KE_final={KE_final/1e3:.1f} kJ, "
      f"E_drag={E_drag/1e3:.1f} kJ, E_rr={E_rr/1e3:.1f} kJ, "
      f"E_drv_loss={E_drv_loss/1e3:.1f} kJ")


# ----------------------------------------------------------------------
# 2. Monte Carlo robustness
# ----------------------------------------------------------------------
print("\n--- 2. Monte Carlo (500 samples) ---")
rng = np.random.default_rng(42)
N_MC = 500
# Parameter distributions (symmetric around baseline unless stated).
#   mass:            N(250, 8 kg)       — build tolerance
#   mu_max:          N(1.70, 0.08)      — tyre variability
#   cg_x:            N(1.14, 0.03 m)    — loaded-position uncertainty
#   cg_z:            N(0.22, 0.015 m)   — same
#   eta_drv:         N(0.95, 0.015)     — driveline efficiency spread
#   CdA:             N(0.80, 0.05)      — bodywork tolerance
mc_times = []
mc_power_ok = []
mc_time_ok = []
mc_wheelie = []
for i in range(N_MC):
    c = copy.deepcopy(cfg)
    c.mass.total_mass += rng.normal(0, 8.0)
    c.tires.pacejka_pDx1 = 1.45 * (1 + rng.normal(0, 0.06))
    c.mass.cg_x          += rng.normal(0, 0.03)
    c.mass.cg_z          = max(0.15, c.mass.cg_z + rng.normal(0, 0.015))
    c.powertrain.drivetrain_efficiency = min(0.99, max(0.85,
                            c.powertrain.drivetrain_efficiency + rng.normal(0, 0.015)))
    c.aerodynamics.cda   = max(0.5, c.aerodynamics.cda + rng.normal(0, 0.05))
    try:
        r = run_sim(c)
        mc_times.append(r["final_time"])
        mc_power_ok.append(r["peak_power"] <= P_max * 1.0001)
        mc_time_ok.append(r["final_time"] < 25.0)
        mc_wheelie.append(r["wheelie"])
    except Exception as e:
        print(f"  Sample {i} failed: {e}")
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{N_MC} done, running mean = {np.mean(mc_times):.3f} s")

mc_times = np.array(mc_times)
mc_mean = float(np.mean(mc_times))
mc_std = float(np.std(mc_times))
mc_p05 = float(np.percentile(mc_times, 5))
mc_p95 = float(np.percentile(mc_times, 95))
print(f"  Mean {mc_mean:.3f}, std {mc_std:.3f}, P5 {mc_p05:.3f}, P95 {mc_p95:.3f}")
print(f"  Power compliant: {sum(mc_power_ok)}/{len(mc_power_ok)}")
print(f"  Time compliant:  {sum(mc_time_ok)}/{len(mc_time_ok)}")
print(f"  No wheelie:      {sum(1 for w in mc_wheelie if not w)}/{len(mc_wheelie)}")

# MC histogram.
fig, ax = plt.subplots(figsize=(7.0, 4.0))
ax.hist(mc_times, bins=30, color="#4a6fa5", edgecolor="white", alpha=0.9)
ax.axvline(mc_mean, color="k", lw=1.5, label=f"Mean {mc_mean:.3f} s")
ax.axvline(mc_p05, color="0.4", lw=1.0, ls="--",
            label=f"5–95\\% band [{mc_p05:.3f}, {mc_p95:.3f}]")
ax.axvline(mc_p95, color="0.4", lw=1.0, ls="--")
ax.axvline(t_sim, color="#d62728", lw=1.2, ls=":",
            label=f"Baseline {t_sim:.3f} s")
ax.set(xlabel="Predicted 75 m time (s)", ylabel="Count",
       title=f"Monte Carlo distribution over {N_MC} samples "
             f"({sum(mc_time_ok)}/{N_MC} compliant)")
ax.legend(loc="upper right")
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "mc_histogram.pdf", bbox_inches="tight")
plt.close(fig)


# ----------------------------------------------------------------------
# 3. Optimiser convergence
# ----------------------------------------------------------------------
print("\n--- 3. Optimiser convergence trace ---")
# 7-variable Nelder-Mead optimiser. Decision variables:
# (wheelbase, cg_x_frac, gear_ratio, r_wheel, mu_slip_opt, launch_torque, AS)
from scipy.optimize import minimize


def unpack(x, base_cfg):
    """Return a configured copy with the optimisation variables applied."""
    c = copy.deepcopy(base_cfg)
    c.mass.wheelbase             = float(x[0])
    c.mass.cg_x                  = float(x[1]) * c.mass.wheelbase
    c.powertrain.gear_ratio      = float(x[2])
    c.tires.radius_loaded        = float(x[3])
    c.tires.mu_slip_optimal      = float(x[4])
    c.control.launch_torque_limit = float(x[5])
    c.suspension.anti_squat_ratio = float(x[6])
    return c


x0 = np.array([1.60, 0.712, 5.5, 0.247, 0.14, 1000.0, 0.12])
bounds_low  = np.array([1.525, 0.50, 3.0, 0.20, 0.08, 400.0, 0.00])
bounds_high = np.array([1.750, 0.88, 7.0, 0.28, 0.20, 1200.0, 1.00])

trace = []  # (iter, best_time, wheelie_ok, power_ok)

def objective(x):
    x_clip = np.clip(x, bounds_low, bounds_high)
    try:
        c = unpack(x_clip, cfg)
        r = run_sim(c)
        penalty = 0.0
        if r["wheelie"]:
            penalty += 2.0
        if r["peak_power"] > P_max * 1.0001:
            penalty += 1.0
        if r["final_time"] >= 25.0:
            penalty += 5.0
        val = r["final_time"] + penalty
        trace.append(dict(val=val, time=r["final_time"],
                          wheelie=r["wheelie"],
                          peak_power=r["peak_power"]))
        return val
    except Exception:
        trace.append(dict(val=10.0, time=10.0,
                          wheelie=True, peak_power=0))
        return 10.0


print("  Running 500-eval Nelder-Mead (shortened for convergence plot)...")
result = minimize(objective, x0, method="Nelder-Mead",
                  options=dict(maxiter=500, maxfev=500,
                                xatol=1e-4, fatol=1e-4, disp=False))
print(f"  Final x = {result.x}")
print(f"  Final t = {result.fun:.3f} s  ({len(trace)} evals)")

iters = np.arange(1, len(trace) + 1)
best_so_far = np.minimum.accumulate(np.array([tr["val"] for tr in trace]))
times = np.array([tr["time"] for tr in trace])
wheelies = np.array([tr["wheelie"] for tr in trace])
powers = np.array([tr["peak_power"] for tr in trace]) / 1e3

# Convergence plot (2 panels).
fig, axes = plt.subplots(2, 1, figsize=(7.0, 5.2), sharex=True)
ax = axes[0]
ax.plot(iters, times, ".", ms=2.5, color="0.6", label="Eval $t_{75}$")
ax.plot(iters, best_so_far, "-", color="#1f77b4", lw=1.6,
        label="Best feasible so far (incl. penalty)")
ax.set(ylabel="Predicted 75 m time (s)",
       title="Nelder–Mead convergence of the acceleration optimiser")
ax.legend(loc="upper right")
ax.grid(alpha=0.3)
ax.set_ylim(3.3, 5.0)

ax = axes[1]
ax.plot(iters, powers, ".", ms=2.5, color="#9467bd", label="Peak electrical P")
ax.axhline(80.0, color="r", ls="--", lw=1.0, label="FS-EV 2.2 cap")
# Mark wheelie evaluations as red crosses on the same axis.
if wheelies.any():
    ax.plot(iters[wheelies], powers[wheelies], "x", ms=4.5,
            color="#d62728", label="Wheelie (rejected)")
ax.set(xlabel="Objective evaluation", ylabel="Peak electrical power (kW)")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)
ax.set_ylim(55, 90)

fig.tight_layout()
fig.savefig(FIG / "optim_convergence.pdf", bbox_inches="tight")
plt.close(fig)


# ----------------------------------------------------------------------
# 4. Energy / power budget at terminal and at mid-run
# ----------------------------------------------------------------------
print("\n--- 4. Power budget snapshots ---")
v_term = v[-1]
P_drag_term = 0.5 * 1.225 * 0.8 * v_term**2 * v_term
P_rr_term   = 0.01 * m_v * 9.81 * v_term
P_drive_term = P_max * eta_drv
print(f"  v_terminal = {v_term:.2f} m/s")
print(f"  P_drag     = {P_drag_term/1e3:.2f} kW")
print(f"  P_rolling  = {P_rr_term/1e3:.2f} kW")
print(f"  P_drive    = {P_drive_term/1e3:.2f} kW")

# ----------------------------------------------------------------------
# 5. Pacejka coefficients snapshot
# ----------------------------------------------------------------------
pac = dict(
    C=cfg.tires.pacejka_C,
    pDx1=cfg.tires.pacejka_pDx1,
    pDx2=cfg.tires.pacejka_pDx2,
    pKx1=cfg.tires.pacejka_pKx1,
    pKx2=cfg.tires.pacejka_pKx2,
    E=cfg.tires.pacejka_E,
    Fz0=cfg.tires.pacejka_Fz0,
)
print("\n--- 5. Pacejka coefficients ---")
for k, v2 in pac.items():
    print(f"  {k:6} = {v2}")

# ----------------------------------------------------------------------
# Dump
# ----------------------------------------------------------------------
out = dict(
    time_decomp=dict(
        t_sim=t_sim, t_cp=t_cp, gap_s=gap,
        dt_drag_ms=dt_drag*1000,
        dt_rr_ms=dt_rr*1000,
        dt_drv_ms=dt_drv*1000,
        dt_traction_ms=dt_traction*1000,
        dt_residual_ms=dt_residual*1000,
    ),
    energy_budget_kJ=dict(
        E_elec=E_elec/1e3,
        KE_final=KE_final/1e3,
        E_drag=E_drag/1e3,
        E_rr=E_rr/1e3,
        E_drv_loss=E_drv_loss/1e3,
        E_mech=E_mech/1e3,
    ),
    power_budget_kW=dict(
        v_term=v_term,
        P_drag=P_drag_term/1e3,
        P_rr=P_rr_term/1e3,
        P_drive=P_drive_term/1e3,
    ),
    monte_carlo=dict(
        N=int(N_MC),
        mean=mc_mean, std=mc_std, p05=mc_p05, p95=mc_p95,
        n_power_ok=int(sum(mc_power_ok)),
        n_time_ok=int(sum(mc_time_ok)),
        n_no_wheelie=int(sum(1 for w in mc_wheelie if not w)),
    ),
    optimiser=dict(
        n_evals=int(len(trace)),
        final_time=float(result.fun),
        best_feasible_time=float(
            min((tr["time"] for tr in trace if not tr["wheelie"]
                 and tr["peak_power"] <= P_max * 1.0001),
                default=result.fun)),
    ),
    pacejka=pac,
)
(HERE / "extras.json").write_text(json.dumps(out, indent=2, default=float))
print(f"\nWrote {HERE / 'extras.json'}")
print(f"Wrote figures/mc_histogram.pdf, optim_convergence.pdf")
