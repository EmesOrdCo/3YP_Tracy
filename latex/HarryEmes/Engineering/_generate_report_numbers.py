"""Generate every numerical result needed for the report chapter.

This script exists only to fill placeholders in ``main.tex`` with real values
from the current simulation. It writes a JSON summary to ``report_numbers.json``
in the same directory and produces any figures that main.tex references.

Run from the repository root:
    python3 latex/HarryEmes/Engineering/_generate_report_numbers.py
"""

from __future__ import annotations

import json
import math
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.lines as mlines
import matplotlib.pyplot as plt

# Project root so imports work when run from anywhere.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver
from simulation.acceleration_sim import AccelerationSimulation

HERE = Path(__file__).resolve().parent
FIG_DIR = HERE / "figures"
FIG_DIR.mkdir(exist_ok=True)
# Beamer’s first \graphicspath entry is Presentation/figures, so a stale
# `final_run_combined.pdf` there overrides a fresh Engineering/figures/ copy
# (same filename). The generator must write the slide version explicitly.
PRESENTATION_FIGS = HERE.parent / "Presentation" / "figures"
SLIDE_BG = "#E8E8E8"  # match beamer `slidebg` in `Presentation/main.tex`

BASE_CONFIG_PATH = REPO_ROOT / "config" / "vehicle_configs" / "base_vehicle.json"


def run(config) -> dict:
    """Run one simulation and return a compact trace + headline metrics."""
    solver = DynamicsSolver(config)
    final = solver.solve()
    hist = solver.state_history

    t = np.array([s.time for s in hist])
    x = np.array([s.position for s in hist])
    v = np.array([s.velocity for s in hist])
    a = np.array([s.acceleration for s in hist])
    p = np.array([s.power_consumed for s in hist])
    fz_f = np.array([s.normal_force_front for s in hist])
    fz_r = np.array([s.normal_force_rear for s in hist])
    slip = np.array([getattr(s, "slip_ratio_rear", 0.0) for s in hist])
    fx = np.array([s.tire_force_rear for s in hist])

    return dict(
        t=t, x=x, v=v, a=a, p=p, fz_f=fz_f, fz_r=fz_r, slip=slip, fx=fx,
        final_time=float(final.time),
        final_velocity=float(final.velocity),
        peak_power=float(np.max(p)),
        min_fz_front=float(np.min(fz_f)),
    )


# --------------------------------------------------------------------------
# 1. Baseline run and V&V hand-calc comparison
# --------------------------------------------------------------------------
print("--- 1. Baseline simulation ---")
config_base = load_config(BASE_CONFIG_PATH)
base = run(config_base)
print(f"  time  = {base['final_time']:.4f} s")
print(f"  v_f   = {base['final_velocity']:.2f} m/s = {base['final_velocity']*3.6:.1f} km/h")
print(f"  P_max = {base['peak_power']/1e3:.2f} kW")
print(f"  min Fz_front = {base['min_fz_front']:.1f} N")

# Traction -> power: first time electrical power hits the FS accumulator cap
# (not 95% of the trace peak: on a linear ramp, 0.95*P_peak is ~0.95*t_to_cap,
# and mis-aligns t* with the 80 kW kink in the power curve).
P_cap = float(config_base.powertrain.max_power_accumulator_outlet)
idx_at_cap = np.where(base["p"] >= 0.999 * P_cap)[0]
if len(idx_at_cap):
    t_transition = float(base["t"][idx_at_cap[0]])
else:
    p_thresh = 0.95 * base["peak_power"]
    idx_trans = int(np.argmax(base["p"] >= p_thresh))
    t_transition = float(base["t"][idx_trans]) if idx_trans > 0 else 0.0
print(f"  t_transition (P >= 80 kW cap) = {t_transition:.3f} s")

# Time split between regimes.
t_traction = t_transition
t_power = base["final_time"] - t_transition
print(f"  traction phase = {t_traction:.3f} s, power phase = {t_power:.3f} s")

