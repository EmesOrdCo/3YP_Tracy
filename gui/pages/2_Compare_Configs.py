"""Compare multiple saved configs on a single page with overlaid plots."""

from pathlib import Path
import sys

_PKG_ROOT = Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

import pandas as pd
import streamlit as st

from gui._core import plots, sim_runner
from gui._core.config_io import list_configs, load_as_dict


st.set_page_config(page_title="Compare Configs", page_icon=":bar_chart:", layout="wide")
st.title("Compare Configs")

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

st.markdown(
    "Pick two or more configurations to overlay velocity, acceleration, power and "
    "normal-force traces, along with a summary table."
)

default_selection = [c for c in ("base_vehicle", "optimized_vehicle",
                                 "supercapacitor_vehicle") if c in configs]
if not default_selection:
    default_selection = configs[: min(2, len(configs))]

selection = st.multiselect("Configs to compare", configs, default=default_selection)

include_current_edits = False
if "p1_current_config" in st.session_state:
    include_current_edits = st.checkbox(
        "Include Single Run page's unsaved edits as an extra overlay", value=False
    )

if not selection and not include_current_edits:
    st.info("Select at least one config (or enable the Single Run edits overlay).")
    st.stop()

# --- Run each and collect ------------------------------------------------

runs = []  # list of (label, outcome)
for name in selection:
    runs.append((name, sim_runner.run(load_as_dict(name))))
if include_current_edits:
    runs.append(("(current edits)",
                 sim_runner.run(st.session_state["p1_current_config"])))

good_runs = [(lbl, o) for lbl, o in runs if o.ok]
bad_runs = [(lbl, o) for lbl, o in runs if not o.ok]

if bad_runs:
    with st.expander(f"{len(bad_runs)} config(s) failed to run", expanded=True):
        for lbl, o in bad_runs:
            st.error(f"**{lbl}**: {'; '.join(o.errors)}")

if not good_runs:
    st.stop()

# --- Summary table --------------------------------------------------------

rows = []
for lbl, o in good_runs:
    r = o.result
    rows.append({
        "Config": lbl,
        "Time (s)": round(r.final_time, 3),
        "Velocity (m/s)": round(r.final_velocity, 2),
        "Velocity (km/h)": round(r.final_velocity * 3.6, 1),
        "Max power (kW)": round(r.max_power_used / 1000, 2),
        "Distance (m)": round(r.final_distance, 2),
        "Power OK": r.power_compliant,
        "Time OK": r.time_compliant,
        "Wheelie": r.wheelie_detected,
    })
summary = pd.DataFrame(rows).set_index("Config")
st.subheader("Summary")
st.dataframe(summary, use_container_width=True)

# --- Overlaid plots -------------------------------------------------------

st.subheader("Overlaid traces")

builders = [
    ("Velocity", plots.velocity_plot),
    ("Acceleration", plots.acceleration_plot),
    ("Power", plots.power_plot),
    ("Normal forces", plots.normal_forces_plot),
    ("Tire forces", plots.tire_forces_plot),
    ("Slip", plots.slip_plot),
]

tabs = st.tabs([name for name, _ in builders])

for tab, (name, builder) in zip(tabs, builders):
    with tab:
        fig = None
        for lbl, outcome in good_runs:
            fig = builder(outcome.history, label=lbl, fig=fig)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
