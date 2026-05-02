"""Generate a comparison figure for the end-of-run power dip investigation.

Plots P_elec(t) and V_dc(t) for three configurations:
    - Baseline (200 cells, BAMOCAR-PG-D3-700/400 with 285 A_RMS peak)
    - +Cells (240 supercap cells; raises V_init to 720 V)
    - +Inverter (BAMOCAR upgraded to ≥400 A_RMS peak; modelled by setting
      motor_max_current = 400 A in config; supercap unchanged)

The point of the figure is to show that the only ways to flatten power
to the finish involve a hardware change. Used in the engineering report
to support the investigation writeup; not added to any presentation
slides (the slide layout is locked).

Output: latex/HarryEmes/Engineering/figures/power_dip_options.pdf and .png.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver

CONFIG_PATH = ROOT / "config" / "vehicle_configs" / "base_vehicle.json"
OUT_DIR = ROOT / "latex" / "HarryEmes" / "Engineering" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run(overrides: dict | None = None):
    cfg = load_config(CONFIG_PATH)
    if overrides:
        for path, value in overrides.items():
            obj = cfg
            parts = path.split(".")
            for p in parts[:-1]:
                obj = getattr(obj, p)
            setattr(obj, parts[-1], value)
    solver = DynamicsSolver(cfg)
    final = solver.solve()
    hist = solver.state_history
    t = np.array([s.time for s in hist])
    p = np.array([s.power_consumed for s in hist]) / 1e3
    vdc = np.array([s.dc_bus_voltage for s in hist])
    return t, p, vdc, final.time


cases = [
    ("Baseline (200 cells, 285 A_RMS)", {}, "tab:red"),
    ("+ 40 cells (240 cells, 285 A_RMS)", {
        "powertrain.supercap_num_cells": 240,
        "powertrain.battery_voltage_nominal": 720.0,
    }, "tab:blue"),
    ("+ Larger inverter (200 cells, 400 A_RMS)", {
        "powertrain.motor_max_current": 400.0,
    }, "tab:green"),
]

fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.0), sharex=True)
ax_p, ax_v = axes

for label, over, colour in cases:
    t, p, vdc, t_final = run(over)
    ax_p.plot(t, p, color=colour, lw=2.0, label=f"{label} ({t_final:.2f} s)")
    ax_v.plot(t, vdc, color=colour, lw=2.0)

ax_p.axhline(80.0, color="k", ls="--", lw=1.0, alpha=0.6,
             label="80 kW FS cap")
ax_p.set_ylabel("Electrical power (kW)")
ax_p.set_ylim(0, 90)
ax_p.legend(loc="lower right", fontsize=9)
ax_p.grid(alpha=0.3)

# Highlight V_dc threshold below which motor cannot deliver 80 kW elec
# (V_dc < 600.5 V with 285 A_RMS BAMOCAR). Shown as dotted line.
ax_v.axhline(600.5, color="k", ls=":", lw=1.0, alpha=0.6,
             label="V_dc for 80 kW (285 A inverter)")
ax_v.set_ylabel("DC bus voltage (V)")
ax_v.set_xlabel("Time (s)")
ax_v.grid(alpha=0.3)
ax_v.legend(loc="lower left", fontsize=9)

fig.suptitle("End-of-run power dip — three configurations", fontsize=12)
fig.tight_layout()

pdf_out = OUT_DIR / "power_dip_options.pdf"
png_out = OUT_DIR / "power_dip_options.png"
fig.savefig(pdf_out, bbox_inches="tight")
fig.savefig(png_out, dpi=160, bbox_inches="tight")
print(f"Wrote {pdf_out}")
print(f"Wrote {png_out}")