# Grip utilisation during traction phase: tyre force / (mu_peak * Fz_rear).
# Use a representative post-launch window (0.05-0.2 s) to avoid the torque ramp.
mask_launch = (base["t"] >= 0.05) & (base["t"] <= min(0.20, t_transition))
if mask_launch.any():
    util = (base["fx"][mask_launch] / np.maximum(1.0, base["fz_r"][mask_launch] * 1.45)).mean()
else:
    util = float("nan")
print(f"  mean grip utilisation in early launch = {util*100:.1f}%")

# --------------------------------------------------------------------------
# 2. Analytical constant-power lower bound
# --------------------------------------------------------------------------
print("\n--- 2. Analytical lower bound (constant power, no resistance) ---")
m = config_base.mass.total_mass
P = config_base.powertrain.max_power_accumulator_outlet
d = 75.0  # FS-D 5 track length
# x = (1/2 m v^2) / P * v   =>  solve: d = sqrt(8 m d^3 / (9 P))? No.
# Constant P starting from rest: v(t) = sqrt(2 P t / m); x(t) = (2/3) sqrt(2 P / m) t^{3/2}.
# Solve for t at x = d: t = ( d / ((2/3) * sqrt(2P/m)) )^{2/3}.
t_cp = (d / ((2.0 / 3.0) * math.sqrt(2.0 * P / m))) ** (2.0 / 3.0)
print(f"  Analytical t = {t_cp:.3f} s  (lower bound: assumes infinite grip, no losses)")
print(f"  Simulation gap to bound = {base['final_time'] - t_cp:.3f} s "
      f"({(base['final_time']/t_cp - 1)*100:.1f}%)")

# --------------------------------------------------------------------------
# 3. Hand-calculation V&V
# --------------------------------------------------------------------------
print("\n--- 3. Hand-calc V&V ---")
# Test 1: steady-state cruise at 20 m/s — rolling resistance.
# Analytically: Frr = crr * m*g (both axles, summed). Paul used 0.015, we use 0.01.
g = 9.81
crr = config_base.tires.rolling_resistance_coeff
frr_hand = crr * m * g
p_hand = frr_hand * 20.0
print(f"  Hand:  Frr @ v=20 m/s = {frr_hand:.1f} N,  P = {p_hand:.1f} W")

# Test 2: launch acceleration from pure torque balance at first step.
# Initial motor max torque capped by launch_torque_limit = 1000 Nm (per config).
Ng = config_base.powertrain.gear_ratio
eta = config_base.powertrain.drivetrain_efficiency
rw = config_base.tires.radius_loaded
launch_torque = config_base.control.launch_torque_limit
# Actually launch_torque_limit is *wheel* torque per the code comments; use directly.
F_drive_initial = launch_torque / rw
I_w = config_base.powertrain.wheel_inertia
m_eff = m + 4.0 * I_w / rw**2
a_hand = F_drive_initial / m_eff
# But the sim's initial torque ramps over 80 ms, so compare at t ~ 0.10 s:
idx_100ms = int(np.argmax(base["t"] >= 0.10))
a_sim_100ms = float(base["a"][idx_100ms])
print(f"  Hand:  a at unconstrained launch = {a_hand:.2f} m/s^2")
print(f"  Sim:   a at t=0.10 s         = {a_sim_100ms:.2f} m/s^2")

# Test 3: wheelie-onset acceleration from pitch moment balance.
cg_x = config_base.mass.cg_x
cg_z = config_base.mass.cg_z
L = config_base.mass.wheelbase
fz_f_static = m * g * (L - cg_x) / L
a_wheelie = fz_f_static * L / (m * cg_z)
print(f"  Hand:  a_wheelie = {a_wheelie:.2f} m/s^2")
print(f"  Sim:   peak a    = {float(np.max(base['a'])):.2f} m/s^2")

