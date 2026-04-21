"""Single acceleration run: edit params in the sidebar, see metrics + plots."""

from pathlib import Path
import sys

_PKG_ROOT = Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

import streamlit as st

from gui._core import sim_runner
from gui._core.config_io import (
    config_path,
    deep_copy_dict,
    list_configs,
    load_as_dict,
    save_config,
)
from gui._core import plots
from gui._core.widgets import render_param_sidebar


st.set_page_config(page_title="Single Run", page_icon=":racing_car:", layout="wide")
st.title("Single Run")

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

# --- Sidebar: config selection + param editing -----------------------------

st.sidebar.header("Base config")
default_idx = configs.index("base_vehicle") if "base_vehicle" in configs else 0
base_name = st.sidebar.selectbox("Select base config", configs, index=default_idx,
                                 key="p1_base_select")

# Track which config was last loaded so the "Reset" button can force a reload.
if ("p1_loaded_name" not in st.session_state
        or st.session_state["p1_loaded_name"] != base_name
        or st.session_state.get("p1_reset_flag", False)):
    st.session_state["p1_current_config"] = load_as_dict(base_name)
    st.session_state["p1_loaded_name"] = base_name
    st.session_state["p1_reset_flag"] = False
    # Clear per-widget state so values refresh from the freshly-loaded config.
    for k in list(st.session_state.keys()):
        if k.startswith("p1_") and k not in {"p1_base_select", "p1_loaded_name",
                                              "p1_current_config", "p1_reset_flag"}:
            del st.session_state[k]
    st.rerun()

col_reset, col_save = st.sidebar.columns(2)
with col_reset:
    if st.button("Reset to base", key="p1_reset_btn"):
        st.session_state["p1_reset_flag"] = True
        st.rerun()
with col_save:
    save_clicked = st.button("Save as new...", key="p1_save_btn")

st.sidebar.divider()
st.sidebar.header("Parameters")

current_data = render_param_sidebar(st.session_state["p1_current_config"],
                                    key_prefix="p1")
st.session_state["p1_current_config"] = current_data

st.sidebar.divider()
# Scoring is de-emphasised; we focus on timed runs. Pass a placeholder
# fastest_time so the SimulationResult still populates, but it's not shown.
fastest_time = 4.5

# --- Save-as-new-config dialog -------------------------------------------

if save_clicked:
    st.session_state["p1_show_save_form"] = True

if st.session_state.get("p1_show_save_form"):
    with st.sidebar.form("p1_save_form"):
        st.write("Save current edits as a new JSON config:")
        new_name = st.text_input("Config name (no extension)",
                                 value=f"{base_name}_edited")
        submitted = st.form_submit_button("Save")
        if submitted:
            target = config_path(new_name)
            if target.exists():
                st.sidebar.error(f"{target.name} already exists.")
            else:
                out = save_config(new_name, deep_copy_dict(current_data))
                st.sidebar.success(f"Saved to {out}")
                st.session_state["p1_show_save_form"] = False
                st.rerun()

# --- Run simulation --------------------------------------------------------

outcome = sim_runner.run(current_data, fastest_time=fastest_time)

if not outcome.ok:
    st.error("Simulation could not run with the current configuration:")
    for err in outcome.errors:
        st.markdown(f"- {err}")
    st.stop()

r = outcome.result
df = outcome.history

# --- Top row: headline metrics --------------------------------------------

if r.wheelie_detected:
    st.error(
        "Wheelie detected — this run is **invalid**. Front wheels lifted at "
        f"t = {r.wheelie_time:.3f} s, so lateral stability and steering are "
        "lost. The reported time below is not physically meaningful; treat it "
        "as DNF. Reduce launch torque, shift CG forward, add anti-squat or "
        "lower CG height to keep the front planted."
    )

time_label = "Final time" if not r.wheelie_detected else "Final time (INVALID)"
time_str = (f"{r.final_time:.3f} s" if not r.wheelie_detected
            else f"{r.final_time:.3f} s — DNF")

m1, m2, m3, m4 = st.columns(4)
m1.metric(time_label, time_str)
m2.metric("Final velocity", f"{r.final_velocity:.1f} m/s",
          f"{r.final_velocity * 3.6:.1f} km/h")
m3.metric("Max power", f"{r.max_power_used / 1000:.2f} kW")
m4.metric("Final distance", f"{r.final_distance:.2f} m")

# --- Compliance badges ----------------------------------------------------

def _badge(col, label: str, ok: bool, detail: str = "") -> None:
    marker = "PASS" if ok else "FAIL"
    body = f"**{label}**: {marker}"
    if detail:
        body += f"  \n_{detail}_"
    if ok:
        col.success(body)
    else:
        col.error(body)

b1, b2, b3 = st.columns(3)
_badge(b1, "Power (EV 2.2, <= 80 kW)", r.power_compliant,
       f"Max {r.max_power_used / 1000:.2f} kW")
_badge(b2, "Time (<= 25 s)", r.time_compliant,
       f"{r.final_time:.2f} s")
wheelie_detail = (f"Min front Fz = {r.min_front_normal_force:.2f} N"
                  if not r.wheelie_detected
                  else f"Lift-off at t={r.wheelie_time:.3f} s")
_badge(b3, "No wheelie", not r.wheelie_detected, wheelie_detail)

st.caption(
    f"Target distance: {current_data.get('simulation', {}).get('target_distance', 75):.1f} m"
)

st.divider()

# --- Plot tabs -------------------------------------------------------------

tab_labels = ["Velocity", "Acceleration", "Power", "Normal forces",
              "Tire forces", "Slip", "Distance"]
is_supercap = (current_data.get("powertrain", {}).get("energy_storage_type")
               == "supercapacitor")
if is_supercap:
    tab_labels += ["Energy storage"]

tabs = st.tabs(tab_labels)

with tabs[0]:
    st.plotly_chart(plots.velocity_plot(df), use_container_width=True)
with tabs[1]:
    st.plotly_chart(plots.acceleration_plot(df), use_container_width=True)
with tabs[2]:
    st.plotly_chart(plots.power_plot(df), use_container_width=True)
with tabs[3]:
    st.plotly_chart(plots.normal_forces_plot(df), use_container_width=True)
with tabs[4]:
    st.plotly_chart(plots.tire_forces_plot(df), use_container_width=True)
with tabs[5]:
    st.plotly_chart(plots.slip_plot(df), use_container_width=True)
with tabs[6]:
    st.plotly_chart(plots.distance_plot(df), use_container_width=True)
if is_supercap:
    with tabs[7]:
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(plots.soc_plot(df), use_container_width=True)
        with c2:
            st.plotly_chart(plots.voltage_plot(df), use_container_width=True)

with st.expander("Raw state history (first 500 samples)"):
    st.dataframe(df.head(500))
