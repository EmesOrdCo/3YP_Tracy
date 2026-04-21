"""Track-conditions analysis: dry vs damp vs wet vs iced.

Runs the same vehicle config under several preset surface conditions and
shows the headline deltas + overlaid plots. The `environment.surface_mu_scaling`
multiplier is the only knob that differs between scenarios (optionally the
air temperature and tyre initial temp if the thermal model is on).

Useful for the report: produces a clean "how sensitive is acceleration to
track conditions?" figure that is hard to get from the generic Parameter
Sweep.
"""

from __future__ import annotations

from pathlib import Path
import copy
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_PKG_ROOT = Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

from gui._core import plots, sim_runner
from gui._core.config_io import list_configs, load_as_dict


# Scenario presets. surface_mu_scaling multiplies every peak tyre force
# (Pacejka or simple). Temperature fields are only applied when the thermal
# model is enabled on the base config.
SCENARIOS = {
    "Dry (reference)": {
        "mu_scale": 1.00,
        "ambient_c": 25.0,
        "tyre_initial_c": 60.0,
        "description": "Clean, dry tarmac. Peak μ at the value in the tyre config.",
    },
    "Damp (light rain)": {
        "mu_scale": 0.80,
        "ambient_c": 18.0,
        "tyre_initial_c": 40.0,
        "description": "Damp surface, standing moisture; slicks lose about 20% of peak μ.",
    },
    "Wet (steady rain)": {
        "mu_scale": 0.60,
        "ambient_c": 14.0,
        "tyre_initial_c": 30.0,
        "description": "Water film, slicks on a wet surface. ~40% drop in peak μ.",
    },
    "Cold + dry": {
        "mu_scale": 1.00,
        "ambient_c": 5.0,
        "tyre_initial_c": 10.0,
        "description": "Cold morning, dry tyres but well below optimal temperature.",
    },
    "Hot + dry": {
        "mu_scale": 1.00,
        "ambient_c": 35.0,
        "tyre_initial_c": 90.0,
        "description": "Hot day; tyres near or slightly above optimal.",
    },
}


st.set_page_config(page_title="Track Conditions", page_icon=":droplet:", layout="wide")
st.title("Track Conditions Analysis")

st.caption(
    "Compares the same config across dry/damp/wet/cold/hot scenarios by "
    "scaling `environment.surface_mu_scaling` and (if the thermal model is "
    "on) the ambient and initial-tyre temperatures. Produces a single "
    "figure for the report showing how sensitive acceleration is to "
    "surface conditions."
)

# --- Controls ----------------------------------------------------------

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

default_idx = configs.index("base_vehicle") if "base_vehicle" in configs else 0
c_cfg, c_dt = st.columns([3, 1])
with c_cfg:
    base_name = st.selectbox("Base config", configs, index=default_idx)
with c_dt:
    search_dt = st.number_input("dt (s)", min_value=0.001, max_value=0.02,
                                value=0.005, step=0.001, format="%.3f")

st.subheader("Scenarios to compare")
scenario_cols = st.columns(len(SCENARIOS))
selected: list = []
for (name, preset), col in zip(SCENARIOS.items(), scenario_cols):
    with col:
        default_on = name in ("Dry (reference)", "Damp (light rain)", "Wet (steady rain)")
        if st.checkbox(name, value=default_on, key=f"tc_sel_{name}"):
            selected.append(name)
        st.caption(
            f"μ×{preset['mu_scale']:.2f}, "
            f"T_amb={preset['ambient_c']:.0f}°C, "
            f"T_tyre_init={preset['tyre_initial_c']:.0f}°C"
        )

run_clicked = st.button("Run scenarios", type="primary", disabled=len(selected) == 0)


# --- Execution --------------------------------------------------------

def _apply_scenario(base: dict, preset: dict) -> dict:
    data = copy.deepcopy(base)
    data.setdefault("environment", {})["surface_mu_scaling"] = float(preset["mu_scale"])
    thermal_on = bool(data.get("tires", {}).get("thermal_model_enabled", False))
    if thermal_on:
        data.setdefault("tires", {})["thermal_ambient_temp"] = float(preset["ambient_c"])
        data["tires"]["thermal_initial_temp"] = float(preset["tyre_initial_c"])
    data.setdefault("simulation", {})["dt"] = float(search_dt)
    return data


