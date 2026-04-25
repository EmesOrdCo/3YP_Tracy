"""Monte Carlo robustness analysis.

Runs N simulations with each uncertain parameter sampled from its own
distribution (Gaussian by default; spread interpreted as 1-sigma for
Gaussian or half-width for uniform). Produces:

- A **histogram** of the chosen objective with mean and 95 % CI overlaid.
- A **summary statistics** card (mean, std, percentiles, min/max).
- **Compliance probabilities** (wheelie, power violation, non-compliant).
- A **variance-contribution tornado**: what fraction of the output
  variance is linearly explained by each input (corr^2).
- A **data table** of all trials with CSV export.

This is the signature figure for a report: "our 75 m time is
X +/- sigma s with 95 % CI [a, b], P(wheelie) = Z %" - a statement
about the whole envelope of real-world variability.
"""

from __future__ import annotations

from pathlib import Path
import copy
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_PKG_ROOT = Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from gui._core.config_io import list_configs, load_as_dict
from gui._core.monte_carlo import (
    UncertainParam,
    default_uncertain_params,
    run_monte_carlo,
)
from gui._core.param_schema import find, get_value


st.set_page_config(page_title="Monte Carlo Robustness", page_icon=":game_die:",
                   layout="wide")
st.title("Monte Carlo Robustness Analysis")

st.caption(
    "Randomises each listed parameter from its own distribution, runs a "
    "full simulation per trial, and reports the distribution of final-time "
    "(or other objective) outcomes along with compliance probabilities. "
    "Adds proper error bars to any headline result."
)

# --- Setup ------------------------------------------------------------

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

default_idx = (
    configs.index("optimized_vehicle") if "optimized_vehicle" in configs
    else configs.index("base_vehicle") if "base_vehicle" in configs
    else 0
)

c_cfg, c_obj, c_n = st.columns([2, 2, 1])
with c_cfg:
    base_name = st.selectbox("Base config", configs, index=default_idx)
with c_obj:
    objective = st.selectbox(
        "Objective",
        options=["final_time", "final_velocity"],
        index=0,
        format_func=lambda k: {"final_time": "Final 75 m time (s)",
                               "final_velocity": "Final velocity (m/s)"}[k],
    )
with c_n:
    n_trials = st.number_input("Trials (N)", min_value=20, max_value=5000,
                               value=200, step=20,
                               help="200 = ~60 s with default settings. "
                                    "1000 is suitable for final-figure runs.")

c_dt, c_maxt, c_seed = st.columns(3)
with c_dt:
    search_dt = st.number_input("Search dt (s)", min_value=0.001, max_value=0.02,
                                value=0.005, step=0.001, format="%.3f")
with c_maxt:
    search_max_time = st.number_input("Search max time (s)",
                                      min_value=5.0, max_value=30.0,
                                      value=12.0, step=1.0)
with c_seed:
    seed = st.number_input("Random seed", min_value=0, max_value=99999,
                           value=42, step=1,
                           help="Same seed = reproducible sampling.")

base_data = load_as_dict(base_name)

# --- Uncertain-parameter table ---------------------------------------

st.subheader("Uncertain parameters")
st.caption(
    "Each row is a parameter sampled independently per trial. 'Spread' is "
    "1-sigma for Gaussian or half-width for uniform. Samples outside the "
    "schema bounds are clipped (never rejected) to preserve N. Tick 'use' "
    "to include a parameter; untick to leave it at its base value."
)

if "mc_rows" not in st.session_state:
    defaults = default_uncertain_params(base_data)
    st.session_state["mc_rows"] = [
        {"dotted": p.dotted, "use": True, "nominal": p.nominal,
         "spread": p.spread, "distribution": p.distribution}
        for p in defaults
    ]
    st.session_state["mc_base_name"] = base_name
else:
    # Re-centre nominals if the base config has changed.
    if st.session_state.get("mc_base_name") != base_name:
        defaults = default_uncertain_params(base_data)
        st.session_state["mc_rows"] = [
            {"dotted": p.dotted, "use": True, "nominal": p.nominal,
             "spread": p.spread, "distribution": p.distribution}
            for p in defaults
        ]
        st.session_state["mc_base_name"] = base_name

rows = st.session_state["mc_rows"]

