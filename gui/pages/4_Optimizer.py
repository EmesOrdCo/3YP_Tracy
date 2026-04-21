"""Nelder-Mead optimisation of a chosen subset of decision variables."""

from pathlib import Path
import sys

_PKG_ROOT = Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

import pandas as pd
import streamlit as st

from gui._core import optimizer, plots, sim_runner
from gui._core.config_io import (
    config_path,
    deep_copy_dict,
    dict_to_config,
    list_configs,
    load_as_dict,
    save_config,
)


st.set_page_config(page_title="Optimizer", page_icon=":racing_car:", layout="wide")
st.title("Optimizer (Nelder-Mead)")

st.markdown(
    "Select which decision variables to optimise, set their bounds, and run "
    "multi-start Nelder-Mead. The objective is final 0-75 m time with "
    "penalties for FS rule violations (power / time / wheelie / under-distance)."
)

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

default_idx = configs.index("base_vehicle") if "base_vehicle" in configs else 0
base_name = st.selectbox("Base config", configs, index=default_idx)
base_data = load_as_dict(base_name)

st.subheader("Decision variables")

# Per-variable toggles + editable bounds.
base_cfg = dict_to_config(base_data)
selected_vars = []
selected_bounds = []
columns = st.columns(2)
for idx, (name, meta) in enumerate(optimizer.VARIABLES.items()):
    col = columns[idx % 2]
    with col:
        with st.container(border=True):
            default_on = name in ("cg_x_ratio", "gear_ratio", "radius_loaded",
                                  "target_slip_ratio", "launch_torque_limit")
            enabled = st.checkbox(meta["label"], value=default_on, key=f"opt_use_{name}")
            lo_default, hi_default = meta["bounds"]
            try:
                current = float(meta["get_default"](base_cfg))
            except Exception:  # noqa: BLE001
                current = 0.5 * (lo_default + hi_default)
            st.caption(f"Current base value: {current:.4f}")
            bc1, bc2 = st.columns(2)
            with bc1:
                lo = st.number_input("min", value=float(lo_default),
                                     key=f"opt_lo_{name}", format="%.4f",
                                     disabled=not enabled)
            with bc2:
                hi = st.number_input("max", value=float(hi_default),
                                     key=f"opt_hi_{name}", format="%.4f",
                                     disabled=not enabled)
            if enabled:
                if hi <= lo:
                    st.warning(f"{name}: max must be greater than min.")
                else:
                    selected_vars.append(name)
                    selected_bounds.append((float(lo), float(hi)))

st.subheader("Search settings")
sc1, sc2, sc3 = st.columns(3)
with sc1:
    n_starts = st.number_input("Random restarts", min_value=1, max_value=20,
                               value=5, step=1)
with sc2:
    max_iter = st.number_input("Max Nelder-Mead iters / start",
                               min_value=50, max_value=1000, value=200, step=10)
with sc3:
    search_dt = st.number_input("Search dt (s)", min_value=0.001, max_value=0.02,
                                value=0.005, step=0.001, format="%.3f",
                                help="Larger = faster search, but dt > 0.005 s "
                                     "biases the optimiser towards the wrong "
                                     "decision variables for this vehicle.")

apply_presets = st.checkbox(
    "Apply run_quick_optimization.py preset pins (MINIMIZE / MAXIMIZE / FIXED)",
    value=False,
    help=(
        "When ticked, overlay the same MINIMIZE/MAXIMIZE/FIXED_PARAMS used by the "
        "CLI script run_quick_optimization.py on top of the base config before "
        "optimising. Without this, the optimiser runs on the base config as-is, "
        "which will generally give different results from the CLI script."
    ),
)

run_clicked = st.button("Run optimisation", type="primary",
                        disabled=(len(selected_vars) == 0))

if not selected_vars:
    st.info("Enable at least one decision variable above.")
    st.stop()

# --- Run ---

