"""1D / 2D parameter sweep over a base config."""

from pathlib import Path
import sys

_PKG_ROOT = Path(__file__).resolve().parents[2]
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

import copy
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from gui._core import sim_runner
from gui._core.config_io import deep_copy_dict, list_configs, load_as_dict
from gui._core.param_schema import NUMERIC_PARAMS, find


st.set_page_config(page_title="Parameter Sweep", page_icon=":bar_chart:", layout="wide")
st.title("Parameter Sweep")

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

# --- Base config selection ------------------------------------------------

default_idx = configs.index("base_vehicle") if "base_vehicle" in configs else 0
base_name = st.selectbox("Base config", configs, index=default_idx)
base_data = load_as_dict(base_name)

mode = st.radio("Sweep dimensionality", ["1D (line)", "2D (heatmap)"], horizontal=True)
is_2d = mode.startswith("2D")

c_dt, c_maxt = st.columns(2)
with c_dt:
    search_dt = st.number_input(
        "Search dt (s)", min_value=0.001, max_value=0.05, value=0.01, step=0.001,
        format="%.3f",
        help="Coarser = faster. 0.001 matches CLI accuracy but is slow for sweeps; "
             "0.01-0.02 is usually fine for exploration.",
    )
with c_maxt:
    search_max_time = st.number_input(
        "Search max time (s)", min_value=5.0, max_value=30.0, value=15.0, step=1.0,
        help="Hard cap per simulation; lower means faster sweeps for bad configs.",
    )

param_options = [p.dotted for p in NUMERIC_PARAMS]


def _param_picker(label_prefix: str, default: str, *, key: str,
                  default_steps: int) -> dict:
    """Render sweep inputs for one parameter and return a config dict."""
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        dotted = st.selectbox(f"{label_prefix} parameter", param_options,
                              index=param_options.index(default)
                              if default in param_options else 0,
                              key=f"{key}_param")
    spec = find(dotted)
    base_val = base_data.get(spec.section, {}).get(spec.key, spec.min or 0.0)
    lo_default = float(spec.min) if spec.min is not None else float(base_val) * 0.5
    hi_default = float(spec.max) if spec.max is not None else float(base_val) * 1.5
    with col2:
        lo = st.number_input(f"{label_prefix} min", value=lo_default,
                             step=float(spec.step or 0.01), key=f"{key}_min")
    with col3:
        hi = st.number_input(f"{label_prefix} max", value=hi_default,
                             step=float(spec.step or 0.01), key=f"{key}_max")
    with col4:
        n = st.number_input(f"{label_prefix} steps", min_value=2, max_value=100,
                            value=default_steps, step=1, key=f"{key}_n")
    if hi <= lo:
        st.warning(f"{label_prefix}: max must be greater than min.")
    return {"spec": spec, "values": np.linspace(lo, hi, int(n))}


x_cfg = _param_picker("X-axis", "mass.cg_x", key="sw_x",
                      default_steps=20 if not is_2d else 10)
y_cfg = None
if is_2d:
    y_cfg = _param_picker("Y-axis", "powertrain.gear_ratio", key="sw_y",
                          default_steps=10)

run_clicked = st.button("Run sweep", type="primary")

# --- Execution ------------------------------------------------------------

def _run_point(base: dict, updates: dict,
               *, dt_override: float, max_time_override: float) -> dict:
    """Run sim with a modified copy of base; return summary dict."""
    data = copy.deepcopy(base)
    for (section, key), value in updates.items():
        data.setdefault(section, {})[key] = float(value)
    # Override search-time simulation params for speed.
    data.setdefault("simulation", {})
    data["simulation"]["dt"] = float(dt_override)
    data["simulation"]["max_time"] = float(max_time_override)
    outcome = sim_runner.run(data)
    if not outcome.ok:
        return {"time": np.nan, "power_ok": False, "time_ok": False,
                "wheelie": True, "max_power_kw": np.nan,
                "distance": np.nan, "error": "; ".join(outcome.errors)}
    r = outcome.result
    return {
        "time": float(r.final_time),
        "power_ok": bool(r.power_compliant),
        "time_ok": bool(r.time_compliant),
        "wheelie": bool(r.wheelie_detected),
        "max_power_kw": r.max_power_used / 1000.0,
        "distance": float(r.final_distance),
        "error": "",
    }