for i, row in enumerate(rows):
    c_use, c_name, c_mean, c_spread, c_dist = st.columns([0.5, 2, 1, 1, 1])
    with c_use:
        row["use"] = st.checkbox(" ", value=row["use"], key=f"mc_use_{i}",
                                 label_visibility="collapsed")
    with c_name:
        st.text(row["dotted"])
        spec = find(row["dotted"])
        if spec and spec.unit:
            st.caption(f"units: {spec.unit}")
    with c_mean:
        row["nominal"] = st.number_input("mean", value=float(row["nominal"]),
                                         key=f"mc_mean_{i}", format="%.4f")
    with c_spread:
        row["spread"] = st.number_input("spread", value=float(row["spread"]),
                                        min_value=0.0, step=0.001,
                                        key=f"mc_sp_{i}", format="%.4f")
    with c_dist:
        row["distribution"] = st.selectbox(
            "dist", options=["gaussian", "uniform"],
            index=0 if row["distribution"] == "gaussian" else 1,
            key=f"mc_d_{i}", label_visibility="collapsed",
        )

# Convenience buttons.
b_reset, b_all, b_none = st.columns([1, 1, 1])
if b_reset.button("Reset to defaults"):
    st.session_state.pop("mc_rows", None)
    st.rerun()
if b_all.button("Use all rows"):
    for row in rows:
        row["use"] = True
if b_none.button("Clear selection"):
    for row in rows:
        row["use"] = False

run_clicked = st.button("Run Monte Carlo", type="primary",
                        disabled=not any(row["use"] for row in rows))


# --- Execution --------------------------------------------------------