if run_clicked:
    status = st.status("Starting optimiser...", expanded=True)
    progress_bar = status.progress(0.0)
    log_placeholder = status.empty()

    def on_progress(p: optimizer.OptimizationProgress) -> None:
        progress_bar.progress(min(p.start_index / max(p.total_starts, 1), 1.0))
        log_placeholder.write(
            f"Start {p.start_index}/{p.total_starts} - "
            f"evals: {p.evaluations} - "
            f"best objective so far: "
            f"{p.best_time:.4f} s"
            if p.best_time < float("inf") else
            f"Start {p.start_index}/{p.total_starts} - searching..."
        )

    try:
        result = optimizer.optimize(
            base_data, selected_vars, selected_bounds,
            n_starts=int(n_starts),
            max_iter=int(max_iter),
            search_dt=float(search_dt),
            apply_presets=bool(apply_presets),
            progress_callback=on_progress,
        )
    except Exception as exc:  # noqa: BLE001
        status.update(label="Optimisation failed", state="error")
        st.exception(exc)
        st.stop()

    status.update(label=f"Done in {result.elapsed_s:.1f} s "
                        f"({result.n_evaluations} evaluations)",
                  state="complete")
    st.session_state["opt_last_result"] = result
    st.session_state["opt_last_base_name"] = base_name

# --- Results display ---

if "opt_last_result" in st.session_state:
    result: optimizer.OptimizationResult = st.session_state["opt_last_result"]
    r = result.final_simulation_result

    st.subheader("Best result")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Final time", f"{r.final_time:.3f} s")
    m2.metric("Final velocity", f"{r.final_velocity:.1f} m/s",
              f"{r.final_velocity * 3.6:.1f} km/h")
    m3.metric("Max power", f"{r.max_power_used / 1000:.2f} kW")
    m4.metric("Evaluations", f"{result.n_evaluations}")

    b1, b2, b3 = st.columns(3)
    b1.success("Power OK") if r.power_compliant else b1.error("Power VIOLATED")
    b2.success("Time OK") if r.time_compliant else b2.error("Time VIOLATED")
    (b3.error(f"Wheelie at t={r.wheelie_time:.3f}s")
     if r.wheelie_detected else b3.success("No wheelie"))

    st.subheader("Optimised variables")
    base_cfg_for_delta = dict_to_config(base_data)
    rows = []
    for name, value in result.best_variables.items():
        try:
            base_val = float(optimizer.VARIABLES[name]["get_default"](base_cfg_for_delta))
        except Exception:  # noqa: BLE001
            base_val = float("nan")
        lo, hi = dict(zip(result.variable_names, result.bounds))[name]
        rows.append({
            "variable": name,
            "label": optimizer.VARIABLES[name]["label"],
            "base value": round(base_val, 6),
            "optimised value": round(value, 6),
            "bounds": f"[{lo:.4f}, {hi:.4f}]",
        })
    st.dataframe(pd.DataFrame(rows).set_index("variable"),
                 use_container_width=True)

    # Overlay base vs optimised traces.
    st.subheader("Traces (base vs optimised)")
    base_outcome = sim_runner.run(base_data, fastest_time=4.5)
    opt_outcome = sim_runner.run(result.best_config_dict, fastest_time=4.5)

    tabs = st.tabs(["Velocity", "Acceleration", "Power", "Normal forces"])
    builders = [plots.velocity_plot, plots.acceleration_plot,
                plots.power_plot, plots.normal_forces_plot]
    for tab, builder in zip(tabs, builders):
        with tab:
            fig = None
            if base_outcome.ok:
                fig = builder(base_outcome.history, label=f"base ({base_name})", fig=fig)
            if opt_outcome.ok:
                fig = builder(opt_outcome.history, label="optimised", fig=fig)
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

    # Save-as-new-config action.
    st.subheader("Save optimised config")
    with st.form("opt_save_form"):
        save_name = st.text_input("New config name (no extension)",
                                  value=f"{base_name}_opt")
        submitted = st.form_submit_button("Save JSON")
        if submitted:
            target = config_path(save_name)
            if target.exists():
                st.error(f"{target.name} already exists. Choose a different name.")
            else:
                out = save_config(save_name, deep_copy_dict(result.best_config_dict))
                st.success(f"Saved to {out}")