if run_clicked:
    x_spec = x_cfg["spec"]
    x_vals = x_cfg["values"]

    if not is_2d:
        # 1D sweep
        progress = st.progress(0.0, text="Running sweep...")
        rows = []
        for i, xv in enumerate(x_vals):
            updates = {(x_spec.section, x_spec.key): xv}
            res = _run_point(base_data, updates,
                             dt_override=search_dt,
                             max_time_override=search_max_time)
            res[x_spec.dotted] = float(xv)
            rows.append(res)
            progress.progress((i + 1) / len(x_vals))
        progress.empty()
        df = pd.DataFrame(rows)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[x_spec.dotted], y=df["time"],
                                 mode="lines+markers", name="Final time (s)"))
        non_compliant = ~df["power_ok"] | ~df["time_ok"] | df["wheelie"]
        if non_compliant.any():
            fig.add_trace(go.Scatter(
                x=df.loc[non_compliant, x_spec.dotted],
                y=df.loc[non_compliant, "time"],
                mode="markers",
                marker=dict(color="red", size=10, symbol="x"),
                name="Non-compliant",
            ))
        fig.update_layout(
            title=f"Final 0-{base_data.get('simulation', {}).get('target_distance', 75):.0f} m "
                  f"time vs {x_spec.label}",
            xaxis_title=f"{x_spec.label} ({x_spec.unit})" if x_spec.unit else x_spec.label,
            yaxis_title="Final time (s)",
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Sweep data table"):
            st.dataframe(df, use_container_width=True)

    else:
        # 2D sweep
        y_spec = y_cfg["spec"]
        y_vals = y_cfg["values"]
        total = len(x_vals) * len(y_vals)
        progress = st.progress(0.0, text=f"Running {total} simulations...")

        time_grid = np.full((len(y_vals), len(x_vals)), np.nan)
        compliant_grid = np.zeros_like(time_grid, dtype=bool)
        rows = []
        done = 0

        for i, yv in enumerate(y_vals):
            for j, xv in enumerate(x_vals):
                updates = {
                    (x_spec.section, x_spec.key): xv,
                    (y_spec.section, y_spec.key): yv,
                }
                res = _run_point(base_data, updates,
                                 dt_override=search_dt,
                                 max_time_override=search_max_time)
                time_grid[i, j] = res["time"]
                compliant_grid[i, j] = (res["power_ok"] and res["time_ok"]
                                         and not res["wheelie"])
                rows.append({x_spec.dotted: xv, y_spec.dotted: yv, **res})
                done += 1
                progress.progress(done / total)
        progress.empty()

        heat = go.Heatmap(
            x=x_vals, y=y_vals, z=time_grid,
            colorscale="Viridis_r",
            colorbar=dict(title="Time (s)"),
            hovertemplate=(f"{x_spec.label}: %{{x:.3f}}<br>"
                           f"{y_spec.label}: %{{y:.3f}}<br>"
                           "Final time: %{z:.3f} s<extra></extra>"),
        )
        fig = go.Figure(data=[heat])

        # Overlay red crosses where non-compliant.
        ys_nc, xs_nc = np.where(~compliant_grid)
        if xs_nc.size:
            fig.add_trace(go.Scatter(
                x=x_vals[xs_nc], y=y_vals[ys_nc],
                mode="markers",
                marker=dict(color="red", symbol="x", size=8, opacity=0.7),
                name="Non-compliant",
                showlegend=True,
            ))

        # Mark the grid cell with the best (min) time.
        if np.isfinite(time_grid).any():
            best_flat = np.nanargmin(time_grid)
            by, bx = np.unravel_index(best_flat, time_grid.shape)
            fig.add_trace(go.Scatter(
                x=[x_vals[bx]], y=[y_vals[by]],
                mode="markers",
                marker=dict(color="gold", symbol="star", size=16,
                            line=dict(color="black", width=1)),
                name=f"Best: {time_grid[by, bx]:.3f} s",
                showlegend=True,
            ))

        fig.update_layout(
            title=f"Final time heatmap over {x_spec.label} x {y_spec.label}",
            xaxis_title=f"{x_spec.label} ({x_spec.unit})" if x_spec.unit else x_spec.label,
            yaxis_title=f"{y_spec.label} ({y_spec.unit})" if y_spec.unit else y_spec.label,
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Sweep data table"):
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
else:
    st.info("Configure the sweep above and click **Run sweep**.")