if run_clicked:
    uncertain_params = [
        UncertainParam(
            dotted=row["dotted"],
            nominal=float(row["nominal"]),
            spread=float(row["spread"]),
            distribution=row["distribution"],
        )
        for row in rows if row["use"]
    ]

    progress = st.progress(0.0, text=f"Running {int(n_trials)} trials...")

    def _cb(i: int, n: int) -> None:
        progress.progress(i / n, text=f"[{i}/{n}]")

    result = run_monte_carlo(
        base_data,
        uncertain_params,
        n_trials=int(n_trials),
        objective=objective,
        seed=int(seed),
        search_dt=search_dt,
        search_max_time=search_max_time,
        progress_callback=_cb,
    )
    progress.empty()

    summary = result.summary()
    meta = result.objective_meta
    units = meta["units"]

    if summary["count"] == 0:
        st.error("All trials failed. Check the base config.")
        st.stop()

    # --- Header metrics ----------------------------------------------

    nominal_str = (f"{result.nominal_metric:.3f} {units}"
                   if result.nominal_metric is not None else "—")
    ci_low = summary["mean"] - 1.96 * summary["std"]
    ci_high = summary["mean"] + 1.96 * summary["std"]

    h = st.columns(5)
    h[0].metric("Nominal", nominal_str,
                help="Deterministic run at the base config, no randomisation.")
    h[1].metric("MC mean",
                f"{summary['mean']:.3f} {units}",
                f"{summary['mean'] - (result.nominal_metric or summary['mean']):+.3f} vs nominal")
    h[2].metric("Std (1-sigma)", f"{summary['std']:.3f} {units}")
    h[3].metric("95 % CI",
                f"[{summary['p05']:.3f}, {summary['p95']:.3f}]",
                help="5th and 95th percentiles (non-parametric CI).")
    h[4].metric("Valid trials",
                f"{summary['count']} / {int(n_trials)}",
                f"{summary['p_failed']*100:.1f}% failed" if summary["p_failed"] > 0 else "0% failed")

    st.info(
        f"**Headline for the report:**  "
        f"{meta['label']} = {summary['mean']:.3f} +/- {summary['std']:.3f} {units}, "
        f"95% CI [{summary['p05']:.3f}, {summary['p95']:.3f}] "
        f"(N = {summary['count']})."
    )

    # --- Compliance probabilities ------------------------------------

    p = st.columns(3)
    p[0].metric("P(wheelie)", f"{summary['p_wheelie']*100:.1f} %",
                help="Fraction of trials that tripped the wheelie detector.")
    p[1].metric("P(power violation)", f"{summary['p_power_violation']*100:.1f} %",
                help="Fraction with moving-avg power > 80 kW + tolerance.")
    p[2].metric("P(non-compliant)", f"{summary['p_non_compliant']*100:.1f} %",
                help="Any rule failure: wheelie, power, or time limit.")

    # --- Histogram ---------------------------------------------------

    m = result.metric_array()
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=m, nbinsx=min(40, max(10, int(np.sqrt(len(m))))),
        name="Trials",
        marker=dict(color="#60a5fa", line=dict(color="#1d4ed8", width=0.5)),
        opacity=0.8,
    ))
    # Mean line.
    fig.add_vline(x=summary["mean"],
                  line=dict(color="#111827", width=2),
                  annotation_text=f"mean {summary['mean']:.3f}",
                  annotation_position="top")
    # 95% CI lines.
    fig.add_vline(x=summary["p05"], line=dict(color="#ef4444", dash="dash"),
                  annotation_text=f"5 %: {summary['p05']:.3f}",
                  annotation_position="bottom left")
    fig.add_vline(x=summary["p95"], line=dict(color="#ef4444", dash="dash"),
                  annotation_text=f"95 %: {summary['p95']:.3f}",
                  annotation_position="bottom right")
    # Nominal (deterministic) marker.
    if result.nominal_metric is not None:
        fig.add_vline(x=result.nominal_metric,
                      line=dict(color="#f59e0b", dash="dot", width=2),
                      annotation_text=f"nominal {result.nominal_metric:.3f}",
                      annotation_position="top right")
    fig.update_layout(
        title=f"Distribution of {meta['label']}  (N = {summary['count']})",
        xaxis_title=f"{meta['label']}",
        yaxis_title="Count",
        template="plotly_white",
        bargap=0.05,
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Variance-contribution tornado ------------------------------

    vd = result.variance_decomposition()
    if not vd.empty and len(uncertain_params) > 1:
        st.subheader("Variance contribution")
        st.caption(
            "For each uncertain input, the fraction of the output variance "
            "linearly attributable to it (corr^2). These sum to <=1 in a "
            "perfectly linear system; any shortfall is interactions / "
            "nonlinearity. The tallest bar is the knob whose uncertainty "
            "is worth reducing first."
        )

        vd_plot = vd.copy().iloc[::-1]  # largest at top
        sign = np.sign(vd_plot["corr"].to_numpy())
        colours = ["#ef4444" if s > 0 else "#3b82f6" for s in sign]
        labels = [f"{p.dotted}" for p in uncertain_params]

        fig_t = go.Figure()
        fig_t.add_trace(go.Bar(
            x=vd_plot["corr2"] * 100,
            y=vd_plot["parameter"],
            orientation="h",
            marker=dict(color=colours),
            text=[f"{c*100:.1f}% ({'+' if corr>0 else '-'})"
                  for c, corr in zip(vd_plot["corr2"], vd_plot["corr"])],
            textposition="auto",
        ))
        fig_t.update_layout(
            title="Share of output variance explained by each input (linear, corr^2)",
            xaxis_title="Variance contribution (%)",
            template="plotly_white",
            height=max(320, 32 * len(vd_plot) + 120),
            margin=dict(l=200, r=40, t=80, b=40),
        )
        st.plotly_chart(fig_t, use_container_width=True)
        st.caption(
            "Red = positive correlation (higher input -> higher output); "
            "Blue = negative (higher input -> lower output)."
        )

    # --- Full stats table --------------------------------------------

    with st.expander("Full statistics"):
        st.table(pd.DataFrame({
            "statistic": ["count (valid)", "mean", "std (1σ)",
                          "min", "5th pct", "50th pct", "95th pct", "max",
                          "P(wheelie)", "P(power violation)",
                          "P(non-compliant)", "P(failed trial)"],
            f"value ({units})": [
                f"{summary['count']}", f"{summary['mean']:.4f}",
                f"{summary['std']:.4f}",
                f"{summary['min']:.4f}", f"{summary['p05']:.4f}",
                f"{summary['p50']:.4f}", f"{summary['p95']:.4f}",
                f"{summary['max']:.4f}",
                f"{summary['p_wheelie']*100:.2f} %",
                f"{summary['p_power_violation']*100:.2f} %",
                f"{summary['p_non_compliant']*100:.2f} %",
                f"{summary['p_failed']*100:.2f} %",
            ],
        }))

    with st.expander("Sample data (all trials)"):
        display_cols = ["__trial"]
        display_cols += [f"__x__{p.dotted}" for p in uncertain_params]
        display_cols += ["__metric", "__final_time", "__final_velocity",
                         "__max_power_kw", "__compliant",
                         "__wheelie", "__power_ok", "__error"]
        display_cols = [c for c in display_cols if c in result.samples.columns]
        st.dataframe(result.samples[display_cols], use_container_width=True)

    st.download_button(
        "Download all trials as CSV",
        data=result.samples.to_csv(index=False),
        file_name=f"monte_carlo_{base_name}_{objective}_N{summary['count']}.csv",
        mime="text/csv",
    )

else:
    st.info(
        "Review the uncertain parameters above, then click **Run Monte Carlo**. "
        "Each trial is a full 75 m simulation with a fresh random sample, "
        "so N=200 takes about a minute with default dt=0.005 s."
    )