# --------------------------------------------------------------------------
# 4. Effective mass correction
# --------------------------------------------------------------------------
m_rot = 4.0 * I_w / rw**2
print(f"\n--- 4. Effective mass ---")
print(f"  m_v = {m:.1f} kg, 4 I_w / r_w^2 = {m_rot:.2f} kg, "
      f"effective-mass penalty = {m_rot/m*100:.2f}%")

# --------------------------------------------------------------------------
# 5. Transition speed of the power limit
# --------------------------------------------------------------------------
Kt = config_base.powertrain.motor_torque_constant
Imax = config_base.powertrain.motor_max_current
Vbus = config_base.powertrain.battery_voltage_nominal
T_m_peak = Kt * Imax
omega_star = P / T_m_peak  # rad/s motor shaft
v_star = omega_star * rw / Ng
print(f"\n--- 5. Power-limit transition speed ---")
print(f"  T_m_peak = {T_m_peak:.1f} N.m")
print(f"  omega* (motor) = {omega_star:.1f} rad/s = {omega_star*60/(2*math.pi):.0f} rpm")
print(f"  v*  (vehicle)  = {v_star:.2f} m/s = {v_star*3.6:.1f} km/h")

# --------------------------------------------------------------------------
# 6. Timestep convergence study
# --------------------------------------------------------------------------
print("\n--- 6. Timestep convergence ---")
conv = {}
for dt in (0.005, 0.002, 0.001, 0.0005, 0.0002):
    cfg = deepcopy(config_base)
    cfg.dt = dt
    r = run(cfg)
    conv[dt] = r["final_time"]
    print(f"  dt = {dt*1000:.2f} ms -> t = {r['final_time']:.5f} s")

# --------------------------------------------------------------------------
# 7. Dry vs wet
# --------------------------------------------------------------------------
print("\n--- 7. Dry vs wet (surface_mu_scaling 1.0 vs 0.6) ---")
cfg_wet = deepcopy(config_base)
cfg_wet.environment.surface_mu_scaling = 0.6
wet = run(cfg_wet)
print(f"  Dry = {base['final_time']:.3f} s,  Wet = {wet['final_time']:.3f} s,  "
      f"delta = {wet['final_time'] - base['final_time']:+.3f} s "
      f"({(wet['final_time']/base['final_time'] - 1)*100:.1f}%)")

# --------------------------------------------------------------------------
# 8. Parameter sensitivity (one-at-a-time ±10%)
# --------------------------------------------------------------------------
print("\n--- 8. Sensitivity tornado (±10% one-at-a-time) ---")
sens_params = [
    ("tires.pacejka_pDx1",          "Peak grip $p_{Dx1}$"),
    ("mass.total_mass",             "Mass $m_v$"),
    ("powertrain.gear_ratio",       "Gear ratio $N_g$"),
    ("mass.cg_z",                   "CG height $h_{CG}$"),
    ("mass.cg_x",                   "CG long. $L_{CG}$"),
    ("tires.radius_loaded",         "Wheel radius $r_w$"),
    ("powertrain.drivetrain_efficiency", "Driveline $\\eta_\\text{drv}$"),
    ("aerodynamics.cda",            "Drag area $C_d A$"),
    ("tires.rolling_resistance_coeff", "Rolling $C_\\text{rr}$"),
    ("suspension.anti_squat_ratio", "Anti-squat AS"),
]

def _get(cfg, path):
    node = cfg
    for p in path.split("."):
        node = getattr(node, p)
    return node

def _set(cfg, path, val):
    node = cfg
    parts = path.split(".")
    for p in parts[:-1]:
        node = getattr(node, p)
    setattr(node, parts[-1], val)

