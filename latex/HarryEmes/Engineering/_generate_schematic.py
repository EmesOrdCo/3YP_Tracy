"""Generate the system-overview diagram used in Section 2 of the report.

Shows a side-view schematic of the vehicle with every force the simulation
computes, annotated with the model that produces it. Saves a vector PDF
into figures/ that main.tex includes as fig:system_overview.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle, FancyBboxPatch
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)


fig, ax = plt.subplots(figsize=(10.0, 6.2))
ax.set_xlim(-1.1, 11.1)
ax.set_ylim(-2.8, 5.8)
ax.set_aspect("equal")
ax.axis("off")

# --- Ground line -------------------------------------------------------
ax.plot([-0.8, 10.8], [0.0, 0.0], color="0.25", lw=2.0)
for x in range(0, 11):
    ax.plot([x - 0.3, x - 0.1], [0.0, -0.25], color="0.25", lw=0.9)

# --- Car silhouette ----------------------------------------------------
# Wheels (two triangles/ellipses at front & rear axles)
wheel_r = 0.55
rear_x = 2.8
front_x = 7.2
for wx in (rear_x, front_x):
    c = Circle((wx, wheel_r), wheel_r, facecolor="0.15", edgecolor="0.05",
               zorder=3)
    ax.add_patch(c)
    ax.add_patch(Circle((wx, wheel_r), 0.18, facecolor="0.55",
                        edgecolor="0.05", zorder=4))

# Body: a simple low monocoque shape.
body_y = wheel_r + 0.15
body = [
    (rear_x - 1.3, body_y),
    (front_x + 1.0, body_y),
    (front_x + 1.0, body_y + 0.35),
    (front_x + 0.3, body_y + 0.35),
    (front_x - 0.9, body_y + 1.10),   # roll hoop top
    (rear_x - 0.2, body_y + 1.10),
    (rear_x - 0.2, body_y + 0.70),
    (rear_x - 1.3, body_y + 0.70),
    (rear_x - 1.3, body_y),
]
xs, ys = zip(*body)
ax.fill(xs, ys, facecolor="#1f77b4", alpha=0.18, edgecolor="#1f3a63",
        linewidth=1.5, zorder=2)

# CG marker.
cg_x, cg_z = 4.7, body_y + 0.55
ax.plot(cg_x, cg_z, marker="+", markersize=14, color="k",
        markeredgewidth=2, zorder=5)
ax.add_patch(Circle((cg_x, cg_z), 0.08, fill=False, edgecolor="k",
                    linewidth=1.2, zorder=5))
ax.annotate("CG", (cg_x, cg_z), xytext=(6, 6), textcoords="offset points",
            fontsize=10, weight="bold")

# Geometry dimensions (L, L_CG, h_CG).
ax.annotate("", xy=(rear_x, -0.7), xytext=(front_x, -0.7),
            arrowprops=dict(arrowstyle="<->", color="0.3", lw=1.0))
ax.text((rear_x + front_x) / 2, -0.95, "$L$", ha="center", fontsize=11,
        color="0.2")

ax.annotate("", xy=(rear_x, -1.5), xytext=(cg_x, -1.5),
            arrowprops=dict(arrowstyle="<->", color="0.3", lw=1.0))
ax.text((rear_x + cg_x) / 2, -1.75, "$L - L_{CG}$", ha="center", fontsize=10,
        color="0.2")

ax.annotate("", xy=(cg_x, 0.0), xytext=(cg_x, cg_z),
            arrowprops=dict(arrowstyle="<->", color="0.3", lw=1.0))
ax.text(cg_x + 0.1, cg_z / 2, "$h_{CG}$", ha="left", fontsize=10, color="0.2")


def force_arrow(x0, y0, dx, dy, colour, width=2.0):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x0 + dx, y0 + dy), arrowstyle="-|>",
        mutation_scale=18, color=colour, lw=width, zorder=6))


# --- Forces on the vehicle --------------------------------------------
# 1) Weight mg at CG, pointing down.
force_arrow(cg_x, cg_z, 0.0, -1.25, "#d62728")
ax.text(cg_x - 0.25, cg_z - 0.75, r"$m_v g$", fontsize=11,
        color="#d62728", ha="right", weight="bold")

# 2) Aerodynamic drag at CG, pointing backward (to the right of travel).
force_arrow(cg_x + 0.4, cg_z, 1.3, 0.0, "#9467bd")
ax.text(cg_x + 1.8, cg_z + 0.18, r"$F_\mathrm{drag}$", fontsize=11,
        color="#9467bd", ha="left", weight="bold")

# 3) Rolling resistance at each axle, pointing backward.
for wx in (rear_x, front_x):
    force_arrow(wx, 0.05, 0.5, 0.0, "#9467bd", width=1.4)
ax.text(rear_x + 0.55, 0.22, r"$F_\mathrm{rr}$", fontsize=10,
        color="#9467bd", ha="left")

# 4) Drive force at rear contact patch, pointing forward (to the LEFT,
#    since the vehicle travels to the LEFT in this schematic --- the force
#    the ground exerts on the tyre that accelerates the vehicle is directed
#    in the direction of travel).
# Actually the vehicle travels to the left in this drawing (rear is to the
# right of front in convention; but we have rear at 2.8, front at 7.2 --
# so the car actually moves in the -x direction to go "forward". Let's
# keep the convention: forward = direction the CAR points, i.e. from rear
# axle to front axle -- the +x direction.
# Rolling resistance and drag oppose motion, so they point in -x.
# Drive force at contact patch also points in +x (direction of travel).
# ...let's just redo with consistent convention: vehicle travels in +x.
pass


# Reset: make all arrows consistent. Vehicle travels in +x direction
# (left-to-right). Redraw forces with this convention.
# We need to clear and redraw forces. Simpler: just draw fresh.
# (The above force_arrow calls already pointed rolling resistance and drag
# in the wrong direction for +x travel. Fix by redrawing.)
# Remove all existing arrow patches and re-add.
for patch in list(ax.patches):
    if isinstance(patch, FancyArrowPatch):
        patch.remove()
# Also remove the force labels.
for text in list(ax.texts):
    if text.get_text() in (r"$m_v g$", r"$F_\mathrm{drag}$",
                            r"$F_\mathrm{rr}$"):
        text.remove()

# Redraw with +x = forward (right) convention.
# Weight: down.
force_arrow(cg_x, cg_z, 0.0, -1.25, "#d62728")
ax.text(cg_x - 0.18, cg_z - 0.7, r"$m_v g$", fontsize=11,
        color="#d62728", ha="right", weight="bold")

# Drag: opposes motion, so points in -x (leftward).
force_arrow(cg_x, cg_z + 0.05, -1.4, 0.0, "#9467bd")
ax.text(cg_x - 1.5, cg_z + 0.25, r"$F_\mathrm{drag}$", fontsize=11,
        color="#9467bd", ha="right", weight="bold")

# Rolling resistance at each axle, pointing in -x.
for wx in (rear_x, front_x):
    force_arrow(wx, 0.05, -0.55, 0.0, "#9467bd", width=1.4)
ax.text(rear_x - 0.65, 0.22, r"$F_\mathrm{rr}$", fontsize=10,
        color="#9467bd", ha="right")

# Normal forces (upward) at each contact patch.
force_arrow(rear_x, 0.0, 0.0, 1.1, "#2ca02c")
ax.text(rear_x + 0.1, 1.25, r"$F_{z,r}$", fontsize=11, color="#2ca02c",
        ha="left", weight="bold")

force_arrow(front_x, 0.0, 0.0, 1.1, "#2ca02c")
ax.text(front_x + 0.1, 1.25, r"$F_{z,f}$", fontsize=11, color="#2ca02c",
        ha="left", weight="bold")

# Downforce on body (optional / mostly zero for this project, but shown
# to indicate where it would act).
force_arrow(rear_x + 0.3, body_y + 0.8, 0.0, -0.6, "#2ca02c", width=1.2)
ax.text(rear_x + 0.4, body_y + 0.85, r"$F_{L,r}$", fontsize=9,
        color="#2ca02c", ha="left", alpha=0.8)
force_arrow(front_x - 0.3, body_y + 0.5, 0.0, -0.5, "#2ca02c", width=1.2)
ax.text(front_x - 0.4, body_y + 0.55, r"$F_{L,f}$", fontsize=9,
        color="#2ca02c", ha="right", alpha=0.8)

# Tractive force at rear contact patch, pointing in +x (forward).
force_arrow(rear_x, 0.05, 1.6, 0.0, "#1f77b4", width=2.6)
ax.text(rear_x + 0.8, -0.35, r"$F_x$", fontsize=12, color="#1f77b4",
        ha="center", weight="bold")

# Motion direction indicator.
ax.annotate("", xy=(10.4, 4.7), xytext=(9.2, 4.7),
            arrowprops=dict(arrowstyle="-|>", color="0.25", lw=1.4))
ax.text(10.2, 4.95, "direction of motion", fontsize=9, color="0.25",
        ha="right")

# --- Model-source callouts --------------------------------------------
# Each box identifies the model that produces the force pointed at.
def callout(xy_text, xy_force, text, fc="#eef2fb"):
    box = FancyBboxPatch((xy_text[0] - 1.05, xy_text[1] - 0.28),
                          2.1, 0.56,
                          boxstyle="round,pad=0.05",
                          linewidth=0.8, edgecolor="0.25",
                          facecolor=fc, zorder=7)
    ax.add_patch(box)
    ax.text(*xy_text, text, ha="center", va="center", fontsize=8.4,
            zorder=8)
    ax.add_patch(FancyArrowPatch(xy_text, xy_force, arrowstyle="->",
                                 mutation_scale=10, color="0.35",
                                 lw=0.7, ls=(0, (3, 2)), zorder=7))


callout((1.4, 4.5), (cg_x - 1.0, cg_z + 0.05),
        "Aerodynamics\n(§2.5)\n$F_\\mathrm{drag},\\; F_{L,f/r}$",
        fc="#f6ecff")
callout((5.0, 4.8), (cg_x, cg_z),
        "Mass Properties\n(§2.2)\n$F_{z,f},\\; F_{z,r},\\; \\Delta F_z$",
        fc="#eaf6ea")
callout((8.6, 4.5), (rear_x + 1.4, 0.05),
        "Tyre Model (§2.3)\n+ Powertrain (§2.4)\n$F_x = \\mu(\\kappa, F_z)\\, F_z$",
        fc="#e7efff")

# Data flow indicators inside the diagram: state -> models -> forces
# -> EoM.
ax.text(cg_x, -2.45,
        r"$(m_v + 4 I_w / r_w^2)\, a = F_x - F_\mathrm{drag} - F_\mathrm{rr}$"
        "     " r"$\longrightarrow$     "
        "RK4 integrator " r"$\longrightarrow$" " new state",
        fontsize=11, ha="center")

fig.tight_layout(pad=0.2)
out_pdf = FIG / "system_overview.pdf"
fig.savefig(out_pdf, bbox_inches="tight")
plt.close(fig)
print(f"Wrote {out_pdf}")
