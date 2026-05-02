"""Figure generator for the AEB Rabbit Financial Evaluation chapter.

Reads financial_model.json and produces every figure used in main.tex.
Focused on the financial-evaluation lens: cost structure, revenue
ramp, CAPEX inversion, cash waterfall, break-even, tornado
sensitivity, scenario comparison, NPV vs discount rate, and downtime
sensitivity.

Run from this directory:
    python _generate_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

HERE = Path(__file__).parent
FIG  = HERE / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size":         9,
    "axes.titlesize":    10,
    "axes.labelsize":    9,
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "legend.fontsize":   8,
    "savefig.dpi":       220,
    "savefig.bbox":      "tight",
    "axes.grid":         True,
    "grid.alpha":        0.3,
    "grid.linestyle":    "--",
})

# ---------- colour palette (colour-blind-safe-ish) ---------------
C_BRAND   = "#0B3D91"
C_ACCENT  = "#F39C12"
C_GREEN   = "#2E8B57"
C_RED     = "#C0392B"
C_GREY    = "#7F8C8D"
C_LIGHT   = "#D5DBDB"


def load() -> dict:
    return json.loads((HERE / "financial_model.json").read_text())


# =================================================================
#  1. Cost structure (Y1 capex + opex) -- donut
# =================================================================

def fig_cost_structure(d: dict) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4))

    cx = d["capex_per_vehicle"]
    cx_labels = list(cx.keys()) + ["Y1 workshop / data platform"]
    cx_values = list(cx.values()) + [d["office_setup_y1"]]
    cx_labels = [l.replace("\\&", "&").replace("\\pounds", "£") for l in cx_labels]
    colors1 = plt.cm.Blues(np.linspace(0.4, 0.9, len(cx_values)))
    ax1.pie(cx_values, labels=cx_labels, autopct="%.0f%%",
            colors=colors1, wedgeprops=dict(width=0.45),
            textprops=dict(fontsize=7))
    ax1.set_title(f"Y1 CAPEX build-up  (£{sum(cx_values)/1000:.0f}k)",
                  fontweight="bold")

    ox = d["fixed_opex_y1"]
    ox_labels = [l.replace("\\&", "&").replace("\\pounds", "£")
                 .replace("\\%", "%") for l in ox.keys()]
    ox_values = list(ox.values())
    colors2 = plt.cm.Oranges(np.linspace(0.3, 0.9, len(ox_values)))
    ax2.pie(ox_values, labels=ox_labels, autopct="%.0f%%",
            colors=colors2, wedgeprops=dict(width=0.45),
            textprops=dict(fontsize=6))
    ax2.set_title(f"Y1 fixed OPEX build-up  (£{sum(ox_values)/1000:.0f}k)",
                  fontweight="bold")

    plt.tight_layout()
    plt.savefig(FIG / "cost_structure.pdf")
    plt.close()


# =================================================================
#  2. Revenue ramp + stacked gross profit
# =================================================================

def fig_revenue_ramp(d: dict) -> None:
    years  = d["years"]
    rev    = d["pnl"]["Revenue (\\pounds k)"]
    vcost  = [-v for v in d["pnl"]["Variable cost (\\pounds k)"]]
    fixed  = [-v for v in d["pnl"]["Fixed opex (\\pounds k)"]]
    dep    = [-v for v in d["pnl"]["Depreciation (\\pounds k)"]]
    net    = d["pnl"]["Net profit (\\pounds k)"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(years))
    w = 0.35

    ax.bar(x - w/2, rev, w, label="Revenue", color=C_BRAND)
    ax.bar(x + w/2, vcost, w, label="Variable cost", color=C_ACCENT)
    ax.bar(x + w/2, fixed, w, bottom=vcost, label="Fixed opex", color=C_GREY)
    ax.bar(x + w/2, dep,   w, bottom=[a+b for a,b in zip(vcost, fixed)],
           label="Depreciation", color=C_LIGHT)

    ax2 = ax.twinx()
    ax2.plot(x, net, color=C_RED, marker="o", linewidth=2, label="Net profit")
    ax2.axhline(0, color=C_RED, linestyle=":", linewidth=1)
    ax2.set_ylabel("Net profit (£k)", color=C_RED)
    ax2.tick_params(axis="y", labelcolor=C_RED)

    ax.set_xticks(x)
    ax.set_xticklabels([f"Y{y}" for y in years])
    ax.set_ylabel("£k")
    ax.set_title("Revenue, cost stack and net profit, five-year plan",
                 fontweight="bold")
    ax.legend(loc="upper left")
    ax2.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(FIG / "revenue_ramp.pdf")
    plt.close()


# =================================================================
#  3. CAPEX inversion -- cumulative capex vs cumulative revenue
# =================================================================

def fig_capex_inversion(d: dict) -> None:
    inv = d["capex_inversion"]
    years = inv["years"]
    cum_capex = inv["cum_capex_k"]
    cum_rev   = inv["cum_rev_k"]
    annual_capex = inv["annual_capex_k"]
    annual_rev   = inv["annual_rev_k"]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))

    # Left: annual bars
    x = np.arange(len(years))
    w = 0.35
    ax.bar(x - w/2, annual_capex, w, color=C_RED, label="Annual CAPEX")
    ax.bar(x + w/2, annual_rev,   w, color=C_GREEN, label="Annual revenue")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Y{y}" for y in years])
    ax.set_ylabel("£k")
    ax.set_title("Annual CAPEX out vs. revenue in",
                 fontweight="bold")
    ax.legend()

    # Right: cumulative
    ax2.plot(years, cum_capex, color=C_RED, marker="o", linewidth=2,
             label="Cumulative CAPEX")
    ax2.plot(years, cum_rev,   color=C_GREEN, marker="s", linewidth=2,
             label="Cumulative revenue")
    ax2.fill_between(years, cum_capex, cum_rev,
                     where=[r < c for r, c in zip(cum_rev, cum_capex)],
                     color=C_RED, alpha=0.12, label="Capex > Revenue (TaaS burden)")
    ax2.fill_between(years, cum_capex, cum_rev,
                     where=[r >= c for r, c in zip(cum_rev, cum_capex)],
                     color=C_GREEN, alpha=0.12, label="Revenue > Capex (recouped)")
    if inv["crossover_year"] is not None:
        ax2.axvline(inv["crossover_year"], color="black", linestyle=":",
                    linewidth=1.2)
        ax2.annotate(f"Crossover: Y{inv['crossover_year']}",
                     (inv["crossover_year"], max(cum_capex + cum_rev) * 0.9),
                     fontsize=8, ha="left", fontweight="bold")
    ax2.set_xticks(years)
    ax2.set_xticklabels([f"Y{y}" for y in years])
    ax2.set_ylabel("Cumulative £k")
    ax2.set_title("Cumulative CAPEX vs. cumulative revenue",
                  fontweight="bold")
    ax2.legend(loc="lower right", fontsize=7)

    plt.tight_layout()
    plt.savefig(FIG / "capex_inversion.pdf")
    plt.close()


# =================================================================
#  4. Cash waterfall: FCF + equity rounds + cumulative cash
# =================================================================

def fig_cash_waterfall(d: dict) -> None:
    years = d["years"]
    cf    = d["cash_flow"]
    fcf        = cf["Free cash flow (\\pounds k)"]
    equity     = cf["+ Equity raised (\\pounds k)"]
    cumulative = cf["Cumulative cash (\\pounds k)"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(years))

    colors = [C_GREEN if v >= 0 else C_RED for v in fcf]
    ax.bar(x, fcf, 0.6, color=colors, label="Free cash flow")
    ax.bar(x, equity, 0.6, bottom=fcf, color=C_BRAND, label="Equity raised")

    ax.plot(x, cumulative, color="black", marker="s", linewidth=2,
            label="Cumulative cash (end of year)")
    ax.axhline(0, color="black", linewidth=0.7)

    for i, (f, e) in enumerate(zip(fcf, equity)):
        if abs(e) > 10:
            ax.annotate(f"+£{e:,.0f}k (round)",
                        xy=(i, f + e),
                        xytext=(0, 6), textcoords="offset points",
                        ha="center", fontsize=7, color=C_BRAND,
                        fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"Y{y}" for y in years])
    ax.set_ylabel("£k")
    ax.set_title("Annual free cash flow, equity rounds, and cumulative cash",
                 fontweight="bold")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(FIG / "cash_waterfall.pdf")
    plt.close()


# =================================================================
#  5. Break-even curve
# =================================================================

def fig_break_even(d: dict) -> None:
    be_days  = d["break_even"]["be_curve_days"]
    be_prof  = d["break_even"]["be_curve_profit_gbp"]
    be_point = d["break_even"]["break_even_days_y2"]
    util_y1_y5 = d["utilisation_days"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    prof_k = [p / 1000 for p in be_prof]
    ax.plot(be_days, prof_k, color=C_BRAND, linewidth=2,
            label="Annual EBIT (Y2 cost base)")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(be_point, color=C_RED, linestyle="--", linewidth=1.5,
               label=f"Break-even = {be_point:.0f} days/yr")

    for i, d_i in enumerate(util_y1_y5, start=1):
        y_val_k = (d_i * (d["blended_day_rate"][i-1] - d["variable_cost_per_day"][i-1])
                   - d["break_even"]["fixed_plus_dep_y2"]) / 1000
        ax.scatter(d_i, y_val_k, color=C_ACCENT, s=60, zorder=5)
        ax.annotate(f"Y{i}\n({d_i} days)", (d_i, y_val_k),
                    xytext=(5, 5), textcoords="offset points",
                    fontsize=7, color=C_ACCENT, fontweight="bold")

    ax.set_xlabel("Test days sold per year")
    ax.set_ylabel("Annual EBIT (£k) -- at Y2 cost base")
    ax.set_title("Break-even: EBIT vs. utilisation (Y2 fixed-cost base)",
                 fontweight="bold")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(FIG / "break_even.pdf")
    plt.close()


# =================================================================
#  6. Tornado sensitivity
# =================================================================

def fig_tornado(d: dict) -> None:
    s = d["sensitivity"]
    drivers = s["Driver"]
    base    = s["Base EBIT (\\pounds k)"][0]
    low     = s["Low EBIT (\\pounds k)"]
    high    = s["High EBIT (\\pounds k)"]
    swing   = [abs(h - l) for h, l in zip(high, low)]

    order = np.argsort(swing)[::-1]
    drivers = [drivers[i] for i in order]
    low     = [low[i] for i in order]
    high    = [high[i] for i in order]

    y = np.arange(len(drivers))
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.barh(y, [l - base for l in low],  color=C_RED,  label="-20% (unfavourable)")
    ax.barh(y, [h - base for h in high], color=C_GREEN, label="+20% (favourable)")
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(drivers)
    ax.invert_yaxis()
    ax.set_xlabel("Swing in Y3 EBIT vs. base (£k)")
    ax.set_title(f"Tornado sensitivity -- Y3 EBIT (base = £{base:,.0f}k)",
                 fontweight="bold")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(FIG / "tornado.pdf")
    plt.close()


# =================================================================
#  7. Scenario comparison
# =================================================================

def fig_scenarios(d: dict) -> None:
    years = d["years"]
    s = d["scenarios"]
    fig, ax = plt.subplots(figsize=(8, 4.5))

    ax.plot(years, s["bull"]["net_profit"], marker="^", linewidth=2,
            color=C_GREEN, label="Bull")
    ax.plot(years, s["base"]["net_profit"], marker="o", linewidth=2,
            color=C_BRAND, label="Base")
    ax.plot(years, s["bear"]["net_profit"], marker="v", linewidth=2,
            color=C_RED,   label="Bear")

    ax.axhline(0, color="black", linewidth=0.7)
    ax.fill_between(years, s["bear"]["net_profit"], s["bull"]["net_profit"],
                    color=C_GREY, alpha=0.15, label="Bear-to-bull range")
    ax.set_xticks(years)
    ax.set_xticklabels([f"Y{y}" for y in years])
    ax.set_ylabel("Net profit (£k)")
    ax.set_title("Scenario analysis -- five-year net profit trajectory",
                 fontweight="bold")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(FIG / "scenarios.pdf")
    plt.close()


# =================================================================
#  8. NPV vs discount rate (IRR crossover)
# =================================================================

def fig_npv_curve(d: dict) -> None:
    npv = d["npv"]
    rates = np.array(npv["npv_curve_rates"])
    values = np.array(npv["npv_curve_k"])
    irr = npv["irr"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(rates * 100, values, color=C_BRAND, linewidth=2,
            label="Project NPV")
    ax.axhline(0, color="black", linewidth=0.7)

    for r, style, label in [(0.10, ":", "10% (low hurdle)"),
                            (0.20, "--", "20% (VC central)"),
                            (0.30, ":", "30% (high hurdle)")]:
        v = values[np.argmin(np.abs(rates - r))]
        ax.axvline(r * 100, color=C_GREY, linestyle=style, linewidth=1)
        ax.scatter(r * 100, v, color=C_ACCENT, s=40, zorder=5)
        ax.annotate(f"{label}\n£{v:,.0f}k",
                    (r * 100, v), xytext=(6, 6),
                    textcoords="offset points", fontsize=7,
                    color=C_ACCENT, fontweight="bold")

    ax.axvline(irr * 100, color=C_RED, linestyle="--", linewidth=1.5,
               label=f"IRR = {irr*100:.1f}%")
    ax.set_xlabel("Discount rate (%)")
    ax.set_ylabel("Project NPV (£k)")
    ax.set_title("NPV vs. discount rate (5-yr FCF + terminal value)",
                 fontweight="bold")
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(FIG / "npv_curve.pdf")
    plt.close()


# =================================================================
#  9. Downtime sensitivity
# =================================================================

def fig_downtime(d: dict) -> None:
    dt = d["downtime_sensitivity"]
    pct = dt["Downtime (\\%)"]
    y3_ebit = dt["Y3 EBIT (\\pounds k)"]
    y5_ebit = dt["Y5 EBIT (\\pounds k)"]
    npv20   = dt["NPV@20\\% (\\pounds k)"]
    y5_rev  = dt["Y5 revenue (\\pounds k)"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    # EBIT trajectory
    ax1.plot(pct, y3_ebit, marker="o", color=C_RED, linewidth=2,
             label="Y3 EBIT")
    ax1.plot(pct, y5_ebit, marker="s", color=C_GREEN, linewidth=2,
             label="Y5 EBIT")
    ax1.axhline(0, color="black", linewidth=0.7)
    ax1.fill_between(pct, y3_ebit, y5_ebit, color=C_GREY, alpha=0.15)
    ax1.set_xlabel("Unplanned downtime (% of planned test days)")
    ax1.set_ylabel("EBIT (£k)")
    ax1.set_title("EBIT vs. downtime (Y3 \u0026 Y5)",
                  fontweight="bold")
    ax1.legend(loc="upper right")

    # NPV and Y5 revenue trajectory
    ax2.plot(pct, npv20, marker="o", color=C_BRAND, linewidth=2,
             label="NPV @ 20%")
    ax2.axhline(0, color="black", linewidth=0.7)
    ax2b = ax2.twinx()
    ax2b.plot(pct, y5_rev, marker="s", color=C_ACCENT, linewidth=1.8,
              linestyle="--", label="Y5 revenue")
    ax2b.set_ylabel("Y5 revenue (£k)", color=C_ACCENT)
    ax2b.tick_params(axis="y", labelcolor=C_ACCENT)
    ax2.set_xlabel("Unplanned downtime (% of planned test days)")
    ax2.set_ylabel("NPV @ 20% (£k)", color=C_BRAND)
    ax2.tick_params(axis="y", labelcolor=C_BRAND)
    ax2.set_title("NPV and Y5 revenue vs. downtime",
                  fontweight="bold")
    ax2.legend(loc="upper left")
    ax2b.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(FIG / "downtime.pdf")
    plt.close()


# =================================================================
# MAIN
# =================================================================

def main() -> None:
    d = load()
    fig_cost_structure(d)
    fig_revenue_ramp(d)
    fig_capex_inversion(d)
    fig_cash_waterfall(d)
    fig_break_even(d)
    fig_tornado(d)
    fig_scenarios(d)
    fig_npv_curve(d)
    fig_downtime(d)
    print("All figures written to", FIG)


if __name__ == "__main__":
    main()