sens_results = []
for path, label in sens_params:
    base_val = _get(config_base, path)
    if base_val == 0.0:
        print(f"  Skipping {path} (baseline 0)")
        continue
    results = {}
    for sign, delta in (("low", -0.10), ("high", +0.10)):
        cfg = deepcopy(config_base)
        _set(cfg, path, base_val * (1.0 + delta))
        try:
            r = run(cfg)
            results[sign] = r["final_time"]
        except Exception as e:
            results[sign] = float("nan")
            print(f"  {path} {sign}: failed ({e})")
    dt_low = results.get("low", float("nan")) - base["final_time"]
    dt_high = results.get("high", float("nan")) - base["final_time"]
    # Signed influence: the greater absolute delta.
    signed = dt_high if abs(dt_high) >= abs(dt_low) else dt_low
    sens_results.append(dict(path=path, label=label, baseline=base_val,
                             dt_low=dt_low, dt_high=dt_high,
                             abs_max=max(abs(dt_low), abs(dt_high))))
    print(f"  {label:22} base={base_val:10.4g}  -10%:{dt_low*1000:+7.1f} ms  "
          f"+10%:{dt_high*1000:+7.1f} ms")

sens_results.sort(key=lambda r: r["abs_max"], reverse=True)

# --------------------------------------------------------------------------
# 9. Plots
# --------------------------------------------------------------------------
print("\n--- 9. Generating figures ---")

# Final-run multi-panel.
fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.8),
                         gridspec_kw=dict(hspace=0.45, wspace=0.32))
t, x, v, a, p = base["t"], base["x"], base["v"], base["a"], base["p"]

ax = axes[0, 0]
ax.plot(t, v, "C0", lw=1.8)
ax.axvline(t_transition, color="grey", ls="--", lw=0.8, label=f"$t^\\star$={t_transition:.2f} s")
ax.set(xlabel="Time (s)", ylabel="Velocity (m/s)", title="Velocity vs time")
ax.legend(loc="lower right"); ax.grid(alpha=0.3)

ax = axes[0, 1]
ax.plot(t, a, "C1", lw=1.2)
ax.axvline(t_transition, color="grey", ls="--", lw=0.8)
ax.set(xlabel="Time (s)", ylabel="Acceleration (m/s$^2$)", title="Acceleration vs time")
ax.grid(alpha=0.3)

ax = axes[1, 0]
ax.plot(t, p / 1e3, "C2", lw=1.4)
ax.axhline(80.0, color="r", ls="--", lw=1.0, label="FS-EV 2.2 (80 kW)")
ax.set(xlabel="Time (s)", ylabel="Electrical power (kW)", title="Power vs time")
ax.legend(loc="lower right", framealpha=0.92); ax.grid(alpha=0.3)
ax.set_ylim(0, 95)

ax = axes[1, 1]
ax.plot(t, x, "C3", lw=1.8)
ax.axhline(75.0, color="grey", ls="--", lw=1.0,
           label=f"75 m at $t={base['final_time']:.2f}$ s")
ax.set(xlabel="Time (s)", ylabel="Distance (m)", title="Distance vs time")
ax.legend(loc="lower right", framealpha=0.92); ax.grid(alpha=0.3)
ax.set_ylim(0, 80)

fig.suptitle(f"Predicted performance of the baseline vehicle "
             f"({base['final_time']:.2f} s, {base['final_velocity']*3.6:.0f} km/h)")
fig.savefig(FIG_DIR / "final_run.pdf", bbox_inches="tight")
plt.close(fig)

# Shared time axis: acceleration (left) and electrical power (right) only.
p_kw = np.minimum(p, P_cap) / 1e3
a_ylim = float((np.ceil((a.max() + 0.4) * 1.0) * 1.0) if a.max() > 0 else 5.0)
a_ylim = max(5.0, min(25.0, a_ylim))
P_ylim = 95.0
c1, c2 = "C1", "C2"
fig_c = plt.figure(figsize=(10.5, 4.2))
# Leave extra room on the right for the power-axis ticks and “Power (kW)” label.
# Larger `bottom` lifts the axes + “Time (s)” so there is clear space above the fig.legend.
fig_c.subplots_adjust(left=0.1, right=0.82, top=0.9, bottom=0.30)