if run_clicked:
    base_data = load_as_dict(base_name)
    outcomes: dict = {}
    rows: list = []
    progress = st.progress(0.0, text="Running scenarios...")

    for i, name in enumerate(selected):
        preset = SCENARIOS[name]
        data = _apply_scenario(base_data, preset)
        outcome = sim_runner.run(data)
        outcomes[name] = outcome
        if outcome.ok:
            r = outcome.result
            rows.append({
                "Scenario": name,
                "mu scaling": preset["mu_scale"],
                "T_ambient (°C)": preset["ambient_c"],
                "T_tyre_init (°C)": preset["tyre_initial_c"],
                "Final time (s)": round(r.final_time, 3),
                "Final velocity (m/s)": round(r.final_velocity, 2),
                "Max power (kW)": round(r.max_power_used / 1000.0, 2),
                "Compliant": bool(r.compliant),
                "Wheelie": bool(r.wheelie_detected),
            })
        else:
            rows.append({
                "Scenario": name,
                "mu scaling": preset["mu_scale"],
                "T_ambient (°C)": preset["ambient_c"],
                "T_tyre_init (°C)": preset["tyre_initial_c"],
                "Final time (s)": None,
                "Final velocity (m/s)": None,
                "Max power (kW)": None,
                "Compliant": False,
                "Wheelie": False,
                "error": "; ".join(outcome.errors),
            })
        progress.progress((i + 1) / len(selected))
    progress.empty()

    # --- Summary table ------------------------------------------------

    df = pd.DataFrame(rows)

    # Deltas vs the reference row if the dry scenario is in the selection.
    ref_name = "Dry (reference)"
    if ref_name in selected and not df.empty:
        ref = df[df["Scenario"] == ref_name].iloc[0]
        if ref["Final time (s)"] is not None:
            df["Δtime vs dry (s)"] = df["Final time (s)"].apply(
                lambda t: round(t - ref["Final time (s)"], 3) if t is not None else None
            )
            df["Δvelocity vs dry (m/s)"] = df["Final velocity (m/s)"].apply(
                lambda v: round(v - ref["Final velocity (m/s)"], 2) if v is not None else None
            )

    st.subheader("Summary")
    st.dataframe(df.set_index("Scenario"), use_container_width=True)

    # --- Overlaid plots -----------------------------------------------

    st.subheader("Overlaid traces")
    plot_choices = [
        ("Velocity", plots.velocity_plot),
        ("Acceleration", plots.acceleration_plot),
        ("Tire forces", plots.tire_forces_plot),
        ("Slip", plots.slip_plot),
        ("Power", plots.power_plot),
    ]
    # Add tyre-temp plot if thermal model is on.
    if bool(base_data.get("tires", {}).get("thermal_model_enabled", False)):
        plot_choices.append(("Tyre temperature", plots.tyre_temp_plot))

    tabs = st.tabs([name for name, _ in plot_choices])
    for tab, (name, builder) in zip(tabs, plot_choices):
        with tab:
            fig = None
            for scenario_name, outcome in outcomes.items():
                if outcome.ok:
                    fig = builder(outcome.history, label=scenario_name, fig=fig)
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No valid scenarios to plot.")

    # --- CSV export --------------------------------------------------

    csv = df.to_csv(index=False)
    st.download_button(
        "Download summary CSV",
        data=csv,
        file_name=f"track_conditions_{base_name}.csv",
        mime="text/csv",
    )

    # --- Report notes -----------------------------------------------

    with st.expander("Report notes"):
        st.markdown(
            """
- The only parameter that changes between scenarios is
  `environment.surface_mu_scaling` (plus ambient / initial tyre
  temperature if the thermal model is enabled). This is a deliberate
  choice: it isolates the **grip** effect of the surface from
  everything else.
- Dry (reference) typically shows the car is **traction-limited** in
  phase 2; wet scenarios push the transition to **power-limited** much
  later or never, because peak tyre force falls below what the motor
  can dump through the driveline.
- The wheelie flag can flip when μ changes: on dry tyres the CG/weight-
  transfer pair lives close to the wheelie boundary; on wet it backs
  away.
- Tick "Dry (reference)" to get the Δ columns; leave it out to compare
  only non-dry scenarios.
            """
        )
else:
    st.info(
        "Pick a base config, select the scenarios to compare, then click "
        "**Run scenarios**. Tick 'Dry (reference)' to get Δ columns vs "
        "the dry baseline."
    )
