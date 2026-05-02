"""Single-panel 'simple vs Pacejka' tyre-model comparison for slide 1.

Renders longitudinal force vs slip ratio at nominal load (Fz = 1500 N)
for both the piecewise-linear simple model and the load-sensitive Pacejka
model, with the slide grey baked into the canvas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SLIDE_BG = "#E8E8E8"
INK      = "#1A1A1A"
MUTED    = "#5C5C5C"
BLUE     = "#1F4E79"
RED      = "#C0392B"

import matplotlib as _mpl
_mpl.rcParams.update({
    "font.size":        22,
    "axes.titlesize":   24,
    "axes.labelsize":   22,
    "xtick.labelsize":  18,
    "ytick.labelsize":  18,
    "legend.fontsize":  18,
})

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT))

from config.vehicle_config import TireProperties
from vehicle.tire_model import TireModel

OUT = HERE / "figures"
OUT.mkdir(exist_ok=True)


def main():
    cfg = TireProperties(
        radius_loaded=0.2286,
        mass=3.0,
        mu_max=1.5,
        mu_slip_optimal=0.12,
        rolling_resistance_coeff=0.015,
        tire_model_type="pacejka",
    )
    simple  = TireModel(cfg, use_pacejka=False)
    pacejka = TireModel(cfg, use_pacejka=True)

    slip = np.linspace(0, 0.40, 250)
    Fz_nom = 1500.0
    fx_simple  = np.array([simple .calculate_longitudinal_force(Fz_nom, k, 10.0)[0] for k in slip])
    fx_pacejka = np.array([pacejka.calculate_longitudinal_force(Fz_nom, k, 10.0)[0] for k in slip])

    # Load-sensitivity: peak grip across loads
    loads = np.linspace(500, 4000, 60)
    mu_simple  = np.full_like(loads, cfg.mu_max)
    mu_pac = np.array([
        max(pacejka.calculate_longitudinal_force(Fz, k, 10.0)[0] for k in slip) / Fz
        for Fz in loads
    ])

    # ---- Layout: two stacked panels, share x where useful -----------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5.5, 8.0))
    fig.patch.set_facecolor(SLIDE_BG)
    for ax in (ax1, ax2):
        ax.set_facecolor(SLIDE_BG)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color("0.4")
        ax.tick_params(colors=MUTED)
        ax.grid(alpha=0.25, color="0.5")

    # Panel 1: Force vs slip at Fz = 1500 N
    ax1.plot(slip * 100, fx_simple  / 1000, "--", color=BLUE, lw=3.0, label="Simple")
    ax1.plot(slip * 100, fx_pacejka / 1000,  "-", color=RED,  lw=3.0, label="Pacejka")
    ax1.set_xlabel("Slip ratio $\\kappa$ (%)", color=INK)
    ax1.set_ylabel("$F_x$ (kN)", color=INK)
    ax1.set_title(f"Force-slip at $F_z = {Fz_nom:.0f}$ N",
                  color=INK, fontweight="bold", loc="left")
    ax1.legend(loc="lower right", framealpha=0.0)
    ax1.set_xlim(0, 40)
    ax1.set_ylim(0, max(fx_pacejka.max(), fx_simple.max()) / 1000 * 1.05)

    # Panel 2: Peak grip vs vertical load
    ax2.plot(loads, mu_simple, "--", color=BLUE, lw=3.0, label="Simple")
    ax2.plot(loads, mu_pac,    "-",  color=RED,  lw=3.0, label="Pacejka")
    ax2.fill_between(loads, mu_simple, mu_pac, where=(mu_pac < mu_simple),
                     color=RED, alpha=0.12)
    ax2.axvspan(1500, 2500, color="0.25", alpha=0.07)
    ax2.set_xlabel("Vertical load $F_z$ (N)", color=INK)
    ax2.set_ylabel("Peak $\\mu$", color=INK)
    ax2.set_title("Load sensitivity: peak grip vs $F_z$",
                  color=INK, fontweight="bold", loc="left")
    ax2.legend(loc="lower left", framealpha=0.0)
    ax2.set_xlim(500, 4000)

    fig.tight_layout(pad=1.0)
    out_pdf = OUT / "pacejka_slide.pdf"
    fig.savefig(out_pdf, bbox_inches="tight", facecolor=SLIDE_BG, edgecolor=SLIDE_BG)
    plt.close(fig)
    print(f"Wrote {out_pdf}")


if __name__ == "__main__":
    main()