ax0 = fig_c.add_subplot(111)
(l1,) = ax0.plot(t, a, c1, lw=1.5, zorder=3, alpha=0.95)
ax0.set_xlim(0.0, max(float(t.max()), 0.2))
ax0.set_ylim(0, a_ylim)
ax0.set_ylabel("Acceleration (m/s$^2$)", color=c1, fontweight="medium", labelpad=3)
ax0.set_xlabel("Time (s)")
ax0.set_title("Run overview: acceleration and power")
ax0.tick_params(axis="y", labelcolor=c1, labelsize=9, length=4)
ax0.grid(True, alpha=0.28, which="both", zorder=0)
ax0.axvline(t_transition, color="0.45", ls="--", lw=1, zorder=1, alpha=0.9)
ax0.set_axisbelow(True)

axp = ax0.twinx()
(l2,) = axp.plot(t, p_kw, c2, lw=1.7, zorder=2)
axp.set_ylim(0, P_ylim)
axp.set_ylabel("Power (kW)", color=c2, fontweight="medium", labelpad=8)
axp.tick_params(axis="y", labelcolor=c2, labelsize=9, length=4)
axp.axhline(80.0, color="0.55", ls=":", lw=0.95, alpha=0.5, zorder=1)  # FS-EV 2.2

h_star = mlines.Line2D([0], [0], color="0.45", ls="--", lw=1)
_legc = fig_c.legend(
    [l1, l2, h_star],
    [
        f"Acceleration (peak {a.max():.1f} m/s$^2$)",
        f"Power (capped {P_cap/1e3:.0f} kW; dotted: FS cap)",
        rf"$t^*$ = {t_transition:.2f} s (traction $\to$ power)",
    ],
    loc="lower center",
    bbox_to_anchor=(0.5, 0.02),
    ncol=3,
    frameon=True,
    framealpha=0.95,
    fontsize=7.2,
    columnspacing=0.6,
    handlelength=1.3,
    borderaxespad=0.0,
    fancybox=False,
)
_save_combined = dict(
    bbox_inches="tight", pad_inches=0.5, facecolor="white", edgecolor="white",
    dpi=150,
)
fig_c.savefig(FIG_DIR / "final_run_combined.pdf", **_save_combined)

# Slides: same geometry; deck’s first `figures/` must match. Match `slidebg`.
PRESENTATION_FIGS.mkdir(exist_ok=True, parents=True)
fig_c.patch.set_facecolor(SLIDE_BG)
for _ax in fig_c.get_axes():
    _ax.set_facecolor(SLIDE_BG)
if _legc is not None and _legc.get_frame() is not None:
    f = _legc.get_frame()
    f.set_facecolor(SLIDE_BG)
    f.set_edgecolor("0.6")
fig_c.savefig(
    PRESENTATION_FIGS / "final_run_combined.pdf",
    bbox_inches="tight", pad_inches=0.5, facecolor=SLIDE_BG, edgecolor=SLIDE_BG, dpi=150,
)
plt.close(fig_c)

# Tornado plot.
fig, ax = plt.subplots(figsize=(8.2, 4.6))
n = len(sens_results)
labels = [r["label"] for r in sens_results]
lows = np.array([r["dt_low"] for r in sens_results]) * 1000.0
highs = np.array([r["dt_high"] for r in sens_results]) * 1000.0
y = np.arange(n)
ax.barh(y, highs, color="C0", alpha=0.75, label="+10%")
ax.barh(y, lows, color="C3", alpha=0.75, label="-10%")
ax.set(yticks=y, yticklabels=labels)
ax.set_title("Sensitivity of 75 m time to $\\pm 10\\%$ parameter perturbations", fontsize=13)
ax.set_xlabel("Change in 75 m time vs baseline (ms)", fontsize=13)
ax.invert_yaxis()
ax.tick_params(axis="y", labelsize=12)
ax.tick_params(axis="x", labelsize=12)
ax.legend(loc="lower right", fontsize=10, framealpha=0.95)
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(FIG_DIR / "tornado.pdf", bbox_inches="tight")
plt.close(fig)

