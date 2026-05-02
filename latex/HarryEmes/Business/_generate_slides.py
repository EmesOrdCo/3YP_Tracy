"""Generate presentation PDFs (16:9 landscape) for the Financial
Evaluation chapter (slides 1\u20133).

Each slide is a single landscape PDF; charts are re-rendered from
the financial_model.json so that titles, fonts and colours match the
chapter figures.

Run from this directory:
    python _generate_slides.py
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.gridspec import GridSpec

HERE = Path(__file__).parent
SLIDES = HERE / "slides"
SLIDES.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size":       13,        # base for chart text
    "axes.titlesize":  17,        # chart titles
    "axes.labelsize":  14,        # axis labels
    "xtick.labelsize": 12,        # tick labels (smallest acceptable for projected charts)
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "savefig.dpi":     220,
    "savefig.bbox":    "tight",
    "axes.grid":       True,
    "grid.alpha":      0.3,
    "grid.linestyle":  "--",
})

C_BRAND  = "#0B3D91"
C_ACCENT = "#F39C12"
C_GREEN  = "#2E8B57"
C_RED    = "#C0392B"
# Darkened from #7F8C8D so secondary text on the #E8E8E8 slide
# background clears WCAG-AA contrast for normal-size text.
C_GREY   = "#555555"
C_LIGHT  = "#D5DBDB"
C_BG     = "#E8E8E8"

SLIDE_W, SLIDE_H = 13.33, 7.5  # 16:9 in inches


def load() -> dict:
    return json.loads((HERE / "financial_model.json").read_text())


# ---------------------------------------------------------------------
#  Reusable building blocks
# ---------------------------------------------------------------------

def add_title_strip(fig, title: str, subtitle: str = "") -> None:
    """Coloured title strip across the top.

    Title and subtitle are stacked vertically (title above, subtitle
    below) so the slide title can run long without colliding with
    the subtitle. The strip is taller than a single-line strip to
    accommodate both lines at full font size.
    """
    ax = fig.add_axes([0, 0.88, 1, 0.12])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=C_BRAND))
    if subtitle:
        ax.text(0.02, 0.66, title, color="white", fontsize=24,
                fontweight="bold", va="center", ha="left")
        ax.text(0.02, 0.28, subtitle, color="white", fontsize=14,
                va="center", ha="left", style="italic")
    else:
        ax.text(0.02, 0.50, title, color="white", fontsize=24,
                fontweight="bold", va="center", ha="left")


def add_footer_strip(fig, text: str, color=C_LIGHT,
                     secondary: str = "") -> None:
    """Footer strip across the bottom.

    If ``secondary`` is provided, the primary text is rendered larger
    on the left and the secondary text smaller and italic on the right.
    """
    ax = fig.add_axes([0, 0, 1, 0.05])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=color))
    if secondary:
        ax.text(0.015, 0.5, text, color="black", fontsize=14,
                fontweight="bold", va="center", ha="left")
        ax.text(0.985, 0.5, secondary, color=C_GREY, fontsize=11,
                va="center", ha="right", style="italic")
    else:
        ax.text(0.5, 0.5, text, color="black", fontsize=13,
                va="center", ha="center", style="italic")


def add_recommendation_strip(fig, text: str) -> None:
    """Bold recommendation strip near the bottom (slide 2).

    Black text on the orange (#F39C12) band -- contrast 7.4:1, well
    inside WCAG-AAA. (White on orange would be only 2.0:1, failing
    even the WCAG-AA threshold for large text.)
    """
    ax = fig.add_axes([0, 0.04, 1, 0.10])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=C_ACCENT))
    ax.text(0.5, 0.5, text, color="black", fontsize=18,
            va="center", ha="center", fontweight="bold")


def add_kpi_tile(fig, x: float, y: float, w: float, h: float,
                 value: str, label: str, color=C_BRAND,
                 sublabel: str = "") -> None:
    """A single KPI tile with big value + small label.

    Sublabel may contain a newline ('\\n') for two-line annotations.
    Long single-line values shrink and clip so adjacent tiles never
    visually merge (matplotlib text defaults draw outside the axes).
    """
    ax = fig.add_axes([x, y, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.02, 0.05), 0.96, 0.9,
        boxstyle="round,pad=0.02",
        facecolor="white", edgecolor=color, linewidth=2, zorder=0))
    # Value: two lines (explicit \\n) use a slightly smaller size;
    # long one-liners also shrink so glyphs stay inside the tile.
    val_plain = value.replace("\n", "")
    n_val_lines = value.count("\n") + 1
    if n_val_lines >= 2:
        val_fs = 22
    elif len(val_plain) > 18:
        val_fs = 21
    elif len(val_plain) > 14:
        val_fs = 24
    else:
        val_fs = 28
    vy = 0.72 if n_val_lines >= 2 else 0.70
    ax.text(
        0.5, vy, value, color=color, fontsize=val_fs,
        fontweight="bold", va="center", ha="center",
        linespacing=1.05, clip_on=True, zorder=2,
    )
    ax.text(
        0.5, 0.38, label, color="black", fontsize=15,
        va="center", ha="center", clip_on=True, zorder=2,
    )
    if sublabel:
        # Slightly smaller font for two-line sublabels so the vertical
        # spread fits the bottom of the tile cleanly.
        is_multiline = "\n" in sublabel
        ax.text(
            0.5, 0.14, sublabel, color=C_GREY,
            fontsize=10 if is_multiline else 12,
            va="center", ha="center", style="italic",
            linespacing=1.15, clip_on=True, zorder=2,
        )


def add_slide1_driver_chip(fig, x: float, y: float, w: float, h: float,
                           title: str, value: str, color: str) -> None:
    """Driver chip: title (name) on top, value below (slide 1, under chart)."""
    ax = fig.add_axes([x, y, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.025, 0.07), 0.95, 0.86,
        boxstyle="round,pad=0.012",
        facecolor="white", edgecolor=color, linewidth=1.5, zorder=0))
    n_t, n_v = len(title), len(value)
    n_max = max(n_t, n_v)
    name_fs = 8 if n_max > 28 else 9 if n_max > 22 else 10
    val_fs = 9 if n_max > 28 else 10 if n_max > 22 else 11
    ax.text(
        0.5, 0.66, title, color=C_GREY, fontsize=name_fs,
        fontweight="bold", va="center", ha="center",
        clip_on=True, zorder=1,
    )
    ax.text(
        0.5, 0.28, value, color=color, fontsize=val_fs,
        fontweight="bold", va="center", ha="center",
        clip_on=True, zorder=1,
    )


def _wrap_callout_block(text: str, width: int) -> str:
    """Hard-wrap each paragraph (split on newlines) for narrow callouts.

    Matplotlib does not reflow long strings inside ``ax.text``; without
    this, sublines spill across neighbouring boxes on slide~2.
    """
    out: list[str] = []
    for para in text.split("\n"):
        p = para.strip()
        if not p:
            out.append("")
            continue
        wrapped = textwrap.fill(
            p,
            width=width,
            break_long_words=False,
            replace_whitespace=True,
        )
        out.append(wrapped)
    return "\n".join(out)


def add_callout_box(fig, x: float, y: float, w: float, h: float,
                    headline: str, sub: str, color=C_BRAND) -> None:
    """Outlined callout with a headline metric and supporting line.

    Uses the supplied colour for the outline and the headline text;
    the supporting line stays neutral grey for visual hierarchy.
    Headline and sub are **hard-wrapped** to the box width so text
    cannot spill into adjacent callouts (matplotlib has no auto-wrap
    here). Intentional ``\\n`` in the input are preserved as paragraph
    breaks before wrapping each paragraph. Border is a plain rectangle
    so all four sides render clearly at slide scale.
    """
    ax = fig.add_axes([x, y, w, h])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    # Rectangle (not FancyBbox): heavy rounding on short, wide boxes
    # can make left/right edges look missing; four-sided stroke is clearer.
    ax.add_patch(mpatches.Rectangle(
        (0.006, 0.05), 0.988, 0.9,
        facecolor="white", edgecolor=color, linewidth=2,
        joinstyle="round"))

    # Char-wrap widths: wide enough that copy uses horizontal space
    # inside the tighter rounded-rect margins (slide 2 callouts).
    headline_w = 28
    sub_w = 34
    headline_txt = _wrap_callout_block(headline, headline_w)
    sub_txt = _wrap_callout_block(sub, sub_w)
    sub_lines = max(1, sub_txt.count("\n") + 1)
    # Slightly smaller than KPI tiles so three callouts fit without
    # clipping the top of multi-line headlines inside short boxes.
    headline_fs = 19
    sub_fs = 13 if sub_lines >= 3 else 14

    # Headline and sub clustered near the vertical centre so the pair
    # reads as one block (avoids a tall empty band between top- and
    # bottom-pinned text when copy is short).
    ax.text(0.5, 0.56, headline_txt, color=color, fontsize=headline_fs,
            fontweight="bold", va="bottom", ha="center",
            linespacing=1.08)
    ax.text(0.5, 0.42, sub_txt, color=C_GREY, fontsize=sub_fs,
            va="top", ha="center", style="italic",
            linespacing=1.08)


# ---------------------------------------------------------------------
#  Charts (re-rendered into the slide canvas)
# ---------------------------------------------------------------------

def render_revenue_ramp(ax_left, ax_right_axis, d: dict) -> None:
    """Stacked-cost + net-profit chart on a single axis pair, with
    Seed and Series A funding-round annotations on the timeline."""
    years = d["years"]
    rev   = d["pnl"]["Revenue (\\pounds k)"]
    vcost = [-v for v in d["pnl"]["Variable cost (\\pounds k)"]]
    fixed = [-v for v in d["pnl"]["Fixed opex (\\pounds k)"]]
    dep   = [-v for v in d["pnl"]["Depreciation (\\pounds k)"]]
    net   = d["pnl"]["Net profit (\\pounds k)"]

    x = np.arange(len(years))
    w = 0.35

    ax_left.bar(x - w/2, rev, w, label="Revenue", color=C_BRAND)
    ax_left.bar(x + w/2, vcost, w, label="Variable cost", color=C_ACCENT)
    ax_left.bar(x + w/2, fixed, w, bottom=vcost,
                label="Fixed opex", color=C_GREY)
    ax_left.bar(x + w/2, dep, w,
                bottom=[a + b for a, b in zip(vcost, fixed)],
                label="Depreciation", color=C_LIGHT)

    ax_right_axis.plot(x, net, color=C_RED, marker="o",
                      linewidth=2.5, label="Net profit")
    ax_right_axis.axhline(0, color=C_RED, linestyle=":", linewidth=1)
    ax_right_axis.set_ylabel("Net profit (\u00a3k)", color=C_RED)
    ax_right_axis.tick_params(axis="y", labelcolor=C_RED)

    ax_left.set_xticks(x)
    ax_left.set_xticklabels([f"Y{y}" for y in years])
    ax_left.set_ylabel("\u00a3k")
    ax_left.set_title("Revenue scales ahead of cost; profit turns positive in Y4",
                      fontweight="bold", fontsize=17)
    ax_left.legend(loc="upper left", fontsize=12, framealpha=0.92)
    ax_right_axis.legend(loc="lower right", fontsize=12,
                         framealpha=0.92)
    # Pull x tick labels slightly toward the axis so they stay inside the
    # axes bbox (slide 1 stacks driver chips in figure space just below).
    ax_left.tick_params(axis="x", which="major", pad=1.5, labelsize=10.5)
    ax_left.set_xmargin(0.02)


def render_downtime(ax1, ax2, d: dict) -> None:
    """Two-panel downtime sensitivity (NPV + EBIT), matching report figure."""
    dt = d["downtime_sensitivity"]
    pct      = dt["Downtime (\\%)"]
    y3_ebit  = dt["Y3 EBIT (\\pounds k)"]
    y5_ebit  = dt["Y5 EBIT (\\pounds k)"]
    npv20    = dt["NPV@20\\% (\\pounds k)"]

    ax1.plot(pct, npv20, marker="o", color=C_BRAND, linewidth=2.5,
             label="NPV @ 20%")
    ax1.axhline(0, color="black", linewidth=0.7)
    ax1.set_xlabel("Unplanned downtime (% of planned days)")
    ax1.set_ylabel("NPV @ 20% (\u00a3k)", color=C_BRAND)
    ax1.tick_params(axis="y", labelcolor=C_BRAND)
    ax1.set_title("Project NPV vs. downtime",
                  fontweight="bold", fontsize=16)
    ax1.legend(loc="upper right", fontsize=12)

    ax2.plot(pct, y3_ebit, marker="o", color=C_RED, linewidth=2.5,
             label="Y3 EBIT")
    ax2.plot(pct, y5_ebit, marker="s", color=C_GREEN, linewidth=2.5,
             label="Y5 EBIT")
    ax2.axhline(0, color="black", linewidth=0.7)
    ax2.fill_between(pct, y3_ebit, y5_ebit, color=C_GREY, alpha=0.12)
    ax2.set_xlabel("Unplanned downtime (% of planned days)")
    ax2.set_ylabel("EBIT (\u00a3k)")
    ax2.set_title("EBIT vs. downtime (Y3 \u0026 Y5)",
                  fontweight="bold", fontsize=16)
    ax2.legend(loc="upper right", fontsize=12)


def render_tornado(ax, d: dict) -> None:
    """Tornado sensitivity panel (Y3 EBIT, +/-20% perturbation)."""
    s = d["sensitivity"]
    drivers = s["Driver"]
    base    = s["Base EBIT (\\pounds k)"][0]
    low     = s["Low EBIT (\\pounds k)"]
    high    = s["High EBIT (\\pounds k)"]
    swing   = [abs(h - l) for h, l in zip(high, low)]

    order   = np.argsort(swing)[::-1]
    drivers = [drivers[i] for i in order]
    low     = [low[i] for i in order]
    high    = [high[i] for i in order]

    y = np.arange(len(drivers))
    ax.barh(y, [l - base for l in low], color=C_RED,   label="Unfavourable")
    ax.barh(y, [h - base for h in high], color=C_GREEN, label="Favourable")
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(drivers, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("Y3 EBIT swing vs. base (\u00a3k)")
    ax.set_title("Day-rate \u0026 utilisation dominate",
                 fontweight="bold", fontsize=16)
    # Legend handled separately by a dedicated axes outside the chart,
    # placed in clean space at the bottom of the slide; see
    # _draw_slide_2().


def render_downtime_npv_only(ax, d: dict) -> None:
    """Single-panel downtime: NPV @ 20% vs downtime, zero baseline.
    Optional vertical marker where NPV first crosses zero (only if
    that occurs inside the modelled downtime grid)."""
    dt = d["downtime_sensitivity"]
    pct   = np.array(dt["Downtime (\\%)"])
    npv20 = np.array(dt["NPV@20\\% (\\pounds k)"])

    ax.plot(pct, npv20, marker="o", color=C_BRAND, linewidth=2.5,
            label="NPV @ 20%")
    ax.axhline(0, color="black", linewidth=0.7)

    cross = None
    for i in range(len(pct) - 1):
        if npv20[i] * npv20[i + 1] < 0:
            cross = (pct[i] + (pct[i + 1] - pct[i])
                     * npv20[i] / (npv20[i] - npv20[i + 1]))
            break
    if cross is not None:
        ax.axvline(cross, color=C_BLUE_DARKEST, linestyle="--",
                   linewidth=1.2, alpha=0.7)

    ax.set_xlabel("Unplanned downtime (% of planned days)")
    ax.set_ylabel("NPV @ 20% (\u00a3k)", color=C_BRAND)
    ax.tick_params(axis="y", labelcolor=C_BRAND)
    ax.set_title("Project NPV vs. downtime",
                 fontweight="bold", fontsize=16)
    ax.legend(loc="upper right", fontsize=12)


def add_scenario_strip(fig, y0: float, height: float,
                       d: dict) -> None:
    """One-line scenarios summary: bull / base / bear Y5 net profit
    rendered inline as supporting evidence under the charts."""
    s = d["scenarios"]
    bull = s["bull"]["net_profit"][-1]
    base = s["base"]["net_profit"][-1]
    bear = s["bear"]["net_profit"][-1]

    ax = fig.add_axes([0.04, y0, 0.94, height])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def _fmt(v):
        sign = "+" if v >= 0 else "-"
        return f"{sign}\u00a3{abs(v):,.0f} k"

    line = (
        "Bull  /  Base  /  Bear   (Y5 net profit):    "
        f"{_fmt(bull)}    /    {_fmt(base)}    /    {_fmt(bear)}"
    )
    ax.text(0.5, 0.5, line, fontsize=15, color="black",
            ha="center", va="center", style="italic")


# ---------------------------------------------------------------------
#  SLIDE 1
# ---------------------------------------------------------------------

# Oxford-style blues for charts, callouts, and shared styling.
C_BLUE_DARKEST  = "#08306B"
C_BLUE_DARK     = "#0B3D91"   # = C_BRAND
C_BLUE_MID_DARK = "#1F4E96"
C_BLUE_MID      = "#3B6FB5"
C_BLUE_LIGHT    = "#5481C5"
# Lightest step: must read clearly lighter than C_BLUE_LIGHT on #E8E8E8.
C_BLUE_LIGHTER  = "#6FA0DE"

# Slide 1 KPI grid: right column, 2 x 3 (positions 1--6). Edge runs dark -> light.
SLIDE_1_KPI_TILE_EDGE = (
    C_BLUE_DARKEST,
    C_BLUE_DARK,
    C_BLUE_MID_DARK,
    C_BLUE_MID,
    C_BLUE_LIGHT,
    C_BLUE_LIGHTER,
)


def slide_1_under_chart_headlines(
    d: dict,
) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str]]:
    """(title, value) pairs for three stacked driver chips under the chart."""
    days = d["utilisation_days"]
    rates = d["blended_day_rate"]
    vcd = d["variable_cost_per_day"]
    r0, r4 = rates[0] / 1000.0, rates[-1] / 1000.0
    v0, v4 = vcd[0] / 1000.0, vcd[-1] / 1000.0
    return (
        ("Utilisation", f"{int(days[0])} -> {int(days[-1])} d/yr"),
        ("Blended rate", f"\u00a3{r0:.1f}k -> \u00a3{r4:.1f}k/d"),
        ("Variable cost", f"\u00a3{v0:.1f}k -> \u00a3{v4:.1f}k/d"),
    )


def slide_1_kpi_tiles(d: dict):
    """Six KPI tiles for slide 1: (value, label, sublabel) per position.

    Outline colours: ``SLIDE_1_KPI_TILE_EDGE[i]``. NPV is read from JSON.
    Utilisation, day-rate, and variable-cost chips sit under the chart.
    """
    npv_k = float(d["npv"]["npv_at_rate"]["20"])
    npv_m = npv_k / 1000.0
    npv_val = f"\u00a3 {npv_m:.2f} M"
    return [
        ("\u00a3 0.98 M", "Total CAPEX over 5 yrs", "3 vehicles + Y1 setup"),
        ("\u00a3 2.5 M", "Equity raised",
         "\u00a31.0 M Seed (Y1)\n\u00a31.5 M Series A (Y3)"),
        ("122 days / yr", "Break-even utilisation",
         "covers fixed costs + depreciation"),
        (npv_val, "Project NPV @ 20%", "5-yr FCF + Y5 terminal value"),
        ("\u00a3 5.2 M", "Indicative Y5 exit value", "@ 2.5\u00d7 Y5 revenue"),
        ("\u00a3 538 k", "Y1 fixed OPEX", "60% headcount; ~3% inflation/yr"),
    ]


def _draw_slide_1(fig, d: dict) -> None:
    add_title_strip(
        fig,
        title="AEB Rabbit TaaS  \u2014  key assumptions & 5-year financial profile",
        subtitle="Harry Emes  |  Financial Evaluation",
    )

    # Left column: compact driver chips just above the footer, then a
    # generous figure-space gutter so x-axis tick labels (which extend
    # below the axes bbox) never overlap the chips.
    # Slightly wider left column so the three driver chips read larger.
    chart_x, chart_w = 0.04, 0.46
    n_chips = 3
    chip_gap = 0.007
    chip_y = 0.052
    chip_h = 0.050
    chip_w = (chart_w - (n_chips - 1) * chip_gap) / n_chips
    # Space reserved under the chart for tick labels + padding.
    label_gutter = 0.066
    chart_bottom = chip_y + chip_h + label_gutter
    chart_h = max(0.48, 0.855 - chart_bottom)

    ax_chart = fig.add_axes([chart_x, chart_bottom, chart_w, chart_h])
    ax_right = ax_chart.twinx()
    render_revenue_ramp(ax_chart, ax_right, d)

    chip_colors = (C_BLUE_MID_DARK, C_BLUE_MID, C_BLUE_DARK)
    for j, ((title, value), c_edge) in enumerate(
            zip(slide_1_under_chart_headlines(d), chip_colors)):
        x_chip = chart_x + j * (chip_w + chip_gap)
        add_slide1_driver_chip(fig, x_chip, chip_y, chip_w, chip_h,
                               title, value, c_edge)

    # KPI tiles right -- 2 columns x 3 rows = 6 tiles.
    grid_x0 = 0.55
    grid_w  = 0.43
    col_w   = grid_w / 2
    row_h   = 0.218
    gap_x   = 0.012
    gap_y   = 0.014
    base_y  = 0.13
    tiles = slide_1_kpi_tiles(d)
    n_rows = (len(tiles) + 1) // 2
    for i, (value, label, sublabel) in enumerate(tiles):
        col = i % 2
        row = i // 2
        x = grid_x0 + col * col_w
        y = base_y + (n_rows - 1 - row) * (row_h + gap_y)
        add_kpi_tile(
            fig, x + gap_x / 2, y, col_w - gap_x, row_h,
            value=value, label=label, sublabel=sublabel,
            color=SLIDE_1_KPI_TILE_EDGE[i],
        )

    add_footer_strip(
        fig,
        text="Series A trigger:  \u2265 \u00a3400 k ARR  +  2 retainer customers  (target Q4-Y2 close)",
        secondary="Driver-based Python model \u2014 single source for every number",
    )


def make_slide_1(d: dict) -> None:
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), facecolor=C_BG)
    _draw_slide_1(fig, d)
    plt.savefig(SLIDES / "slide_1.pdf", facecolor=C_BG)
    plt.savefig(SLIDES / "slide_1.png", dpi=180, facecolor=C_BG)
    plt.close()


# ---------------------------------------------------------------------
#  SLIDE 2
# ---------------------------------------------------------------------

def _draw_slide_2(fig, d: dict) -> None:
    add_title_strip(
        fig,
        title="Where it could break \u2014 and what defends it",
        subtitle="Harry Emes  |  Sensitivity \u0026 Downtime Analysis",
    )

    # Layout (top-down):
    #   title strip       0.88 - 1.00
    #   charts            0.42 - 0.84   (full slide width)
    #   tornado legend    0.31 - 0.36
    #   callouts (3 wide) 0.04 - 0.28   (horizontal row across bottom)
    #
    # With the recommendation strip and the scenario strip removed,
    # the right column is freed up entirely -- both charts can be
    # close to twice their previous width.
    panel_y = 0.42
    panel_h = 0.42

    # Tornado on the left (more left margin so the long y-tick driver
    # names sit cleanly inside the slide); downtime on the right.
    ax_tornado  = fig.add_axes([0.10, panel_y, 0.34, panel_h])
    ax_downtime = fig.add_axes([0.56, panel_y, 0.39, panel_h])
    render_tornado(ax_tornado, d)
    render_downtime_npv_only(ax_downtime, d)

    # Dedicated tornado legend, just below the chart's x-label.
    ax_tornado_legend = fig.add_axes([0.10, 0.31, 0.34, 0.05])
    ax_tornado_legend.axis("off")
    legend_handles = [
        mpatches.Patch(color=C_RED,   label="Unfavourable"),
        mpatches.Patch(color=C_GREEN, label="Favourable"),
    ]
    ax_tornado_legend.legend(handles=legend_handles, loc="center",
                             ncol=2, fontsize=12, frameon=True,
                             framealpha=0.95)

    # Three callouts: downtime NPV hit; fiscal maintenance line;
    # execution recommendation (recovery + spare vehicle).

    # Horizontal callout row: 3 boxes wide enough that headline text
    # has visible padding from the box border (each headline is 30+
    # characters at 18pt -- 3.5-3.8 inches of text -- so the boxes
    # need to be ~4.3 inches wide for ~0.3 inches of padding per side).
    cw  = 0.326
    cgap = 0.006
    cy  = 0.04
    ch  = 0.26
    callout_x = [0.008, 0.008 + cw + cgap, 0.008 + 2 * (cw + cgap)]

    add_callout_box(
        fig, callout_x[0], cy, cw, ch,
        headline="10% downtime\n=  -\u00a3390 k NPV",
        sub="impact on NPV for an unplanned\ndowntime of 10% each year",
        color=C_BLUE_DARKEST,
    )
    add_callout_box(
        fig, callout_x[1], cy, cw, ch,
        headline="~\u00a320k yearly maintenance",
        sub="maintenance is a small share of\nthe \u00a3538k OPEX",
        color=C_BLUE_MID_DARK,
    )
    add_callout_box(
        fig, callout_x[2], cy, cw, ch,
        headline="Uptime is the lever",
        sub="prioritise quick-recovery protocols\n"
             "and a spare-vehicle strategy",
        color=C_BLUE_MID,
    )


def make_slide_2(d: dict) -> None:
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), facecolor=C_BG)
    _draw_slide_2(fig, d)
    plt.savefig(SLIDES / "slide_2.pdf", facecolor=C_BG)
    plt.savefig(SLIDES / "slide_2.png", dpi=180, facecolor=C_BG)
    plt.close()


# ---------------------------------------------------------------------
#  SLIDE 3  --  Key model assumptions
# ---------------------------------------------------------------------

def _draw_slide_3(fig, d: dict) -> None:
    """Bullet list of principal drivers (matches ``_generate_financial_model.py``)."""
    add_title_strip(
        fig,
        title="Key model assumptions",
        subtitle="Harry Emes  |  Single-source driver set (Python)",
    )

    def _bullets_in_ax(ax, items: list[str], wrap_width: int) -> None:
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        y = 0.98
        for raw in items:
            block = textwrap.fill(
                "\u2022  " + raw,
                width=wrap_width,
                break_long_words=False,
            )
            ax.text(
                0.02, y, block,
                ha="left", va="top",
                fontsize=12.5, color="black",
                transform=ax.transAxes,
                linespacing=1.28,
            )
            lines = block.count("\n") + 1
            y -= 0.028 * lines + 0.045

    left = [
        "Utilisation ramp: 40 -> 220 sold test-days/yr; fleet 1 -> 2 (Y3) -> 3 (Y5) vehicles.",
        "Blended day rate \u00a37.5k -> \u00a39.5k (packaging/mix uplift + inflation path).",
        "Variable cost \u00a32.3k\u2013\u00a32.5k per test-day (consumables, crew T&S, wear).",
        "Unit economics: CAC \u00a312k; 3-yr customer life; 70% gross margin for LTV/CAC.",
    ]
    right = [
        "CAPEX: \u00a3310k per new vehicle + \u00a350k one-off Y1 setup; 5-yr straight-line depreciation; no debt.",
        "Fixed OPEX: Y1 base ~\u00a3538k + phased headcount adds; 3%/yr inflation on that stack and on variable \u00a3/day.",
        "Funding: \u00a31.0M seed (Y1) + \u00a31.5M Series A (Y3); UK corp. tax 19% on positive EBIT.",
        "NPV/IRR: pre-equity free cash flows; headline hurdle 20%; terminal = 2.5\u00d7 Y5 revenue (peer median).",
        "Downtime stress: same % loss on billable days every forecast year vs base; fixed OPEX unchanged.",
    ]

    # Two clipped axes with a clear gutter so wrapped lines cannot collide.
    ax_left = fig.add_axes([0.055, 0.10, 0.43, 0.76])
    ax_right = fig.add_axes([0.525, 0.10, 0.415, 0.76])
    _bullets_in_ax(ax_left, left, wrap_width=40)
    _bullets_in_ax(ax_right, right, wrap_width=38)

    add_footer_strip(
        fig,
        text="Assumptions are inputs \u2014 sensitivities (slides 1\u20132) show robustness",
        secondary="Regenerate: python _generate_financial_model.py  then  python _generate_slides.py",
    )


def make_slide_3(d: dict) -> None:
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), facecolor=C_BG)
    _draw_slide_3(fig, d)
    plt.savefig(SLIDES / "slide_3.pdf", facecolor=C_BG)
    plt.savefig(SLIDES / "slide_3.png", dpi=180, facecolor=C_BG)
    plt.close()


# ---------------------------------------------------------------------
#  Combined multi-page PDF (for one-file delivery)
# ---------------------------------------------------------------------

def make_combined_pdf(d: dict) -> None:
    """Single PDF containing slides 1\u20133 (shared draw helpers)."""
    from matplotlib.backends.backend_pdf import PdfPages
    out = SLIDES / "slides_combined.pdf"
    with PdfPages(out) as pdf:
        fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), facecolor=C_BG)
        _draw_slide_1(fig, d)
        pdf.savefig(fig, facecolor=C_BG)
        plt.close()

        fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), facecolor=C_BG)
        _draw_slide_2(fig, d)
        pdf.savefig(fig, facecolor=C_BG)
        plt.close()

        fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), facecolor=C_BG)
        _draw_slide_3(fig, d)
        pdf.savefig(fig, facecolor=C_BG)
        plt.close()


def main() -> None:
    d = load()
    make_slide_1(d)
    make_slide_2(d)
    make_slide_3(d)
    make_combined_pdf(d)
    print("Slides written to", SLIDES)
    for f in sorted(SLIDES.iterdir()):
        print("  -", f.name)


if __name__ == "__main__":
    main()
