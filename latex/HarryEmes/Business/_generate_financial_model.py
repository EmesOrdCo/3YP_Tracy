"""Driver-based financial model for the AEB Rabbit TaaS business.

Single source of truth for every number used in Harry Emes' Financial
Evaluation chapter. Models a Testing-as-a-Service (TaaS) /
Product-Service-System (PSS) business where the operator retains
ownership of the test-vehicle fleet and sells test-days to AV
developers, with revenue tethered to fleet utilisation.

Produces:
    * financial_model.json  -- machine-readable outputs consumed by figure script
    * tables/*.tex          -- LaTeX table fragments consumed by main.tex
    * report_numbers.tex    -- \\newcommand macros for inline numbers in prose

Run from this directory:
    python _generate_financial_model.py
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


HERE = Path(__file__).parent
TABLES_DIR = HERE / "tables"
TABLES_DIR.mkdir(exist_ok=True)


# ====================================================================
#  DRIVERS  --  every "assumption" in the chapter lives here
# ====================================================================

YEARS = [1, 2, 3, 4, 5]
N_YEARS = len(YEARS)

# --- Demand-side drivers -----------------------------------------
# Test days sold per year. Y1 is a pilot year; ramp follows Toby's
# phased targeting (EV startups -> AI firms -> OEMs).
UTILISATION_DAYS = [40, 70, 110, 150, 220]

# Fleet size (number of active test vehicles). 2nd vehicle added Y3,
# 3rd vehicle Y5 once bookings exceed ~150 days/yr per vehicle.
FLEET_SIZE = [1, 1, 2, 2, 3]

# Blended day rate (£). Rises with (a) repeat-customer uplift,
# (b) move from Bronze toward Silver/Gold packaging, (c) inflation.
BLENDED_DAY_RATE = [7_500, 8_000, 8_500, 9_000, 9_500]

# Per-day variable cost (£): tyres, consumables, transport fuel,
# crew T&S, amortised vehicle wear.
VARIABLE_COST_PER_DAY = [2_300, 2_350, 2_400, 2_450, 2_500]

# --- Capex drivers -----------------------------------------------
# Per-vehicle capex (£). Re-used each time fleet grows.
CAPEX_PER_VEHICLE = {
    "Vehicle build (chassis, powertrain, aero)": 180_000,
    "Data acquisition \\& instrumentation":        60_000,
    "Safety \\& emergency redundancy systems":     25_000,
    "Trailer \\& transport rig":                  30_000,
    "Spares, tooling \\& initial tyre stock":      15_000,
}
CAPEX_PER_VEHICLE_TOTAL = sum(CAPEX_PER_VEHICLE.values())  # £310k

# One-off Y1 company set-up capex (£).
OFFICE_SETUP_Y1 = {
    "Workshop fit-out \\& office setup": 35_000,
    "Data platform \\& analytics stack": 15_000,
}
OFFICE_SETUP_Y1_TOTAL = sum(OFFICE_SETUP_Y1.values())  # £50k

CAPEX_DEPRECIATION_YEARS = 5       # straight-line

# --- Fixed opex (Y1 baseline; scales with headcount + inflation) ----
FIXED_OPEX_Y1 = {
    "CEO / Commercial Director (1 FTE)":           75_000,
    "Operations Manager / Lead Engineer (1 FTE)":  60_000,
    "Test Engineer (2 FTE @ \\pounds50k)":         100_000,
    "Data \\& Software Engineer (1 FTE)":          60_000,
    "Admin \\& finance (0.3 FTE)":                 15_000,
    "Employer NI \\& benefits (20\\% of salary)":  62_000,
    "Workshop \\& office rent (UK regional)":      36_000,
    "Insurance (public, product, vehicle)":        40_000,
    "Certification \\& standards fees":            10_000,
    "Marketing \\& business development":          30_000,
    "Software, IT \\& data platform hosting":      15_000,
    "Vehicle maintenance contract":                20_000,
    "Professional services (legal, audit, R\\&D)": 15_000,
}
FIXED_OPEX_Y1_TOTAL = sum(FIXED_OPEX_Y1.values())  # ~£538k

# Headcount additions by year (cost added to the fixed opex base).
HEADCOUNT_ADDITIONS_COST = {
    1: 0,
    2: 60_000,          # +1 commercial/BD exec
    3: 55_000,          # +1 test engineer for 2nd vehicle
    4: 110_000,         # +1 engineer, +1 marketing
    5: 110_000,         # +2 engineers for 3rd vehicle
}

INFLATION_RATE = 0.03  # applied to fixed opex and variable cost

# --- Y6–Y10 extension (VC horizon; five-year chapter unchanged) ----------
# Extrapolates sold test-days and pricing after the published Y5 plan.
# Fleet remains 3 vehicles; no further vehicle capex; no new equity rounds.
# Sold days Y6–Y10: compound growth (not linear): D[y] = round(D[y-1]*(1+g)).
Y6_10_UTILISATION_CAGR = 0.12     # annual compound growth on total sold test-days
Y6_10_BLENDED_RATE_STEP = 200     # £/year on blended day rate
Y6_10_VARIABLE_COST_STEP = 50     # £/day per year (consumables + inflation)
MAX_BLENDED_DAY_RATE_Y10 = 12_000  # cap near Gold-tier ceiling

# --- Pricing benchmarks (for pricing-strategy table) -----------------
PRICING_BENCHMARKS = [
    # (competitor,            typical day-rate £,  positioning)
    ("AB Dynamics (ADAS test robots + engineer)", "8,000--12,000",  "Premium, automated"),
    ("UTAC proving-ground hire (Millbrook, Leyland)", "5,000--9,000",   "Facility-led, inflexible"),
    ("HORIBA / AVL dynamometer laboratory",           "4,000--6,500",   "Controlled, not on-track"),
    ("In-house OEM test team (fully-loaded)",         "12,000+",        "Captive, not available to 3rd parties"),
    ("AEB Rabbit TaaS: Bronze package",               "6,000",          "Vehicle hire, customer-crewed"),
    ("AEB Rabbit TaaS: Silver package",               "8,000",          "Vehicle + test engineer"),
    ("AEB Rabbit TaaS: Gold package",                 "10,000",         "Vehicle + 2 engineers + data package"),
]

# --- Unit-economics assumptions -------------------------------------
CAC = 12_000   # average customer acquisition cost (£) -- conferences + outbound
AVG_REVENUE_PER_CUSTOMER_PER_YEAR = 60_000   # 6-10 test days per customer
CUSTOMER_LIFETIME_YEARS = 3
CONTRACT_GROSS_MARGIN = 0.70   # revenue-weighted average
LTV = (
    AVG_REVENUE_PER_CUSTOMER_PER_YEAR * CUSTOMER_LIFETIME_YEARS * CONTRACT_GROSS_MARGIN
)
LTV_CAC = LTV / CAC
PAYBACK_MONTHS = CAC / (AVG_REVENUE_PER_CUSTOMER_PER_YEAR * CONTRACT_GROSS_MARGIN / 12)

# --- Funding strategy ------------------------------------------------
SEED_ROUND = 1_000_000     # Y1
SERIES_A_ROUND = 1_500_000 # Y3 when expanding to 2nd vehicle + sales scale
TOTAL_RAISE = SEED_ROUND + SERIES_A_ROUND
SEED_EQUITY_STAKE = 0.20   # dilution at seed
SERIES_A_EQUITY_STAKE = 0.20

# --- Valuation comparable-multiples ---------------------------------
COMPARABLE_EV_REVENUE_MULTIPLES = {
    "AB Dynamics (LSE: ABDP, 2024)":     3.5,
    "Spirent Communications (LSE: SPT)": 2.2,
    "AVL List (private, Refinitiv est.)":1.8,
    "Peer-group median":                 2.5,
}


# ====================================================================
#  MODEL ENGINE
# ====================================================================

def build_capex_schedule() -> pd.DataFrame:
    """Capex cash out each year (new vehicles + one-off Y1 setup)."""
    capex = np.zeros(N_YEARS)
    capex[0] = CAPEX_PER_VEHICLE_TOTAL + OFFICE_SETUP_Y1_TOTAL  # Y1: 1 vehicle + setup
    for y in range(1, N_YEARS):
        new_vehicles = FLEET_SIZE[y] - FLEET_SIZE[y - 1]
        capex[y] = new_vehicles * CAPEX_PER_VEHICLE_TOTAL
    return pd.DataFrame({
        "Year": YEARS,
        "New vehicles purchased":      [FLEET_SIZE[0]] + [FLEET_SIZE[i] - FLEET_SIZE[i - 1] for i in range(1, N_YEARS)],
        "Vehicle capex (\\pounds k)":  [FLEET_SIZE[0] * CAPEX_PER_VEHICLE_TOTAL / 1000] +
                                        [(FLEET_SIZE[i] - FLEET_SIZE[i - 1]) * CAPEX_PER_VEHICLE_TOTAL / 1000
                                         for i in range(1, N_YEARS)],
        "Other setup capex (\\pounds k)": [OFFICE_SETUP_Y1_TOTAL / 1000]
                                        + [0] * (N_YEARS - 1),
        "Total capex (\\pounds k)":    capex / 1000,
    })


def build_depreciation_schedule(capex_df: pd.DataFrame) -> np.ndarray:
    """Straight-line depreciation. Each capex spend depreciates over
    CAPEX_DEPRECIATION_YEARS starting the year it is incurred."""
    dep = np.zeros(N_YEARS)
    capex_vec = capex_df["Total capex (\\pounds k)"].values * 1000
    for y_spent, amount in enumerate(capex_vec):
        per_year = amount / CAPEX_DEPRECIATION_YEARS
        for y_dep in range(y_spent, min(y_spent + CAPEX_DEPRECIATION_YEARS, N_YEARS)):
            dep[y_dep] += per_year
    return dep


def build_opex_schedule() -> pd.DataFrame:
    """Fixed opex by year: Y1 baseline + cumulative headcount additions,
    inflated."""
    rows = []
    cumulative_additions = 0
    for y in range(N_YEARS):
        cumulative_additions += HEADCOUNT_ADDITIONS_COST[y + 1]
        base = FIXED_OPEX_Y1_TOTAL + cumulative_additions
        inflated = base * ((1 + INFLATION_RATE) ** y)
        rows.append(inflated)
    return pd.DataFrame({
        "Year": YEARS,
        "Fixed opex (\\pounds k)": np.array(rows) / 1000,
    })


def build_revenue_schedule() -> pd.DataFrame:
    """Revenue and variable cost by year, driven by utilisation days."""
    revenue = np.array([UTILISATION_DAYS[y] * BLENDED_DAY_RATE[y]
                        for y in range(N_YEARS)])
    var_cost = np.array([UTILISATION_DAYS[y] * VARIABLE_COST_PER_DAY[y]
                         for y in range(N_YEARS)])
    return pd.DataFrame({
        "Year":                          YEARS,
        "Test days sold":                UTILISATION_DAYS,
        "Fleet size":                    FLEET_SIZE,
        "Utilisation (days/vehicle)":    [UTILISATION_DAYS[y] / FLEET_SIZE[y]
                                          for y in range(N_YEARS)],
        "Blended day rate (\\pounds)":   BLENDED_DAY_RATE,
        "Revenue (\\pounds k)":          revenue / 1000,
        "Variable cost (\\pounds k)":    var_cost / 1000,
        "Gross profit (\\pounds k)":     (revenue - var_cost) / 1000,
        "Gross margin (\\%)":            (revenue - var_cost) / revenue * 100,
    })


def build_pnl() -> pd.DataFrame:
    capex_df = build_capex_schedule()
    rev_df   = build_revenue_schedule()
    opex_df  = build_opex_schedule()
    dep      = build_depreciation_schedule(capex_df)

    revenue   = rev_df["Revenue (\\pounds k)"].values
    var_cost  = rev_df["Variable cost (\\pounds k)"].values
    gross     = rev_df["Gross profit (\\pounds k)"].values
    fixed     = opex_df["Fixed opex (\\pounds k)"].values
    depr_k    = dep / 1000
    ebitda    = gross - fixed
    ebit      = ebitda - depr_k
    # Assume no debt -> no interest. 19% UK corp tax on positive EBIT.
    tax       = np.where(ebit > 0, ebit * 0.19, 0)
    net       = ebit - tax

    return pd.DataFrame({
        "Year":                          YEARS,
        "Revenue (\\pounds k)":          revenue,
        "Variable cost (\\pounds k)":    -var_cost,
        "Gross profit (\\pounds k)":     gross,
        "Fixed opex (\\pounds k)":       -fixed,
        "EBITDA (\\pounds k)":           ebitda,
        "Depreciation (\\pounds k)":     -depr_k,
        "EBIT (\\pounds k)":             ebit,
        "Tax @ 19\\% (\\pounds k)":      -tax,
        "Net profit (\\pounds k)":       net,
    })


def build_cash_flow() -> pd.DataFrame:
    pnl_df   = build_pnl()
    capex_df = build_capex_schedule()
    net      = pnl_df["Net profit (\\pounds k)"].values
    dep      = -pnl_df["Depreciation (\\pounds k)"].values   # positive add-back
    capex    = capex_df["Total capex (\\pounds k)"].values
    ocf      = net + dep
    fcf      = ocf - capex

    equity = np.zeros(N_YEARS)
    equity[0] = SEED_ROUND / 1000          # Y1 seed
    equity[2] = SERIES_A_ROUND / 1000      # Y3 Series A

    net_cf = fcf + equity
    cumulative_cash = np.cumsum(net_cf)

    return pd.DataFrame({
        "Year":                             YEARS,
        "Net profit (\\pounds k)":          net,
        "+ Depreciation (\\pounds k)":      dep,
        "Operating cash flow (\\pounds k)": ocf,
        "- Capex (\\pounds k)":             -capex,
        "Free cash flow (\\pounds k)":      fcf,
        "+ Equity raised (\\pounds k)":     equity,
        "Net cash flow (\\pounds k)":       net_cf,
        "Cumulative cash (\\pounds k)":     cumulative_cash,
    })


def compute_break_even(pnl_df: pd.DataFrame) -> Dict:
    """Break-even in test-days/year at Y2 cost structure.

    BE days = (fixed opex + depreciation) / (day_rate - variable_cost_per_day)
    """
    fixed_y2 = -pnl_df.loc[pnl_df["Year"] == 2, "Fixed opex (\\pounds k)"].values[0] * 1000
    dep_y2   = -pnl_df.loc[pnl_df["Year"] == 2, "Depreciation (\\pounds k)"].values[0] * 1000
    contribution_per_day = BLENDED_DAY_RATE[1] - VARIABLE_COST_PER_DAY[1]
    be_days = (fixed_y2 + dep_y2) / contribution_per_day

    be_curve_days = np.arange(0, 260, 5)
    be_profit = (
        be_curve_days * (BLENDED_DAY_RATE[1] - VARIABLE_COST_PER_DAY[1])
        - (fixed_y2 + dep_y2)
    )
    return {
        "break_even_days_y2":        be_days,
        "contribution_per_day":      contribution_per_day,
        "fixed_plus_dep_y2":         fixed_y2 + dep_y2,
        "be_curve_days":             be_curve_days.tolist(),
        "be_curve_profit_gbp":       be_profit.tolist(),
    }


def run_sensitivity() -> pd.DataFrame:
    """One-at-a-time sensitivity: impact on Y3 EBIT from +/-20%
    perturbation of each key driver."""
    base_pnl = build_pnl()
    base_y3_ebit = base_pnl.loc[base_pnl["Year"] == 3, "EBIT (\\pounds k)"].values[0]

    drivers = [
        ("Utilisation days (Y3)",       "UTILISATION_DAYS",        2, 0.20),
        ("Blended day rate (Y3)",       "BLENDED_DAY_RATE",        2, 0.20),
        ("Variable cost per day (Y3)",  "VARIABLE_COST_PER_DAY",   2, 0.20),
        ("Fixed opex (all years)",      "FIXED_OPEX_Y1_TOTAL",     None, 0.20),
        ("Capex per vehicle",           "CAPEX_PER_VEHICLE_TOTAL", None, 0.20),
        ("Inflation rate",              "INFLATION_RATE",          None, 0.50),
    ]

    rows = []
    for label, var_name, idx, pct in drivers:
        low_pnl  = _rebuild_pnl_with_override(var_name, idx,  1 - pct)
        high_pnl = _rebuild_pnl_with_override(var_name, idx,  1 + pct)
        low_ebit  = low_pnl.loc[low_pnl["Year"]   == 3, "EBIT (\\pounds k)"].values[0]
        high_ebit = high_pnl.loc[high_pnl["Year"] == 3, "EBIT (\\pounds k)"].values[0]
        rows.append({
            "Driver":              label,
            "Perturbation":        f"$\\pm${int(pct*100)}\\%",
            "Low EBIT (\\pounds k)":  low_ebit,
            "Base EBIT (\\pounds k)": base_y3_ebit,
            "High EBIT (\\pounds k)": high_ebit,
            "Swing (\\pounds k)":  high_ebit - low_ebit,
        })
    df = pd.DataFrame(rows)
    df = df.sort_values("Swing (\\pounds k)", key=abs, ascending=False).reset_index(drop=True)
    return df


def _rebuild_pnl_with_override(var_name: str, idx, multiplier: float) -> pd.DataFrame:
    """Ugly but effective: hot-swap a module-level global, rebuild P&L,
    restore. Avoids wrapping the whole model in a class at this stage."""
    g = globals()
    old = g[var_name]
    try:
        if idx is None:
            g[var_name] = old * multiplier
        else:
            new_list = list(old)
            new_list[idx] = new_list[idx] * multiplier
            g[var_name] = new_list
        return build_pnl()
    finally:
        g[var_name] = old


def run_scenarios() -> Dict:
    """Base/Bull/Bear 5-year P&L comparison."""
    base_pnl = build_pnl()

    # Bull: +25% utilisation, +10% day rate, -5% variable cost
    bull_pnl = _scenario(1.25, 1.10, 0.95)
    # Bear: -30% utilisation, -10% day rate, +10% variable cost
    bear_pnl = _scenario(0.70, 0.90, 1.10)

    def extract(df: pd.DataFrame) -> Dict:
        return {
            "revenue":    df["Revenue (\\pounds k)"].tolist(),
            "ebitda":     df["EBITDA (\\pounds k)"].tolist(),
            "ebit":       df["EBIT (\\pounds k)"].tolist(),
            "net_profit": df["Net profit (\\pounds k)"].tolist(),
        }

    return {
        "base": extract(base_pnl),
        "bull": extract(bull_pnl),
        "bear": extract(bear_pnl),
    }


# --- NPV / IRR / Downtime drivers ------------------------------------

DISCOUNT_RATES = [0.10, 0.15, 0.20, 0.25, 0.30]
TERMINAL_EV_REVENUE_MULTIPLE = 2.5   # peer-group median; Y5 EV = 2.5 x Y5 revenue
DOWNTIME_SENSITIVITY_PCTS = [0, 5, 10, 15, 20, 25, 30]  # % of planned days lost


def compute_npv_irr(terminal_multiple: float = TERMINAL_EV_REVENUE_MULTIPLE
                    ) -> Dict:
    """Project NPV and IRR from a capital-budgeting perspective.

    Convention: year-end FCFs (pre-equity) are the project's free cash
    flows. Terminal value is added to Y5 at the peer-group
    EV/revenue multiple; no further year is modelled. IRR is the
    discount rate at which the sum of discounted FCFs equals zero.

    Returns a dict with NPV at each standard discount rate, IRR, and
    the Y5 terminal value used.
    """
    cash_df   = build_cash_flow()
    pnl_df    = build_pnl()
    fcf_k     = cash_df["Free cash flow (\\pounds k)"].values  # GBP k
    y5_rev    = pnl_df.loc[pnl_df["Year"] == 5, "Revenue (\\pounds k)"].values[0]
    terminal_value = y5_rev * terminal_multiple  # GBP k

    # Year-end FCFs including terminal value in Y5
    fcf_incl_tv = fcf_k.copy()
    fcf_incl_tv[-1] = fcf_incl_tv[-1] + terminal_value

    npvs = {}
    for r in DISCOUNT_RATES:
        npv = sum(fcf_incl_tv[t] / (1 + r) ** (t + 1) for t in range(N_YEARS))
        npvs[r] = npv

    # IRR via bisection on the interval [-0.9, 5.0]
    def npv_at(r):
        if r <= -1:
            return float("inf")
        return sum(fcf_incl_tv[t] / (1 + r) ** (t + 1) for t in range(N_YEARS))

    lo, hi = -0.9, 5.0
    if npv_at(lo) * npv_at(hi) > 0:
        irr = float("nan")
    else:
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if npv_at(lo) * npv_at(mid) <= 0:
                hi = mid
            else:
                lo = mid
        irr = 0.5 * (lo + hi)

    # NPV curve for plotting
    r_grid = np.linspace(-0.05, 1.0, 220)
    npv_curve = [sum(fcf_incl_tv[t] / (1 + r) ** (t + 1) for t in range(N_YEARS))
                 for r in r_grid]

    return {
        "npv_at_rate":         npvs,
        "irr":                 irr,
        "terminal_value_k":    terminal_value,
        "fcf_incl_tv_k":       fcf_incl_tv.tolist(),
        "npv_curve_rates":     r_grid.tolist(),
        "npv_curve_k":         npv_curve,
    }


def compute_year_10_projection() -> Dict:
    """Project revenue / EBIT / terminal-style EV at Y10 using extended drivers.

    The Financial Evaluation chapter remains Y1--Y5 only; this block is an
    optional **10-year lens** for investor narrative. Assumptions:

    * Sold test-day volume compounds annually after Y5:
      ``D[y] = round(D[y-1] * (1 + Y6_10_UTILISATION_CAGR))``.
    * Blended day rate rises £200/year (mix uplift + inflation), capped.
    * Variable cost per day +£50/year.
    * Fleet size 3 throughout Y6--Y10; **no** additional vehicle capex.
    * No further equity raises; headcount additions after Y5 are zero
      (only CPI on the fixed stack).

    Terminal enterprise value at Y10 uses the same peer multiple as Y5
    NPV (``TERMINAL_EV_REVENUE_MULTIPLE``) applied to **Y10 revenue** —
    illustrative only; not part of the chapter's five-year NPV.
    """
    g = globals()
    backup = {
        "UTILISATION_DAYS": list(UTILISATION_DAYS),
        "BLENDED_DAY_RATE": list(BLENDED_DAY_RATE),
        "VARIABLE_COST_PER_DAY": list(VARIABLE_COST_PER_DAY),
        "FLEET_SIZE": list(FLEET_SIZE),
        "YEARS": list(YEARS),
        "N_YEARS": N_YEARS,
        "HEADCOUNT_ADDITIONS_COST": dict(HEADCOUNT_ADDITIONS_COST),
    }

    util = backup["UTILISATION_DAYS"][:]
    rate = backup["BLENDED_DAY_RATE"][:]
    vcd = backup["VARIABLE_COST_PER_DAY"][:]
    fleet = backup["FLEET_SIZE"][:] + [3, 3, 3, 3, 3]

    for _ in range(5):
        util.append(int(round(util[-1] * (1 + Y6_10_UTILISATION_CAGR))))
        nr = rate[-1] + Y6_10_BLENDED_RATE_STEP
        rate.append(min(nr, MAX_BLENDED_DAY_RATE_Y10))
        vcd.append(vcd[-1] + Y6_10_VARIABLE_COST_STEP)

    hc = dict(HEADCOUNT_ADDITIONS_COST)
    for k in range(6, 11):
        hc[k] = 0

    try:
        g["UTILISATION_DAYS"] = util
        g["BLENDED_DAY_RATE"] = rate
        g["VARIABLE_COST_PER_DAY"] = vcd
        g["FLEET_SIZE"] = fleet
        g["YEARS"] = list(range(1, 11))
        g["N_YEARS"] = 10
        g["HEADCOUNT_ADDITIONS_COST"] = hc

        pnl = build_pnl()
        rev_df = build_revenue_schedule()

        y10_rev_k = float(
            pnl.loc[pnl["Year"] == 10, "Revenue (\\pounds k)"].values[0]
        )
        y10_ebit_k = float(
            pnl.loc[pnl["Year"] == 10, "EBIT (\\pounds k)"].values[0]
        )
        y10_net_k = float(
            pnl.loc[pnl["Year"] == 10, "Net profit (\\pounds k)"].values[0]
        )
        terminal_ev_y10_k = y10_rev_k * TERMINAL_EV_REVENUE_MULTIPLE
        days_y10 = util[-1]
        rate_y10 = rate[-1]
        days_per_vehicle_y10 = days_y10 / fleet[-1]

        return {
            "assumptions_summary": (
                "Y6–Y10: fleet fixed at 3 vehicles; sold test-days grow "
                f"compounding {Y6_10_UTILISATION_CAGR:.0%}/yr after Y5; "
                "blended rate +£200/yr (capped £12k); variable cost/day +£50/yr; "
                "no new capex or equity; headcount adds only through Y5."
            ),
            "y6_10_utilisation_cagr": Y6_10_UTILISATION_CAGR,
            "year_10_revenue_k": y10_rev_k,
            "year_10_ebit_k": y10_ebit_k,
            "year_10_net_profit_k": y10_net_k,
            "year_10_total_test_days_sold": days_y10,
            "year_10_blended_day_rate": rate_y10,
            "year_10_days_per_vehicle": round(days_per_vehicle_y10, 1),
            "terminal_ev_revenue_multiple": TERMINAL_EV_REVENUE_MULTIPLE,
            "year_10_terminal_enterprise_value_k": terminal_ev_y10_k,
            "extended_utilisation_days_y1_y10": util,
            "extended_blended_day_rate_y1_y10": rate,
        }
    finally:
        for k, v in backup.items():
            g[k] = v


def run_downtime_sensitivity() -> pd.DataFrame:
    """Sensitivity of Y3 and Y5 EBIT / NPV to unplanned downtime.

    Downtime is modelled as a fractional reduction in utilisation days
    (maintenance/recovery failures directly erode billable days). The
    variable cost per day is unchanged (we assume we still incur the
    crew-standing-down cost on a downtime day), so EBIT drops by the
    full gross-profit-per-day times lost days.
    """
    rows = []
    for pct in DOWNTIME_SENSITIVITY_PCTS:
        factor = 1 - pct / 100.0
        # Apply downtime as a utilisation multiplier.
        g = globals()
        util_old = list(UTILISATION_DAYS)
        try:
            g["UTILISATION_DAYS"] = [int(round(d * factor)) for d in util_old]
            pnl = build_pnl()
            npv_irr = compute_npv_irr()
        finally:
            g["UTILISATION_DAYS"] = util_old

        y3_ebit = pnl.loc[pnl["Year"] == 3, "EBIT (\\pounds k)"].values[0]
        y5_ebit = pnl.loc[pnl["Year"] == 5, "EBIT (\\pounds k)"].values[0]
        y5_rev  = pnl.loc[pnl["Year"] == 5, "Revenue (\\pounds k)"].values[0]
        npv_20  = npv_irr["npv_at_rate"][0.20]
        rows.append({
            "Downtime (\\%)":                   pct,
            "Effective Y1 days":               max(int(round(UTILISATION_DAYS[0] * factor)), 0),
            "Effective Y5 days":               max(int(round(UTILISATION_DAYS[4] * factor)), 0),
            "Y3 EBIT (\\pounds k)":            y3_ebit,
            "Y5 EBIT (\\pounds k)":            y5_ebit,
            "Y5 revenue (\\pounds k)":         y5_rev,
            "NPV@20\\% (\\pounds k)":          npv_20,
        })
    return pd.DataFrame(rows)


def compute_capex_inversion() -> Dict:
    """CAPEX / cumulative-revenue series used to visualise the TaaS
    capex-inversion narrative: in a TaaS model the operator absorbs
    the capex before any billable hour, so cumulative capex leads
    cumulative revenue for several years."""
    cash_df = build_cash_flow()
    rev_df  = build_revenue_schedule()
    capex_k = (-cash_df["- Capex (\\pounds k)"].values)
    rev_k   = rev_df["Revenue (\\pounds k)"].values
    cum_capex = np.cumsum(capex_k)
    cum_revenue = np.cumsum(rev_k)
    crossover_year = None
    for t in range(N_YEARS):
        if cum_revenue[t] >= cum_capex[t]:
            crossover_year = YEARS[t]
            break
    return {
        "years":          YEARS,
        "annual_capex_k": capex_k.tolist(),
        "annual_rev_k":   rev_k.tolist(),
        "cum_capex_k":    cum_capex.tolist(),
        "cum_rev_k":      cum_revenue.tolist(),
        "crossover_year": crossover_year,
    }


def _scenario(util_mult: float, rate_mult: float, varcost_mult: float) -> pd.DataFrame:
    g = globals()
    util_old = list(UTILISATION_DAYS)
    rate_old = list(BLENDED_DAY_RATE)
    vc_old   = list(VARIABLE_COST_PER_DAY)
    try:
        g["UTILISATION_DAYS"]      = [int(d * util_mult)  for d in util_old]
        g["BLENDED_DAY_RATE"]      = [int(r * rate_mult)  for r in rate_old]
        g["VARIABLE_COST_PER_DAY"] = [int(c * varcost_mult) for c in vc_old]
        return build_pnl()
    finally:
        g["UTILISATION_DAYS"]      = util_old
        g["BLENDED_DAY_RATE"]      = rate_old
        g["VARIABLE_COST_PER_DAY"] = vc_old


# ====================================================================
#  LATEX EMISSION
# ====================================================================

def _fmt(x: float, decimals: int = 0, bold_if_neg: bool = False) -> str:
    if pd.isna(x):
        return "--"
    if decimals == 0:
        s = f"{x:,.0f}"
    else:
        s = f"{x:,.{decimals}f}"
    if bold_if_neg and x < 0:
        return f"\\textcolor{{red}}{{{s}}}"
    return s


def write_table_capex(df: pd.DataFrame) -> None:
    veh_col = "Vehicle capex (\\pounds k)"
    oth_col = "Other setup capex (\\pounds k)"
    tot_col = "Total capex (\\pounds k)"
    rows = []
    for _, row in df.iterrows():
        year = int(row["Year"])
        n_veh = int(row["New vehicles purchased"])
        veh = _fmt(row[veh_col])
        oth = _fmt(row[oth_col])
        tot = _fmt(row[tot_col])
        rows.append(f"{year} & {n_veh} & {veh} & {oth} & \\textbf{{{tot}}} \\\\")
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Five-year capex schedule (\\pounds k). Per-vehicle build costs 
\\pounds{CAPEX_PER_VEHICLE_TOTAL/1000:.0f}k (see Table~\\ref{{tab:capex_breakdown}}); 
one-off Y1 company setup \\pounds{OFFICE_SETUP_Y1_TOTAL/1000:.0f}k.}}
\\label{{tab:capex_schedule}}
\\begin{{tabular}}{{cccccc}}
\\toprule
\\textbf{{Year}} & \\textbf{{New vehicles}} & \\textbf{{Vehicle capex}} & \\textbf{{Other capex}} & \\textbf{{Total}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "capex_schedule.tex").write_text(tex)


def write_table_capex_breakdown() -> None:
    rows = [f"{k} & {v/1000:,.0f} \\\\" for k, v in CAPEX_PER_VEHICLE.items()]
    rows.append(f"\\midrule\n\\textbf{{Total per vehicle}} & \\textbf{{{CAPEX_PER_VEHICLE_TOTAL/1000:,.0f}}} \\\\")
    rows.append(f"\\midrule")
    for k, v in OFFICE_SETUP_Y1.items():
        rows.append(f"{k} (Y1 only) & {v/1000:,.0f} \\\\")
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Per-vehicle capex build-up and Y1 one-off setup. Figures are 
internal team estimates benchmarked against published Formula Student cost 
reports and published industrial-test-rig build quotes.}}
\\label{{tab:capex_breakdown}}
\\begin{{tabular}}{{lr}}
\\toprule
\\textbf{{Line item}} & \\textbf{{Cost (\\pounds k)}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "capex_breakdown.tex").write_text(tex)


def write_table_opex_breakdown() -> None:
    rows = [f"{k} & {v/1000:,.0f} \\\\" for k, v in FIXED_OPEX_Y1.items()]
    rows.append(f"\\midrule\n\\textbf{{Total fixed opex, Y1}} & \\textbf{{{FIXED_OPEX_Y1_TOTAL/1000:,.0f}}} \\\\")
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Year-1 fixed opex build-up (\\pounds k). Salaries benchmarked 
against 2026 Gradcracker/Reed automotive-engineering bands for UK regional 
centres; workshop rent from 2024 average Oxford-Didcot light-industrial 
rates.}}
\\label{{tab:opex_breakdown}}
\\begin{{tabular}}{{lr}}
\\toprule
\\textbf{{Line item}} & \\textbf{{Cost (\\pounds k)}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "opex_breakdown.tex").write_text(tex)


def write_table_pricing() -> None:
    rows = [f"{c} & {r} & {p} \\\\" for c, r, p in PRICING_BENCHMARKS]
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Pricing benchmark vs. direct and indirect competitors. 
Competitor ranges are list prices published on 2024--25 industry 
RFP responses and Applus~IDIADA / UTAC Millbrook brochures; Tracey 
packages are this chapter's proposed pricing.}}
\\label{{tab:pricing_benchmark}}
\\begin{{tabular}}{{p{{6cm}}p{{3cm}}p{{5cm}}}}
\\toprule
\\textbf{{Offer}} & \\textbf{{Day rate (\\pounds)}} & \\textbf{{Positioning}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "pricing_benchmark.tex").write_text(tex)


def write_table_pnl(df: pd.DataFrame) -> None:
    cols = ["Revenue (\\pounds k)", "Variable cost (\\pounds k)",
            "Gross profit (\\pounds k)", "Fixed opex (\\pounds k)",
            "EBITDA (\\pounds k)", "Depreciation (\\pounds k)",
            "EBIT (\\pounds k)", "Tax @ 19\\% (\\pounds k)",
            "Net profit (\\pounds k)"]
    header = " & ".join(["\\textbf{Line}"] + [f"\\textbf{{Y{y}}}" for y in YEARS]) + " \\\\"
    lines = [header, "\\midrule"]
    for col in cols:
        vals = " & ".join(_fmt(v) for v in df[col].values)
        label = col.replace("(\\pounds k)", "").strip()
        lines.append(f"{label} & {vals} \\\\")
    body = "\n".join(lines)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Five-year P\\&L summary (\\pounds k). All figures flow from 
the single driver set stated in Sections~\\ref{{sec:capex}}--\\ref{{sec:revenue}}.}}
\\label{{tab:pnl}}
\\begin{{tabular}}{{l{'r' * N_YEARS}}}
\\toprule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "pnl.tex").write_text(tex)


def write_table_cash_flow(df: pd.DataFrame) -> None:
    cols = ["Net profit (\\pounds k)", "+ Depreciation (\\pounds k)",
            "Operating cash flow (\\pounds k)",
            "- Capex (\\pounds k)", "Free cash flow (\\pounds k)",
            "+ Equity raised (\\pounds k)", "Net cash flow (\\pounds k)",
            "Cumulative cash (\\pounds k)"]
    header = " & ".join(["\\textbf{Line}"] + [f"\\textbf{{Y{y}}}" for y in YEARS]) + " \\\\"
    lines = [header, "\\midrule"]
    for col in cols:
        vals = " & ".join(_fmt(v) for v in df[col].values)
        label = col.replace("(\\pounds k)", "").strip()
        lines.append(f"{label} & {vals} \\\\")
    body = "\n".join(lines)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Five-year cash-flow forecast (\\pounds k). Seed round 
\\pounds{SEED_ROUND/1_000_000:.1f}M at Y1; Series~A 
\\pounds{SERIES_A_ROUND/1_000_000:.1f}M at Y3.}}
\\label{{tab:cashflow}}
\\begin{{tabular}}{{l{'r' * N_YEARS}}}
\\toprule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "cashflow.tex").write_text(tex)


def write_table_revenue(df: pd.DataFrame) -> None:
    cols = ["Test days sold", "Fleet size", "Utilisation (days/vehicle)",
            "Blended day rate (\\pounds)", "Revenue (\\pounds k)",
            "Variable cost (\\pounds k)", "Gross profit (\\pounds k)",
            "Gross margin (\\%)"]
    header = " & ".join(["\\textbf{Metric}"] + [f"\\textbf{{Y{y}}}" for y in YEARS]) + " \\\\"
    lines = [header, "\\midrule"]
    unit_map = {
        "Test days sold":             "",
        "Fleet size":                 "",
        "Utilisation (days/vehicle)": "",
        "Blended day rate (\\pounds)": " (\\pounds)",
        "Revenue (\\pounds k)":        " (\\pounds k)",
        "Variable cost (\\pounds k)":  " (\\pounds k)",
        "Gross profit (\\pounds k)":   " (\\pounds k)",
        "Gross margin (\\%)":          " (\\%)",
    }
    for col in cols:
        vals_raw = df[col].values
        decimals = 0 if col != "Gross margin (\\%)" else 1
        vals = " & ".join(_fmt(v, decimals=decimals) for v in vals_raw)
        label = col.replace("(\\pounds k)", "").replace("(\\pounds)", "").replace("(\\%)", "").strip()
        unit = unit_map[col]
        lines.append(f"{label}{unit} & {vals} \\\\")
    body = "\n".join(lines)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Revenue build-up: test days, fleet utilisation, blended day 
rate, and resulting gross-profit stack.}}
\\label{{tab:revenue}}
\\begin{{tabular}}{{l{'r' * N_YEARS}}}
\\toprule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "revenue.tex").write_text(tex)


def write_table_sensitivity(df: pd.DataFrame) -> None:
    low_col  = "Low EBIT (\\pounds k)"
    base_col = "Base EBIT (\\pounds k)"
    high_col = "High EBIT (\\pounds k)"
    sw_col   = "Swing (\\pounds k)"
    rows = []
    for _, row in df.iterrows():
        drv  = row["Driver"]
        pert = row["Perturbation"]
        low  = _fmt(row[low_col],  bold_if_neg=True)
        base = _fmt(row[base_col])
        high = _fmt(row[high_col])
        sw   = _fmt(row[sw_col])
        rows.append(f"{drv} & {pert} & {low} & {base} & {high} & \\textbf{{{sw}}} \\\\")
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{One-at-a-time sensitivity: impact on Year-3 EBIT 
(\\pounds k) of perturbing each driver. Drivers ranked by absolute 
swing; negative EBIT values shown in red. Mirrors the engineering 
sensitivity ranking in Harry Emes' engineering chapter.}}
\\label{{tab:sensitivity}}
\\begin{{tabular}}{{lcrrrr}}
\\toprule
\\textbf{{Driver}} & \\textbf{{Perturbation}} & \\textbf{{Low}} & \\textbf{{Base}} & \\textbf{{High}} & \\textbf{{Swing}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "sensitivity.tex").write_text(tex)


def write_table_scenarios(scen: Dict) -> None:
    def row(name, key):
        return f"{name} & " + " & ".join(_fmt(v) for v in scen[key]["net_profit"]) + " \\\\"
    header = " & ".join(["\\textbf{Scenario}"] + [f"\\textbf{{Y{y}}}" for y in YEARS]) + " \\\\"
    body = "\n".join([
        header, "\\midrule",
        row("Base", "base"),
        row("Bull (+25\\% days, +10\\% rate, -5\\% var cost)", "bull"),
        row("Bear (-30\\% days, -10\\% rate, +10\\% var cost)", "bear"),
    ])
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Scenario analysis -- net profit after tax (\\pounds k) in each 
of the three scenarios.}}
\\label{{tab:scenarios}}
\\begin{{tabular}}{{l{'r' * N_YEARS}}}
\\toprule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "scenarios.tex").write_text(tex)


def write_table_valuation(pnl_df: pd.DataFrame) -> None:
    y5_rev = pnl_df.loc[pnl_df["Year"] == 5, "Revenue (\\pounds k)"].values[0]
    rows = []
    for peer, mult in COMPARABLE_EV_REVENUE_MULTIPLES.items():
        ev = y5_rev * mult / 1000  # £m
        rows.append(f"{peer} & {mult:.1f}$\\times$ & {ev:.1f} \\\\")
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Comparable-multiples valuation. Year-5 forecast revenue 
(\\pounds{y5_rev/1000:.1f}M) multiplied by peer EV/Revenue multiples 
gives the indicative Year-5 enterprise-value range.}}
\\label{{tab:valuation}}
\\begin{{tabular}}{{lcr}}
\\toprule
\\textbf{{Peer}} & \\textbf{{EV / Revenue}} & \\textbf{{Implied EV (\\pounds M)}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "valuation.tex").write_text(tex)


def write_table_npv(npv: Dict) -> None:
    rows = []
    for r, v in npv["npv_at_rate"].items():
        rows.append(f"{int(r*100)}\\% & {_fmt(v)} \\\\")
    body = "\n".join(rows)
    irr_pct = npv["irr"] * 100
    tv_k    = npv["terminal_value_k"]
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Project NPV and IRR, discounting the five-year free-cash-flow 
series plus a Y5 terminal value of \\pounds{tv_k/1000:,.1f}M (peer-group 
EV/Revenue median of $2.5\\times$ Y5 revenue). Free cash flows are taken 
from Table~\\ref{{tab:cashflow}} (pre-equity, post-capex). The IRR is the 
discount rate at which the project's NPV equals zero.}}
\\label{{tab:npv}}
\\begin{{tabular}}{{cr}}
\\toprule
\\textbf{{Discount rate}} & \\textbf{{Project NPV (\\pounds k)}} \\\\
\\midrule
{body}
\\midrule
\\textbf{{Project IRR}} & \\multicolumn{{1}}{{r}}{{\\textbf{{{irr_pct:.1f}\\%}}}} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "npv.tex").write_text(tex)


def write_table_downtime(dt_df: pd.DataFrame) -> None:
    dt_col  = "Downtime (\\%)"
    y3_col  = "Y3 EBIT (\\pounds k)"
    y5_col  = "Y5 EBIT (\\pounds k)"
    y5r_col = "Y5 revenue (\\pounds k)"
    npv_col = "NPV@20\\% (\\pounds k)"
    rows = []
    for _, row in dt_df.iterrows():
        dt    = int(row[dt_col])
        y1d   = int(row["Effective Y1 days"])
        y5d   = int(row["Effective Y5 days"])
        y3e   = _fmt(row[y3_col],  bold_if_neg=True)
        y5e   = _fmt(row[y5_col],  bold_if_neg=True)
        y5r   = _fmt(row[y5r_col])
        npv20 = _fmt(row[npv_col], bold_if_neg=True)
        rows.append(f"{dt}\\% & {y1d} & {y5d} & {y5r} & {y3e} & {y5e} & {npv20} \\\\")
    body = "\n".join(rows)
    tex = f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{Downtime sensitivity: effect of a persistent shortfall in 
billable days on revenue, EBIT and project NPV. A \\textit{{downtime}} 
of $d\\%$ models the case where David's maintenance protocols deliver 
$(1-d)$ of the planned test days each year. Red values indicate an EBIT 
or NPV that has turned negative.}}
\\label{{tab:downtime}}
\\begin{{tabular}}{{crrrrrr}}
\\toprule
\\textbf{{Downtime}} & \\textbf{{Y1 days}} & \\textbf{{Y5 days}} & \\textbf{{Y5 rev.}} & \\textbf{{Y3 EBIT}} & \\textbf{{Y5 EBIT}} & \\textbf{{NPV @ 20\\%}} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    (TABLES_DIR / "downtime.tex").write_text(tex)


def write_report_numbers(pnl_df: pd.DataFrame, cash_df: pd.DataFrame,
                         be: Dict, npv: Dict, dt_df: pd.DataFrame,
                         inversion: Dict) -> None:
    """Inline \\newcommand macros for numbers used in the prose."""
    y1_rev = pnl_df.loc[pnl_df["Year"] == 1, "Revenue (\\pounds k)"].values[0]
    y5_rev = pnl_df.loc[pnl_df["Year"] == 5, "Revenue (\\pounds k)"].values[0]
    y5_ebit = pnl_df.loc[pnl_df["Year"] == 5, "EBIT (\\pounds k)"].values[0]
    break_even_year = pnl_df.loc[pnl_df["EBIT (\\pounds k)"] > 0, "Year"].min()
    break_even_year = int(break_even_year) if pd.notna(break_even_year) else "n/a"

    # Downtime break-point: first downtime % at which NPV@20% <= 0
    npv_col = "NPV@20\\% (\\pounds k)"
    dt_col  = "Downtime (\\%)"
    dt_negative = dt_df[dt_df[npv_col] <= 0]
    downtime_break = (int(dt_negative[dt_col].iloc[0])
                      if not dt_negative.empty else None)

    # Cumulative capex at crossover year (from inversion analysis)
    cross_year = inversion["crossover_year"]
    total_capex = sum(inversion["annual_capex_k"])

    commands = {
        "yOneRevenue":       f"\\pounds{y1_rev:,.0f}k",
        "yFiveRevenue":      f"\\pounds{y5_rev/1000:,.1f}M",
        "yFiveEbit":         f"\\pounds{y5_ebit/1000:,.1f}M",
        "breakEvenYear":     f"Y{break_even_year}",
        "breakEvenDays":     f"{be['break_even_days_y2']:,.0f}",
        "contributionMargin": f"\\pounds{be['contribution_per_day']:,.0f}",
        "seedRound":         f"\\pounds{SEED_ROUND/1_000_000:.1f}M",
        "seriesARound":      f"\\pounds{SERIES_A_ROUND/1_000_000:.1f}M",
        "totalRaise":        f"\\pounds{TOTAL_RAISE/1_000_000:.1f}M",
        "capexPerVehicle":   f"\\pounds{CAPEX_PER_VEHICLE_TOTAL/1000:.0f}k",
        "totalCapex":        f"\\pounds{total_capex/1000:,.2f}M",
        "fixedOpexYOne":     f"\\pounds{FIXED_OPEX_Y1_TOTAL/1000:.0f}k",
        "ltv":               f"\\pounds{LTV/1000:.0f}k",
        "cac":               f"\\pounds{CAC/1000:.0f}k",
        "ltvCac":            f"{LTV_CAC:.1f}\\ensuremath{{\\times}}",
        "paybackMonths":     f"{PAYBACK_MONTHS:.1f}",
        "npvBase":           f"\\pounds{npv['npv_at_rate'][0.20]/1000:,.2f}M",
        "npvHurdle":         f"\\pounds{npv['npv_at_rate'][0.25]/1000:,.2f}M",
        "irr":               f"{npv['irr']*100:.1f}\\%",
        "terminalValue":     f"\\pounds{npv['terminal_value_k']/1000:,.1f}M",
        "downtimeBreak":     (f"{downtime_break}\\%" if downtime_break is not None
                              else "$>30\\%$"),
        "inversionCrossover": f"Y{cross_year}" if cross_year else "beyond Y5",
    }
    tex = "\n".join(f"\\newcommand{{\\{k}}}{{{v}\\xspace}}" for k, v in commands.items())
    tex = "\\usepackage{xspace}\n" + tex + "\n"
    # xspace import lives in main.tex preamble instead; strip here.
    tex = tex.replace("\\usepackage{xspace}\n", "")
    (HERE / "report_numbers.tex").write_text(tex)


# ====================================================================
#  MAIN
# ====================================================================

def main() -> None:
    capex_df  = build_capex_schedule()
    opex_df   = build_opex_schedule()
    rev_df    = build_revenue_schedule()
    pnl_df    = build_pnl()
    cash_df   = build_cash_flow()
    be        = compute_break_even(pnl_df)
    sens_df   = run_sensitivity()
    scenarios = run_scenarios()
    npv       = compute_npv_irr()
    dt_df     = run_downtime_sensitivity()
    inversion = compute_capex_inversion()
    y10_proj  = compute_year_10_projection()

    # LaTeX tables
    write_table_capex(capex_df)
    write_table_capex_breakdown()
    write_table_opex_breakdown()
    write_table_pricing()
    write_table_revenue(rev_df)
    write_table_pnl(pnl_df)
    write_table_cash_flow(cash_df)
    write_table_sensitivity(sens_df)
    write_table_scenarios(scenarios)
    write_table_valuation(pnl_df)
    write_table_npv(npv)
    write_table_downtime(dt_df)

    # Inline prose numbers
    write_report_numbers(pnl_df, cash_df, be, npv, dt_df, inversion)

    # JSON dump for the figures script
    out = {
        "years":               YEARS,
        "utilisation_days":    UTILISATION_DAYS,
        "fleet_size":          FLEET_SIZE,
        "blended_day_rate":    BLENDED_DAY_RATE,
        "variable_cost_per_day": VARIABLE_COST_PER_DAY,
        "capex_per_vehicle":   CAPEX_PER_VEHICLE,
        "capex_per_vehicle_total": CAPEX_PER_VEHICLE_TOTAL,
        "office_setup_y1":     OFFICE_SETUP_Y1_TOTAL,
        "fixed_opex_y1":       FIXED_OPEX_Y1,
        "fixed_opex_y1_total": FIXED_OPEX_Y1_TOTAL,
        "capex_schedule":      capex_df.to_dict(orient="list"),
        "opex_schedule":       opex_df.to_dict(orient="list"),
        "revenue_schedule":    rev_df.to_dict(orient="list"),
        "pnl":                 pnl_df.to_dict(orient="list"),
        "cash_flow":           cash_df.to_dict(orient="list"),
        "break_even":          be,
        "sensitivity":         sens_df.to_dict(orient="list"),
        "scenarios":           scenarios,
        "cac":                 CAC,
        "ltv":                 LTV,
        "ltv_cac":             LTV_CAC,
        "payback_months":      PAYBACK_MONTHS,
        "seed_round":          SEED_ROUND,
        "series_a_round":      SERIES_A_ROUND,
        "valuation_multiples": COMPARABLE_EV_REVENUE_MULTIPLES,
        "npv":                 {
            "npv_at_rate":     {f"{int(r*100)}": float(v) for r, v in npv["npv_at_rate"].items()},
            "irr":             float(npv["irr"]),
            "terminal_value_k": float(npv["terminal_value_k"]),
            "fcf_incl_tv_k":   npv["fcf_incl_tv_k"],
            "npv_curve_rates": npv["npv_curve_rates"],
            "npv_curve_k":     npv["npv_curve_k"],
        },
        "downtime_sensitivity": dt_df.to_dict(orient="list"),
        "capex_inversion":     inversion,
        "year_10_projection":  y10_proj,
    }
    (HERE / "financial_model.json").write_text(json.dumps(out, indent=2, default=float))

    # Console sanity print
    print("=" * 64)
    print("AEB RABBIT TaaS -- FINANCIAL MODEL SUMMARY")
    print("=" * 64)
    print("\n-- Revenue / gross profit --")
    print(rev_df.to_string(index=False))
    print("\n-- P&L --")
    print(pnl_df.to_string(index=False))
    print("\n-- Cash flow --")
    print(cash_df.to_string(index=False))
    print("\n-- Sensitivity (Y3 EBIT) --")
    print(sens_df.to_string(index=False))
    print(f"\n-- Break-even (Y2 cost base): "
          f"{be['break_even_days_y2']:.0f} test days/year --")
    cum_col = "Cumulative cash (\\pounds k)"
    max_burn = -cash_df[cum_col].min()
    print(f"-- Max cumulative cash burn: GBP {max_burn:,.0f}k --")
    print(f"-- LTV/CAC = {LTV_CAC:.1f}x, payback = {PAYBACK_MONTHS:.1f} months --")
    print(f"\n-- NPV at 20%: GBP {npv['npv_at_rate'][0.20]:,.0f}k, "
          f"IRR: {npv['irr']*100:.1f}% --")
    print(f"-- Terminal value at Y5: GBP {npv['terminal_value_k']:,.0f}k --")
    print(f"-- Y10 (extended horizon): revenue GBP {y10_proj['year_10_revenue_k']:,.0f}k, "
          f"terminal EV (2.5x rev) GBP {y10_proj['year_10_terminal_enterprise_value_k']:,.0f}k --")
    print(f"-- CAPEX inversion: cumulative revenue overtakes cumulative capex in "
          f"Y{inversion['crossover_year']} --")
    print("\n-- Downtime sensitivity --")
    print(dt_df.to_string(index=False))


if __name__ == "__main__":
    main()
