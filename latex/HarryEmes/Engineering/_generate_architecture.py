"""Generate the software architecture diagram used in Section 2.8.

Shows the five-layer Python architecture of the simulation with the
Streamlit GUI on top. Saves a vector PDF that main.tex includes as
fig:architecture.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

# Layer colours (matching the figure 2.1 palette).
CLR = {
    "gui":     "#f6ecff",
    "cfg":     "#eaf6ea",
    "vehicle": "#eef2fb",
    "dyn":     "#fff0e6",
    "rules":   "#fde8ea",
    "results": "#f0f0f0",
}
EDGE = "0.30"

fig, ax = plt.subplots(figsize=(10.0, 6.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10.2)
ax.set_aspect("equal")
ax.axis("off")


def layer(y, h, label, sub_label, boxes, fill):
    """Draw a layer band with a name on the left and child boxes inside."""
    ax.add_patch(FancyBboxPatch(
        (0.2, y), 9.6, h,
        boxstyle="round,pad=0.02",
        linewidth=1.1, edgecolor=EDGE, facecolor=fill, zorder=1,
    ))
    # Layer name on the left.
    ax.text(0.55, y + h / 2, label, fontsize=11.5, weight="bold",
            color="0.15", rotation=90, va="center", ha="center", zorder=3)
    ax.text(0.90, y + h / 2, sub_label, fontsize=8, color="0.35",
            rotation=90, va="center", ha="center", zorder=3)

    # Child boxes inside the layer.
    n = len(boxes)
    x_start = 1.3
    x_end = 9.6
    slot = (x_end - x_start) / n
    for i, txt in enumerate(boxes):
        cx = x_start + slot * (i + 0.5)
        w = slot * 0.88
        box_h = h * 0.72
        box_y = y + (h - box_h) / 2
        box_x = cx - w / 2
        ax.add_patch(FancyBboxPatch(
            (box_x, box_y), w, box_h,
            boxstyle="round,pad=0.02",
            linewidth=0.8, edgecolor="0.25", facecolor="white", zorder=2,
        ))
        ax.text(cx, box_y + box_h / 2, txt,
                fontsize=8.6, ha="center", va="center", zorder=3)


# --- Layers (top to bottom) -------------------------------------------
layer(8.55, 1.15, "GUI", "Streamlit",
      ["Single run", "Parameter sweep", "Optimiser",
       "Gearing", "Sensitivity", "Monte Carlo",
       "Track conditions", "Energy storage"],
      CLR["gui"])

layer(7.20, 1.15, "Config", "JSON / YAML",
      ["base_vehicle.json", "VehicleConfig dataclass",
       "Validation & bounds"],
      CLR["cfg"])

layer(5.00, 2.00, "Vehicle Models", "vehicle/",
      ["Mass\nProperties",
       "Tyre Model\n(Pacejka\n+ thermal)",
       "Powertrain\n+ 80 kW\ncap",
       "Aerodynamics",
       "Suspension\n+ anti-squat",
       "Launch\n+ traction\ncontrol"],
      CLR["vehicle"])

layer(3.20, 1.60, "Dynamics", "dynamics/",
      ["State vector\n$(x, v, \\omega_{w,f/r})$",
       "Force\naggregator",
       "RK4\nintegrator\n($\\Delta t =$ 1 ms)",
       "Wheelie &\nslip governor"],
      CLR["dyn"])

layer(1.70, 1.30, "Rules", "rules/",
      ["Power limit\nEV 2.2",
       "Time limit\nD 5.3.1",
       "Wheelie\ncheck",
       "Score\nD 5.3.2"],
      CLR["rules"])

layer(0.20, 1.30, "Results", "analysis/",
      ["SimulationResult",
       "State history",
       "Plots\n(matplotlib)",
       "Validation\n& V\\&V"],
      CLR["results"])


# --- Arrows between layers --------------------------------------------
def arrow(x, y_top, y_bot, text=None):
    ax.add_patch(FancyArrowPatch(
        (x, y_top), (x, y_bot), arrowstyle="-|>",
        mutation_scale=15, color="0.25", lw=1.3, zorder=4,
    ))
    if text:
        ax.text(x + 0.12, (y_top + y_bot) / 2, text,
                fontsize=7.8, color="0.3", va="center", zorder=4)


arrow(2.2, 8.55, 8.35, "parameter proposals")
arrow(2.2, 7.20, 7.00, "load")
arrow(2.2, 5.00, 4.80, "invoke")
arrow(2.2, 3.20, 3.00, "aggregate")
arrow(2.2, 1.70, 1.50, "results +\ncompliance")

arrow(7.8, 8.35, 8.55, "live PDF /\nplots")
arrow(7.8, 7.00, 7.20, "")
arrow(7.8, 4.80, 5.00, "")
arrow(7.8, 3.00, 3.20, "")
arrow(7.8, 1.50, 1.70, "")

# --- Title ------------------------------------------------------------
ax.text(5.0, 9.95, "Acceleration Simulation — Software Architecture",
        ha="center", fontsize=12, weight="bold")

# --- Tests / sidebar annotation ---------------------------------------
ax.text(9.7, 0.35,
        "9 unit-test modules\n(tires, powertrain, dynamics,\nscoring, Monte Carlo,\n"
        "sensitivity, thermal,\ncontroller, integration)",
        ha="right", va="bottom", fontsize=7.5, color="0.2",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor="0.5", linewidth=0.7))

fig.tight_layout(pad=0.1)
out = FIG / "architecture.pdf"
fig.savefig(out, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {out}")
