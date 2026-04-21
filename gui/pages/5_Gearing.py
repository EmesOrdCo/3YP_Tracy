"""Gear-ratio envelope plot.

Sweeps ``powertrain.gear_ratio`` against a single base config and, for each
ratio, runs a full 0-75 m simulation. Two things make this page more useful
than the generic parameter sweep:

1. It classifies **which phase the car finishes in** (traction-limited,
   power-limited, or motor-speed-saturated) and shades the gear-ratio axis
   accordingly. The "best" gear is the one that just barely stays inside the
   power-limited band.

2. It overlays the motor speed reached at the finish line against the
   motor's spec limit, so it is obvious when a gear ratio is too short
   (motor saturates before 75 m and acceleration collapses in the final
   tenths of a second).

The analysis directly reflects the physics we discussed in the audit: the
optimiser was previously choosing gears that saturated the motor just before
the line. Use this page to sanity-check the optimised gear choice against the
whole neighbourhood.
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

from gui._core import sim_runner
from gui._core.config_io import list_configs, load_as_dict


# --- Phase classification -------------------------------------------------

PHASE_SATURATED = "motor saturated"
PHASE_POWER = "power-limited"
PHASE_TRACTION = "traction-limited"

PHASE_COLORS = {
    PHASE_SATURATED: "rgba(239, 68, 68, 0.18)",   # red
    PHASE_POWER: "rgba(34, 197, 94, 0.18)",       # green
    PHASE_TRACTION: "rgba(251, 191, 36, 0.18)",   # amber
}


def _classify_phase(history: pd.DataFrame, result, motor_max_speed: float) -> str:
    """Decide which phase the car was in at the finish line.

    - If the motor has saturated (ω_motor >= max_speed) at any point in the
      last 200 ms of the run, we call it motor-saturated.
    - Otherwise, if the power sits at or above 75 kW in the last 500 ms, it's
      power-limited.
    - Otherwise the car never needed the full 80 kW envelope, so call it
      traction-limited.

    The 200 ms window is chosen to catch the "4th-phase" motor-speed-limit
    behaviour we discussed in the audit - even a brief dip into saturation
    near the line dominates the acceleration trace.
    """
    if history.empty:
        return PHASE_TRACTION
    t_end = result.final_time

    tail = history[history["time"] >= t_end - 0.2]
    if "motor_speed" in tail.columns and tail["motor_speed"].max() >= 0.995 * motor_max_speed:
        return PHASE_SATURATED

    power_tail = history[history["time"] >= t_end - 0.5]
    if "power_consumed" in power_tail.columns:
        peak_kw = power_tail["power_consumed"].max() / 1000.0
        if peak_kw >= 75.0:
            return PHASE_POWER

    return PHASE_TRACTION


# --- Page setup -----------------------------------------------------------

st.set_page_config(page_title="Gearing Envelope", page_icon=":gear:", layout="wide")
st.title("Gear Ratio Envelope")

st.caption(
    "Sweeps `powertrain.gear_ratio` against a fixed base config and shows "
    "75 m time + finish motor speed across the range. Background shading "
    "identifies which phase (traction / power / motor-saturated) the car is "
    "in at the finish line. The fastest valid gear is marked."
)

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

default_idx = (
    configs.index("optimized_vehicle") if "optimized_vehicle" in configs
    else configs.index("base_vehicle") if "base_vehicle" in configs
    else 0
)
base_name = st.selectbox("Base config", configs, index=default_idx)
base_data = load_as_dict(base_name)

c1, c2, c3, c4 = st.columns(4)
with c1:
    lo = st.number_input("Gear ratio min", min_value=2.0, max_value=15.0,
                         value=3.0, step=0.1)
with c2:
    hi = st.number_input("Gear ratio max", min_value=2.0, max_value=15.0,
                         value=8.0, step=0.1)
with c3:
    n_points = st.number_input("Points", min_value=5, max_value=100,
                               value=30, step=1)
with c4:
    search_dt = st.number_input("dt (s)", min_value=0.001, max_value=0.02,
                                value=0.005, step=0.001, format="%.3f",
                                help="Coarser = faster sweep. 0.005 s is a good balance.")

run_clicked = st.button("Sweep gear ratio", type="primary")

# --- Execution ------------------------------------------------------------

if run_clicked:
    if hi <= lo:
        st.error("Gear ratio max must exceed min.")
        st.stop()

    motor_max_speed = float(
        base_data.get("powertrain", {}).get("motor_max_speed", 838.0)
    )
    tyre_radius = float(
        base_data.get("tires", {}).get("radius_loaded", 0.25)
    )

    gear_values = np.linspace(float(lo), float(hi), int(n_points))
    rows = []
    progress = st.progress(0.0, text="Running gear sweep...")

    for i, g in enumerate(gear_values):
        data = copy.deepcopy(base_data)
        data.setdefault("powertrain", {})["gear_ratio"] = float(g)
        data.setdefault("simulation", {})
        data["simulation"]["dt"] = float(search_dt)
        data["simulation"]["max_time"] = 15.0

        outcome = sim_runner.run(data)
        if not outcome.ok:
            rows.append({
                "gear_ratio": float(g),
                "time": np.nan,
                "v_finish": np.nan,
                "motor_speed_finish": np.nan,
                "wheelie": True,
                "phase": PHASE_TRACTION,
                "compliant": False,
                "error": "; ".join(outcome.errors),
            })
        else:
            r = outcome.result
            phase = _classify_phase(outcome.history, r, motor_max_speed)
            rows.append({
                "gear_ratio": float(g),
                "time": float(r.final_time),
                "v_finish": float(r.final_velocity),
                "motor_speed_finish": float(
                    outcome.history.iloc[-1]["motor_speed"]
                    if "motor_speed" in outcome.history.columns else 0.0
                ),
                "wheelie": bool(r.wheelie_detected),
                "phase": phase,
                "compliant": bool(r.compliant),
                "error": "",
            })
        progress.progress((i + 1) / len(gear_values))
    progress.empty()

    df = pd.DataFrame(rows)

    # --- Figure: time vs gear ratio with phase shading --------------------

    fig_time = go.Figure()

    # Shaded background bands by phase — compute contiguous runs.
    phases = df["phase"].tolist()
    start_idx = 0
    for i in range(1, len(phases) + 1):
        if i == len(phases) or phases[i] != phases[start_idx]:
            x0 = df["gear_ratio"].iloc[start_idx]
            x1 = df["gear_ratio"].iloc[min(i, len(df) - 1)]
            # Extend each band half a step left/right for visual continuity.
            if start_idx > 0:
                x0 -= (df["gear_ratio"].iloc[start_idx]
                       - df["gear_ratio"].iloc[start_idx - 1]) / 2
            if i < len(df):
                x1 += (df["gear_ratio"].iloc[i]
                       - df["gear_ratio"].iloc[i - 1]) / 2
            fig_time.add_vrect(
                x0=x0, x1=x1,
                fillcolor=PHASE_COLORS.get(phases[start_idx], "rgba(200,200,200,0.1)"),
                line_width=0,
                annotation_text=phases[start_idx] if i - start_idx >= 2 else None,
                annotation_position="top left",
                annotation=dict(font=dict(size=10), opacity=0.6),
            )
            start_idx = i

    # Time curve.
    valid = df["compliant"] & df["time"].notna()
    fig_time.add_trace(go.Scatter(
        x=df.loc[valid, "gear_ratio"],
        y=df.loc[valid, "time"],
        mode="lines+markers",
        name="Valid 75 m time",
        line=dict(color="#1f77b4", width=2),
    ))

    # Non-compliant / wheelie runs as red X.
    bad = ~df["compliant"]
    if bad.any():
        fig_time.add_trace(go.Scatter(
            x=df.loc[bad, "gear_ratio"],
            y=df.loc[bad, "time"],
            mode="markers",
            name="Non-compliant",
            marker=dict(symbol="x", size=11, color="#ef4444"),
        ))

    # Mark the best valid gear.
    if valid.any():
        best_idx = df.loc[valid, "time"].idxmin()
        g_best = df.loc[best_idx, "gear_ratio"]
        t_best = df.loc[best_idx, "time"]
        fig_time.add_trace(go.Scatter(
            x=[g_best], y=[t_best],
            mode="markers",
            name=f"Best: gear={g_best:.2f}, t={t_best:.3f} s",
            marker=dict(symbol="star", size=18, color="gold",
                        line=dict(color="black", width=1)),
        ))
        st.success(
            f"Best compliant gear ratio: **{g_best:.2f}** → "
            f"**{t_best:.3f} s**, finish velocity "
            f"**{df.loc[best_idx, 'v_finish']:.1f} m/s**, "
            f"motor speed at finish "
            f"**{df.loc[best_idx, 'motor_speed_finish']:.0f} rad/s** "
            f"({100 * df.loc[best_idx, 'motor_speed_finish'] / motor_max_speed:.0f}% of max)."
        )

    fig_time.update_layout(
        title="Final 75 m time vs gear ratio",
        xaxis_title="Gear ratio",
        yaxis_title="Final time (s)",
        template="plotly_white",
        hovermode="x unified",
    )
    st.plotly_chart(fig_time, use_container_width=True)

    # --- Figure: motor speed at finish vs gear ratio ----------------------

    fig_motor = go.Figure()
    fig_motor.add_hline(
        y=motor_max_speed, line=dict(color="#ef4444", dash="dash"),
        annotation_text=f"motor_max_speed = {motor_max_speed:.0f} rad/s",
        annotation_position="top right",
    )
    fig_motor.add_trace(go.Scatter(
        x=df["gear_ratio"], y=df["motor_speed_finish"],
        mode="lines+markers",
        name="Motor speed at 75 m",
        line=dict(color="#7c3aed", width=2),
    ))
    fig_motor.update_layout(
        title="Motor speed at finish line vs gear ratio",
        xaxis_title="Gear ratio",
        yaxis_title="Motor speed at finish (rad/s)",
        template="plotly_white",
        hovermode="x unified",
    )
    st.plotly_chart(fig_motor, use_container_width=True)

    st.caption(
        "Red band = motor saturated before the line (acceleration collapses "
        "in the last tenths of a second). Green band = good: power-limited to "
        "the finish. Amber = traction never runs out — either the tyres have "
        "too little grip or the car has too much power for the traction "
        "available."
    )

    with st.expander("Sweep data table"):
        st.dataframe(df.set_index("gear_ratio"), use_container_width=True)

else:
    st.info(
        "Pick a base config, choose a gear-ratio range, and click "
        "**Sweep gear ratio**."
    )
