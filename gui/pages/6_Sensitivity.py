"""Sensitivity report.

One-at-a-time perturbation sweep across a user-selected subset of numeric
parameters. For each parameter, the simulation is run with the value shifted
by +/- pct% (or +/- the spec step for zero-valued params), and the change in
final time (or other objective) is recorded.

Output is a tornado chart sorted by absolute impact on the objective, plus
a sortable data table with compliance flags (wheelie / power) at each
perturbation. This answers the question "which parameters actually matter?"
without having to run a 2D sweep or a full optimisation.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_PKG_ROOT = Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from gui._core.config_io import list_configs, load_as_dict
from gui._core.param_schema import (
    NUMERIC_PARAMS,
    SECTION_LABELS,
    SECTION_ORDER,
    find,
    get_value,
)
from gui._core.sensitivity import (
    DEFAULT_SENSITIVITY_PARAMS,
    OBJECTIVES,
    run_sensitivity,
)


st.set_page_config(page_title="Sensitivity", page_icon=":mag:", layout="wide")
st.title("Parameter Sensitivity Report")

st.caption(
    "Perturbs each selected parameter by ±pct% from the base config, runs a "
    "full simulation, and ranks them by impact on the chosen objective. "
    "Parameters outside their schema bounds after perturbation are "
    "automatically clamped and flagged."
)

# --- Base config + objective --------------------------------------------

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

c_cfg, c_obj, c_pct = st.columns([2, 2, 1])
with c_cfg:
    default_idx = (
        configs.index("base_vehicle") if "base_vehicle" in configs else 0
    )
    base_name = st.selectbox("Base config", configs, index=default_idx)
with c_obj:
    objective = st.selectbox(
        "Objective",
        options=list(OBJECTIVES.keys()),
        format_func=lambda k: OBJECTIVES[k]["label"],
        index=0,
    )
with c_pct:
    pct = st.number_input("Perturbation (±%)", min_value=0.5, max_value=25.0,
                          value=5.0, step=0.5,
                          help="Each parameter is shifted by +/- this fraction "
                               "of its base value. Smaller = more linear, "
                               "closer to a true local derivative.")

c_dt, c_maxt = st.columns(2)
with c_dt:
    search_dt = st.number_input("Search dt (s)", min_value=0.001, max_value=0.02,
                                value=0.005, step=0.001, format="%.3f",
                                help="Coarser = faster sweep. 0.005 s is usually fine.")
with c_maxt:
    search_max_time = st.number_input("Search max time (s)", min_value=5.0, max_value=30.0,
                                      value=12.0, step=1.0)

base_data = load_as_dict(base_name)

# --- Parameter selection ------------------------------------------------

st.subheader("Parameters to analyse")
st.caption(
    "The defaults cover the most impactful knobs across mass / grip / aero "
    "/ powertrain / control. Untick to exclude; tick extra boxes to add more."
)

if "sens_selected" not in st.session_state:
    st.session_state["sens_selected"] = set(DEFAULT_SENSITIVITY_PARAMS)

b_all, b_none, b_defaults = st.columns([1, 1, 1])
if b_all.button("Select all numeric"):
    st.session_state["sens_selected"] = {p.dotted for p in NUMERIC_PARAMS}
if b_none.button("Clear selection"):
    st.session_state["sens_selected"] = set()
if b_defaults.button("Reset to defaults"):
    st.session_state["sens_selected"] = set(DEFAULT_SENSITIVITY_PARAMS)

selected_set = st.session_state["sens_selected"]

# Grid of checkboxes grouped by section.
sections: dict = {s: [] for s in SECTION_ORDER}
for p in NUMERIC_PARAMS:
    sections.setdefault(p.section, []).append(p)

for section in SECTION_ORDER:
    specs = sections.get(section, [])
    if not specs:
        continue
    with st.expander(SECTION_LABELS.get(section, section.capitalize()),
                     expanded=(section == "mass")):
        cols = st.columns(3)
        for idx, spec in enumerate(specs):
            with cols[idx % 3]:
                base_val = get_value(base_data, spec, spec.min or 0.0)
                label = f"{spec.label} ({base_val:g})"
                new = st.checkbox(label, value=spec.dotted in selected_set,
                                  key=f"sens_cb_{spec.dotted}")
                if new:
                    selected_set.add(spec.dotted)
                else:
                    selected_set.discard(spec.dotted)

st.session_state["sens_selected"] = selected_set

st.markdown(f"**{len(selected_set)} parameter(s) selected.**")
run_clicked = st.button("Run sensitivity report", type="primary",
                        disabled=len(selected_set) == 0)

# --- Execution ----------------------------------------------------------

if run_clicked:
    dotted_list = sorted(selected_set)
    total_runs = 1 + 2 * len(dotted_list)
    progress = st.progress(0.0, text=f"Running {total_runs} simulations...")

    def _cb(step: int, total: int, label: str) -> None:
        progress.progress(step / total, text=f"[{step}/{total}] {label}")

    try:
        report = run_sensitivity(
            base_data,
            dotted_list,
            pct=pct,
            objective=objective,
            search_dt=search_dt,
            search_max_time=search_max_time,
            progress_callback=_cb,
        )
    except RuntimeError as exc:
        progress.empty()
        st.error(str(exc))
        st.stop()
    progress.empty()

    meta = OBJECTIVES[objective]
    units = meta["units"]

    b1, b2, b3 = st.columns(3)
    b1.metric(f"Base {objective}",
              f"{report.base_metric:.3f} {units}")
    b2.metric("Base compliant",
              "Yes" if report.base_compliant else "NO (invalid base)")
    b3.metric("Simulations run",
              f"{1 + sum(1 for p in report.perturbations if p.ok)}")

    if not report.base_compliant:
        st.warning(
            "Base configuration is non-compliant (wheelie or power-limit "
            "violation). Perturbation deltas are relative to an invalid run "
            "- interpret with caution."
        )

    df = report.dataframe()
    if df.empty:
        st.info("No valid perturbations - all parameters may be at their "
                "schema bounds.")
        st.stop()

    # --- Tornado chart -----------------------------------------------------

    # Horizontal bars, two per parameter (low and high deltas).
    display_df = df.copy()
    # Reverse so largest-impact appears at the TOP of a horizontal bar chart
    # (plotly draws y-axis bottom-to-top).
    display_df = display_df.iloc[::-1].reset_index(drop=True)

    param_labels = [
        f"{row['label']}  ({row['parameter']})"
        for _, row in display_df.iterrows()
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=param_labels,
        x=display_df["delta_low"].fillna(0.0),
        orientation="h",
        name=f"-{pct:g}%",
        marker=dict(color="#3b82f6"),
        hovertemplate=(
            "<b>%{y}</b><br>-" + f"{pct:g}" + "%: <br>"
            "value: %{customdata[0]:.4g}<br>"
            f"{objective}: %{{customdata[1]:.4f}} {units}<br>"
            f"delta: %{{x:+.4f}} {units}<extra></extra>"
        ),
        customdata=list(zip(display_df["value_low"], display_df["metric_low"])),
    ))
    fig.add_trace(go.Bar(
        y=param_labels,
        x=display_df["delta_high"].fillna(0.0),
        orientation="h",
        name=f"+{pct:g}%",
        marker=dict(color="#ef4444"),
        hovertemplate=(
            "<b>%{y}</b><br>+" + f"{pct:g}" + "%: <br>"
            "value: %{customdata[0]:.4g}<br>"
            f"{objective}: %{{customdata[1]:.4f}} {units}<br>"
            f"delta: %{{x:+.4f}} {units}<extra></extra>"
        ),
        customdata=list(zip(display_df["value_high"], display_df["metric_high"])),
    ))

    improve_direction = (
        "lower is better" if meta["direction"] == "minimise"
        else "higher is better" if meta["direction"] == "maximise"
        else "direction depends on context"
    )
    fig.update_layout(
        title=f"Tornado: sensitivity of {meta['label']} to +/-{pct:g}% perturbations "
              f"({improve_direction})",
        xaxis_title=f"Delta from base ({units})",
        barmode="overlay",
        template="plotly_white",
        height=max(400, 32 * len(display_df) + 120),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        margin=dict(l=250, r=40, t=80, b=40),
    )
    fig.add_vline(x=0, line=dict(color="#111827", width=1))

    st.plotly_chart(fig, use_container_width=True)

    # --- Warnings: perturbations that changed compliance -----------------

    compliance_flips = df[
        (~df["low_compliant"]) | (~df["high_compliant"])
        | df["low_wheelie"] | df["high_wheelie"]
    ]
    if not compliance_flips.empty:
        st.warning(
            f"**{len(compliance_flips)} parameter(s) caused compliance to change "
            "in at least one perturbation direction.** These are sensitivities "
            "you likely care about most - a small change triggers a wheelie or "
            "power-limit violation."
        )
        for _, row in compliance_flips.iterrows():
            flags = []
            if row["low_wheelie"]:
                flags.append(f"wheelie at -{pct:g}%")
            if row["high_wheelie"]:
                flags.append(f"wheelie at +{pct:g}%")
            if not row["low_compliant"] and not row["low_wheelie"]:
                flags.append(f"non-compliant at -{pct:g}%")
            if not row["high_compliant"] and not row["high_wheelie"]:
                flags.append(f"non-compliant at +{pct:g}%")
            st.markdown(f"- **{row['parameter']}**: " + "; ".join(flags))

    # --- Data table -------------------------------------------------------

    st.subheader("Full data")
    display_columns = [
        "parameter", "base_value", "value_low", "value_high",
        "metric_low", "metric_high", "delta_low", "delta_high",
        "elasticity", "low_compliant", "high_compliant",
        "low_wheelie", "high_wheelie", "notes",
    ]
    st.dataframe(
        df[display_columns].round(6).set_index("parameter"),
        use_container_width=True,
    )

    csv = df[display_columns].to_csv(index=False)
    st.download_button(
        "Download CSV",
        data=csv,
        file_name=f"sensitivity_{base_name}_{objective}_{pct:g}pct.csv",
        mime="text/csv",
    )

    # --- Interpretation tips ---------------------------------------------

    with st.expander("How to read this"):
        st.markdown(
            f"""
- **Tornado bars** show the change in {meta['label']} when a single
  parameter is perturbed by +/-{pct:g}% (blue = low direction, red = high).
  Bars are sorted top-down by the larger absolute effect on the objective.
- **Elasticity** (in the data table) is (% change in objective) /
  (% change in parameter). A value of -0.5 means a 1% increase in the
  parameter makes the objective 0.5% smaller.
- **Compliance warnings** flag parameters whose perturbation knocked the
  run out of the Formula Student rule envelope (wheelie, 80 kW power limit,
  or 25 s time cap). These are usually your **risk-sensitive** knobs.
- Perturbations that bumped into a schema bound are shown with value ==
  base and delta == null in the table (no useful sensitivity at that edge).
            """
        )
else:
    st.info("Choose the base config, objective, perturbation size, and "
            "parameters above, then click **Run sensitivity report**.")
