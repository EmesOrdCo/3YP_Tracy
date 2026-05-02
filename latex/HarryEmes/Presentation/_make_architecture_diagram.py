"""Generate the layered software-architecture diagram for slide 1.

Replacement for the hand-drawn version: enforces top-to-bottom data flow,
equal-width layer rows, consistent typography, and a clean
``Dynamics Solver`` <-> ``Vehicle Models`` bidirectional link.
Outputs both PDF (vector, for LaTeX) and PNG (preview).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

SLIDE_BG = "#E8E8E8"
INK      = "#1A1A1A"
MUTED    = "#5C5C5C"

# Big slide-readable typography
F_LAYER   = 26   # layer name in the header strip
F_ROLE    = 17   # role (italic) under layer name
F_CHIP    = 22   # item chip label (single column rows)
F_CHIP_2C = 19   # chip label when in 2-col grid (Vehicle Models)

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)


# --- Layer definitions --------------------------------------------------
# Tonal pastels (lighter fill, darker accent stripe) -- single hue per
# layer keeps the page calm but still labels each role.
LAYERS = [
    dict(
        name="CONFIG",
        role="inputs",
        fill="#D8E4F2", edge="#2E6BB0",
        items=["JSON file", "load_config", "validate"],
    ),
    dict(
        name="SIMULATION",
        role="orchestrator",
        fill="#FBEAC4", edge="#B0892E",
        items=["Initialise\nsolver", "Run-loop\norchestration"],
    ),
    # The DYNAMICS+VEHICLE row is special: laid out side-by-side below.
    dict(
        name="RULES",
        role="compliance",
        fill="#E1D6EE", edge="#6A4A9A",
        items=["80\u202fkW limit\n(FS-EV 2.2)",
               "25\u202fs limit\n(FS-D 5.3.1)",
               "Score\n(FS-D 5.3.2)"],
    ),
    dict(
        name="RESULTS",
        role="output",
        fill="#D1E7D6", edge="#3F8B58",
        items=["75\u202fm time", "Score", "Power /\nforce traces",
               "Compliance\nflags"],
    ),
]

DYNAMICS = dict(
    name="DYNAMICS",
    role="core",
    fill="#F2D3CE", edge="#B04A36",
    items=["RK4 integrator\n(1\u202fms)",
           "Compute\nderivatives",
           "State\n(x, v, $\\omega$)"],
    ncols=1,
)
VEHICLE = dict(
    name="VEHICLE MODELS",
    role="physics",
    fill="#F7DBC2", edge="#C57723",
    items=["Mass +\nload transfer",   "Tyre\n(Pacejka)",
           "Powertrain\n(80\u202fkW cap)", "Aerodynamics",
           "Suspension\ngeometry",   "Control\nstrategy"],
    ncols=2,
)


# --- Geometry -----------------------------------------------------------
W, H = 13.0, 11.5             # canvas in inches
fig, ax = plt.subplots(figsize=(W, H))
fig.patch.set_facecolor(SLIDE_BG)
ax.set_facecolor(SLIDE_BG)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")

# Layout constants
LEFT_PAD   = 0.5
RIGHT_PAD  = 0.5
TOP        = H - 0.4
BOT        = 0.5
LAYER_H    = 1.40
LAYER_GAP  = 0.32
DYN_VEH_H  = 3.55         # taller core row to fit stacked 2-line chips
HEADER_W   = 2.85         # left-edge label strip width (fits "SIMULATION" at 26pt)
RADIUS     = 0.10


def draw_layer(y_top, layer, *, full_width=True, x0=LEFT_PAD, x1=W-RIGHT_PAD,
               height=LAYER_H, items=None):
    """Draw a single layer row: coloured strip on the left + items panel."""
    items = layer["items"] if items is None else items
    fill, edge = layer["fill"], layer["edge"]
    name, role = layer["name"], layer["role"]

    y_bot = y_top - height
    # Outer panel (light fill, thin border)
    panel = FancyBboxPatch(
        (x0, y_bot), x1 - x0, height,
        boxstyle=f"round,pad=0.0,rounding_size={RADIUS}",
        linewidth=1.0, edgecolor=edge, facecolor=fill, zorder=2,
    )
    ax.add_patch(panel)

    # Header strip (darker accent bar with the layer name)
    head = FancyBboxPatch(
        (x0, y_bot), HEADER_W, height,
        boxstyle=f"round,pad=0.0,rounding_size={RADIUS}",
        linewidth=0, facecolor=edge, zorder=3,
    )
    ax.add_patch(head)
    # Hard-edge the right side of the header so it butts up to items area
    ax.add_patch(FancyBboxPatch(
        (x0 + HEADER_W - RADIUS, y_bot), RADIUS, height,
        boxstyle="square,pad=0", linewidth=0, facecolor=edge, zorder=3,
    ))
    ax.text(x0 + HEADER_W/2, y_bot + height/2 + 0.20, name,
            color="white", fontsize=F_LAYER, fontweight="bold",
            ha="center", va="center", zorder=4)
    ax.text(x0 + HEADER_W/2, y_bot + height/2 - 0.34, role,
            color="white", fontsize=F_ROLE, alpha=0.85, style="italic",
            ha="center", va="center", zorder=4)

    # Item chips, evenly distributed across the items zone
    items_x0 = x0 + HEADER_W + 0.25
    items_x1 = x1 - 0.20
    n = len(items)
    chip_pad_x, chip_pad_y = 0.25, 0.18
    chip_h = max(0.55, height - 2*chip_pad_y)
    total_w = items_x1 - items_x0
    chip_gap = 0.18
    chip_w = (total_w - (n - 1) * chip_gap) / n
    cy = y_bot + height/2

    for i, label in enumerate(items):
        cx = items_x0 + i * (chip_w + chip_gap)
        chip = FancyBboxPatch(
            (cx, cy - chip_h/2), chip_w, chip_h,
            boxstyle=f"round,pad=0.0,rounding_size=0.06",
            linewidth=0.8, edgecolor=edge, facecolor="white", zorder=4,
        )
        ax.add_patch(chip)
        ax.text(cx + chip_w/2, cy, label,
                color=INK, fontsize=F_CHIP, ha="center", va="center", zorder=5)

    return y_bot


def draw_block_header(x0, y_top, w, h, layer):
    """Header-on-top variant for the side-by-side Dynamics+Vehicle row.

    Items are laid out in ``layer.get('ncols', 1)`` columns of fixed-height
    chips, with explicit gaps. Avoids degenerate chip heights when
    ``len(items)`` is large.
    """
    fill, edge = layer["fill"], layer["edge"]
    ncols = layer.get("ncols", 1)
    panel = FancyBboxPatch(
        (x0, y_top - h), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={RADIUS}",
        linewidth=1.0, edgecolor=edge, facecolor=fill, zorder=2,
    )
    ax.add_patch(panel)

    head_h = 0.95
    head = FancyBboxPatch(
        (x0, y_top - head_h), w, head_h,
        boxstyle=f"round,pad=0.0,rounding_size={RADIUS}",
        linewidth=0, facecolor=edge, zorder=3,
    )
    ax.add_patch(head)
    ax.add_patch(FancyBboxPatch(
        (x0, y_top - head_h - 0.001), w, RADIUS,
        boxstyle="square,pad=0", linewidth=0, facecolor=edge, zorder=3,
    ))
    # Layer name (bold) and role (italic) both in the header strip --
    # the role italic at the bottom of the panel was overlapping the chips.
    ax.text(x0 + w/2, y_top - head_h/2 + 0.10, layer["name"],
            color="white", fontsize=F_LAYER, fontweight="bold",
            ha="center", va="center", zorder=4)
    ax.text(x0 + w/2, y_top - head_h/2 - 0.30, layer["role"],
            color="white", fontsize=F_ROLE, alpha=0.85, style="italic",
            ha="center", va="center", zorder=4)

    # Item chips: fixed height, stacked top-down, optional 2-col grid.
    items = layer["items"]
    nrows = (len(items) + ncols - 1) // ncols
    chip_inset_x = 0.20
    chip_inset_y = 0.22
    grid_x0 = x0 + chip_inset_x
    grid_x1 = x0 + w - chip_inset_x
    grid_top = y_top - head_h - chip_inset_y
    grid_bot = y_top - h + 0.18  # role italic now in header, slim bottom pad
    col_gap  = 0.12
    row_gap  = 0.10
    chip_w   = (grid_x1 - grid_x0 - col_gap * (ncols - 1)) / ncols
    chip_h   = (grid_top - grid_bot - row_gap * (nrows - 1)) / nrows

    for idx, label in enumerate(items):
        r, c = divmod(idx, ncols)
        cx = grid_x0 + c * (chip_w + col_gap)
        cy_top = grid_top - r * (chip_h + row_gap)
        chip = FancyBboxPatch(
            (cx, cy_top - chip_h), chip_w, chip_h,
            boxstyle="round,pad=0,rounding_size=0.06",
            linewidth=0.8, edgecolor=edge, facecolor="white", zorder=4,
        )
        ax.add_patch(chip)
        fs = F_CHIP if ncols == 1 else F_CHIP_2C
        ax.text(cx + chip_w/2, cy_top - chip_h/2,
                label, color=INK, fontsize=fs,
                ha="center", va="center", zorder=5)


def vertical_arrow(y_from, y_to, x=W/2, label=None):
    arr = FancyArrowPatch(
        (x, y_from), (x, y_to),
        arrowstyle="-|>", mutation_scale=14,
        linewidth=1.4, color=MUTED, zorder=1,
    )
    ax.add_patch(arr)
    if label:
        ax.text(x + 0.18, (y_from + y_to)/2, label,
                fontsize=12, color=MUTED, ha="left", va="center",
                style="italic")


# --- Render -------------------------------------------------------------
y = TOP

# 1. Config
y_after_config = draw_layer(y, LAYERS[0])
vertical_arrow(y_after_config, y_after_config - LAYER_GAP, x=W/2)

# 2. Simulation
y = y_after_config - LAYER_GAP
y_after_sim = draw_layer(y, LAYERS[1])
vertical_arrow(y_after_sim, y_after_sim - LAYER_GAP, x=W/2)

# 3. Dynamics + Vehicle (side-by-side row)
y = y_after_sim - LAYER_GAP
core_top = y
gap_xy = 0.50
left_x0  = LEFT_PAD
right_x1 = W - RIGHT_PAD
half_w   = (right_x1 - left_x0 - gap_xy) / 2
draw_block_header(left_x0, core_top, half_w, DYN_VEH_H, DYNAMICS)
draw_block_header(left_x0 + half_w + gap_xy, core_top, half_w, DYN_VEH_H, VEHICLE)

# Bidirectional arrow between them
arr_y = core_top - DYN_VEH_H/2
ax.add_patch(FancyArrowPatch(
    (left_x0 + half_w + 0.04, arr_y),
    (left_x0 + half_w + gap_xy - 0.04, arr_y),
    arrowstyle="<|-|>", mutation_scale=14,
    linewidth=1.6, color=MUTED, zorder=6,
))
ax.text(left_x0 + half_w + gap_xy/2, arr_y + 0.22,
        "state", fontsize=12, color=MUTED, ha="center", va="bottom",
        style="italic")
ax.text(left_x0 + half_w + gap_xy/2, arr_y - 0.22,
        "forces", fontsize=12, color=MUTED, ha="center", va="top",
        style="italic")

y_after_core = core_top - DYN_VEH_H
vertical_arrow(y_after_core, y_after_core - LAYER_GAP, x=W/2)

# 4. Rules
y = y_after_core - LAYER_GAP
y_after_rules = draw_layer(y, LAYERS[2])
vertical_arrow(y_after_rules, y_after_rules - LAYER_GAP, x=W/2)

# 5. Results
y = y_after_rules - LAYER_GAP
draw_layer(y, LAYERS[3])

# No internal title -- LaTeX figlabel sits above the figure on the slide.


# --- Save ---------------------------------------------------------------
fig.tight_layout(pad=0.4)
out_pdf = OUT / "harry_architecture.pdf"
out_png = OUT / "harry_architecture.png"
fig.savefig(out_pdf, bbox_inches="tight",
            facecolor=SLIDE_BG, edgecolor=SLIDE_BG)
fig.savefig(out_png, bbox_inches="tight", dpi=200,
            facecolor=SLIDE_BG, edgecolor=SLIDE_BG)
plt.close(fig)
print(f"Wrote {out_pdf}")
print(f"Wrote {out_png}")
