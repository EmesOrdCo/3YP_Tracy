#!/usr/bin/env python3
"""Regenerate figures/optim_convergence.pdf only (single time panel)."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
BASE_CFG = REPO / "config" / "vehicle_configs" / "base_vehicle.json"


def run_sim(cfg) -> Dict:
    solver = DynamicsSolver(cfg)
    final = solver.solve()
    hist = solver.state_history
    t = np.array([s.time for s in hist])
    return dict(
        final_time=float(final.time),
        peak_power=float(max(s.power_consumed for s in hist)),
        wheelie=any(s.normal_force_front <= 0 for s in hist),
        t=t,
        v=np.array([s.velocity for s in hist]),
        p=np.array([s.power_consumed for s in hist]),
    )


def unpack(x, base_cfg):
    c = copy.deepcopy(base_cfg)
    c.mass.wheelbase = float(x[0])
    c.mass.cg_x = float(x[1]) * c.mass.wheelbase
    c.powertrain.gear_ratio = float(x[2])
    c.tires.radius_loaded = float(x[3])
    c.tires.mu_slip_optimal = float(x[4])
    c.control.launch_torque_limit = float(x[5])
    c.suspension.anti_squat_ratio = float(x[6])
    return c


def main() -> None:
    cfg = load_config(BASE_CFG)
    P_max = cfg.powertrain.max_power_accumulator_outlet

    x0 = np.array([1.60, 0.712, 5.5, 0.247, 0.14, 1000.0, 0.12])
    bounds_low = np.array([1.525, 0.50, 3.0, 0.20, 0.08, 400.0, 0.00])
    bounds_high = np.array([1.750, 0.88, 7.0, 0.28, 0.20, 1200.0, 1.00])
    trace: list = []

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
            trace.append(
                dict(
                    val=val,
                    time=r["final_time"],
                    wheelie=r["wheelie"],
                    peak_power=r["peak_power"],
                )
            )
            return val
        except Exception:
            trace.append(dict(val=10.0, time=10.0, wheelie=True, peak_power=0))
            return 10.0

    print("Nelder–Mead (max 271 evals) for optim_convergence.pdf …")
    minimize(
        objective,
        x0,
        method="Nelder-Mead",
        options=dict(maxiter=271, maxfev=271, xatol=1e-4, fatol=1e-4, disp=False),
    )
    print(f"  {len(trace)} evaluations recorded")

    iters = np.arange(1, len(trace) + 1)
    best_so_far = np.minimum.accumulate(np.array([tr["val"] for tr in trace]))
    times = np.array([tr["time"] for tr in trace])
    wheelies = np.array([tr["wheelie"] for tr in trace])

    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    ax.plot(iters, times, ".", ms=2.5, color="0.6", label="Eval $t_{75}$")
    ax.plot(
        iters,
        best_so_far,
        "-",
        color="#1f77b4",
        lw=1.6,
        label="Best feasible so far (incl. penalty)",
    )
    if wheelies.any():
        ax.plot(
            iters[wheelies],
            times[wheelies],
            "x",
            ms=4.5,
            color="#d62728",
            label="Wheelie (penalised)",
        )
    ax.set(
        xlabel="Objective evaluation",
        ylabel="Predicted 75 m time (s)",
        title="Nelder–Mead convergence of the acceleration optimiser",
    )
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    ax.set_ylim(3.3, 5.0)
    fig.tight_layout()
    FIG.mkdir(exist_ok=True)
    out = FIG / "optim_convergence.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
