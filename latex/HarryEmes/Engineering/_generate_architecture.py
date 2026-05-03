"""Generate the software architecture diagram used in Section 2.8.

Shows the five-layer Python architecture of the simulation with the
Streamlit GUI on top. Saves a vector PDF that main.tex includes as
fig:architecture.
"""

from __future__ import annotations

import textwrap
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


def fit_box_text(s: str, width_chars: int) -> str:
    """Wrap long lines so labels stay inside narrow layer slots."""
    out: list[str] = []
    for block in s.split("\n"):
        b = block.strip()
        if not b:
            out.append("")
            continue
        lines = textwrap.wrap(
            b,
            width=width_chars,
            break_long_words=False,
            break_on_hyphens=True,
        )
        out.append("\n".join(lines) if lines else "")
    return "\n".join(out)


def format_side_label(title: str) -> str:
    """Two-line split for long layer titles so rotated text stays in the gutter."""
    title = title.strip()
    if len(title) <= 12:
        return title
    parts = title.split()
    if len(parts) == 2:
        return f"{parts[0]}\n{parts[1]}"
    lines = textwrap.wrap(title, width=10)
    return "\n".join(lines) if lines else title


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
    # Layer name on the left (rotated); keep inside band — split long titles,
    # shrink font for tall stacks, anchor slightly right of band edge.
    label_disp = format_side_label(label)
    longest_line = max(len(line) for line in label_disp.split("\n"))
    fs_main = min(11.5, 10.2 + 0.35 * h, 110 / max(longest_line, 6))
    fs_sub = min(8.0, 7.2 + 0.12 * h, 72 / max(len(sub_label), 4))
    x_main, x_sub = 0.68, 0.98
    ax.text(x_main, y + h / 2, label_disp, fontsize=fs_main, weight="bold",
            color="0.15", rotation=90, va="center", ha="center", zorder=3,
            parse_math=False)
    ax.text(x_sub, y + h / 2, sub_label, fontsize=fs_sub, color="0.35",
            rotation=90, va="center", ha="center", zorder=3,
            parse_math=False)

    # Child boxes inside the layer.
    n = len(boxes)
    x_start = 1.38
    x_end = 9.6
    slot = (x_end - x_start) / n
    # Narrow slots → smaller type + tighter wrap width.
    wrap_w = max(9, min(16, int(110 / max(n, 1))))
    fs = max(6.4, min(8.2, 10.0 - 0.45 * n))
    box_h = h * min(0.82, 0.68 + 0.02 * max(0, 6 - n))
    for i, txt in enumerate(boxes):
        cx = x_start + slot * (i + 0.5)
        w = slot * 0.92
        box_y = y + (h - box_h) / 2
        box_x = cx - w / 2
        ax.add_patch(FancyBboxPatch(
            (box_x, box_y), w, box_h,
            boxstyle="round,pad=0.02",
            linewidth=0.8, edgecolor="0.25", facecolor="white", zorder=2,
        ))
        label_txt = fit_box_text(txt, wrap_w)
        ax.text(cx, box_y + box_h / 2, label_txt,
                fontsize=fs, ha="center", va="center", zorder=3,
                linespacing=0.95, parse_math=False)


# --- Layers (top to bottom) -------------------------------------------
layer(8.55, 1.15, "GUI", "Streamlit",
      ["Single run", "Param.\nsweep", "Optimiser",
       "Gearing", "Sensitivity", "Monte Carlo",
       "Track", "Energy\nstorage"],
      CLR["gui"])

layer(7.20, 1.15, "Config", "JSON / YAML",
      ["base_vehicle.json", "VehicleConfig dataclass",
       "Validation & bounds"],
      CLR["cfg"])

layer(5.00, 2.00, "Vehicle Models", "vehicle/",
      ["Mass\nproperties",
       "Tyre (Pacejka +\nthermal)",
       "Powertrain +\n80 kW cap",
       "Aero-\ndynamics",
       "Suspension +\nanti-squat",
       "Launch +\ntraction ctrl"],
      CLR["vehicle"])

layer(3.20, 1.60, "Dynamics", "dynamics/",
      ["State\n(x, v, \u03c9_w)",
       "Force\naggregator",
       "RK4\n(\u0394t = 1 ms)",
       "Wheelie /\nslip limit"],
      CLR["dyn"])

layer(1.70, 1.30, "Rules", "rules/",
      ["Power limit\nEV 2.2",
       "Time limit\nD 5.3.1",
       "Wheelie\ncheck",
       "Score\nD 5.3.2"],
      CLR["rules"])

layer(0.20, 1.30, "Results", "analysis/",
      ["Sim.\nresult",
       "State\nhistory",
       "Plots\n(pyplot)",
       "V&V\nvalidation"],
      CLR["results"])


# --- Arrows between layers (no mid-arrow labels — keeps diagram readable)
def arrow(x, y_top, y_bot):
    ax.add_patch(FancyArrowPatch(
        (x, y_top), (x, y_bot), arrowstyle="-|>",
        mutation_scale=15, color="0.25", lw=1.3, zorder=4,
    ))


arrow(2.2, 8.55, 8.35)
arrow(2.2, 7.20, 7.00)
arrow(2.2, 5.00, 4.80)
arrow(2.2, 3.20, 3.00)
arrow(2.2, 1.70, 1.50)

arrow(7.8, 8.35, 8.55)
arrow(7.8, 7.00, 7.20)
arrow(7.8, 4.80, 5.00)
arrow(7.8, 3.00, 3.20)
arrow(7.8, 1.50, 1.70)

# --- Title ------------------------------------------------------------
ax.text(5.0, 9.95, "Acceleration Simulation — Software Architecture",
        ha="center", fontsize=12, weight="bold", parse_math=False)

fig.tight_layout(pad=0.1)
out = FIG / "architecture.pdf"
fig.savefig(out, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {out}")