# Dry vs wet.
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.plot(base["t"], base["v"], "C0", lw=1.8, label=f"Dry ($\\mu_s$=1.0), t={base['final_time']:.2f} s")
ax.plot(wet["t"], wet["v"], "C3", lw=1.8, ls="--", label=f"Wet ($\\mu_s$=0.6), t={wet['final_time']:.2f} s")
ax.set(xlabel="Time (s)", ylabel="Velocity (m/s)",
       title="Robustness to track conditions")
ax.legend(loc="lower right"); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(FIG_DIR / "dry_wet.pdf", bbox_inches="tight")
plt.close(fig)

# dt convergence plot.
fig, ax = plt.subplots(figsize=(6.5, 3.6))
dts = sorted(conv.keys(), reverse=True)
times = [conv[d] for d in dts]
ax.semilogx([d * 1000 for d in dts], times, "o-", lw=1.4)
ax.set(xlabel="Timestep $\\Delta t$ (ms)", ylabel="Predicted 75 m time (s)",
       title="Convergence of the 75 m time with timestep")
ax.grid(alpha=0.3, which="both")
fig.tight_layout()
fig.savefig(FIG_DIR / "dt_convergence.pdf", bbox_inches="tight")
plt.close(fig)

# --------------------------------------------------------------------------
# 10. Dump numbers to JSON for traceability
# --------------------------------------------------------------------------
out = dict(
    baseline=dict(
        final_time=base["final_time"],
        final_velocity=base["final_velocity"],
        peak_power_kW=base["peak_power"] / 1e3,
        min_fz_front=base["min_fz_front"],
        t_transition=t_transition,
        t_traction=t_traction,
        t_power=t_power,
        early_launch_grip_util=util,
    ),
    params=dict(
        m_v=m, cg_x=cg_x, cg_z=cg_z, L=L,
        r_w=rw, mu_max=config_base.tires.mu_max,
        Ng=Ng, eta_drv=eta, Kt=Kt, Imax=Imax, Vbus=Vbus,
        CdA=config_base.aerodynamics.cda,
        AS=config_base.suspension.anti_squat_ratio,
        crr=crr,
        m_rot=m_rot,
        m_eff=m + m_rot,
    ),
    analytical_bound=dict(
        t_cp=t_cp,
        gap_s=base["final_time"] - t_cp,
        gap_pct=(base["final_time"] / t_cp - 1) * 100,
    ),
    hand_calc=dict(
        frr_hand=frr_hand, p_hand=p_hand,
        a_hand_launch=a_hand,
        a_sim_100ms=a_sim_100ms,
        a_peak=float(np.max(base["a"])),
        a_wheelie=a_wheelie,
    ),
    power_transition=dict(
        T_m_peak=T_m_peak, omega_star=omega_star, v_star=v_star,
    ),
    convergence={f"{k*1000:.2f}ms": v for k, v in conv.items()},
    dry_wet=dict(
        dry=base["final_time"], wet=wet["final_time"],
        delta=wet["final_time"] - base["final_time"],
    ),
    sensitivity=[
        dict(
            label=r["label"],
            path=r["path"],
            baseline=r["baseline"],
            dt_low_ms=r["dt_low"] * 1000,
            dt_high_ms=r["dt_high"] * 1000,
        )
        for r in sens_results
    ],
)
(HERE / "report_numbers.json").write_text(json.dumps(out, indent=2, default=float))
print(f"\nWrote {HERE / 'report_numbers.json'}")
print(f"Wrote figures to {FIG_DIR}/")
