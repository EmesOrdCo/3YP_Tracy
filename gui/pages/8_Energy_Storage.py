"""Battery vs supercapacitor energy-storage study.

Runs the same vehicle config twice - once with a Li-ion battery as the HV
storage, once with a supercapacitor stack - and shows the operational
differences across the 75 m run. The comparison produces:

- Headline time / velocity / peak-power deltas.
- DC bus voltage vs time (battery near-constant; supercap decays).
- Pack current vs time (supercap higher, because V drops so I must rise to
  hit the same power).
- Cumulative energy drawn from storage.
- State-of-charge trace.
- A set of "recommendation" bullets summarising the trade-off.

This is a direct answer to the report question "why would you pick one over
the other?", with data and figures you can drop straight into the report.
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


st.set_page_config(page_title="Battery vs Supercap", page_icon=":battery:", layout="wide")
st.title("Battery vs Supercapacitor Study")

st.caption(
    "Runs the same chassis twice, once with each energy storage technology, "
    "and compares the behaviour throughout the 75 m run. The motor, chassis, "
    "aero, controller, and driveline are identical; only the HV storage "
    "changes."
)

configs = list_configs()
if not configs:
    st.error("No configs found under config/vehicle_configs/.")
    st.stop()

default_idx = configs.index("optimized_vehicle") if "optimized_vehicle" in configs else 0
c_cfg, c_dt = st.columns([3, 1])
with c_cfg:
    base_name = st.selectbox("Base config", configs, index=default_idx)
with c_dt:
    search_dt = st.number_input("dt (s)", min_value=0.001, max_value=0.02,
                                value=0.005, step=0.001, format="%.3f")

st.subheader("Storage-specific parameters")

bat_col, cap_col = st.columns(2)

with bat_col:
    st.markdown("**Battery (lithium-ion pack)**")
    bat_nominal_v = st.number_input("Nominal pack voltage (V)",
                                    min_value=100.0, max_value=800.0,
                                    value=600.0, step=10.0,
                                    key="es_bat_v")
    bat_ir = st.number_input("Pack internal resistance (Ω)",
                             min_value=0.001, max_value=0.5, value=0.05,
                             step=0.005, format="%.3f", key="es_bat_r")
    bat_imax = st.number_input("Pack peak current (A)",
                               min_value=50.0, max_value=500.0,
                               value=300.0, step=5.0,
                               key="es_bat_i")

with cap_col:
    st.markdown("**Supercapacitor stack**")
    cap_nominal_v = st.number_input("Fully-charged pack voltage (V)",
                                    min_value=100.0, max_value=800.0,
                                    value=600.0, step=10.0,
                                    key="es_cap_v")
    cap_min_v = st.number_input("Minimum operating voltage (V)",
                                min_value=50.0, max_value=600.0,
                                value=350.0, step=5.0, key="es_cap_minv")
    cap_cells = st.number_input("Cells in series",
                                min_value=10.0, max_value=500.0,
                                value=200.0, step=1.0, key="es_cap_n")
    cap_cap = st.number_input("Capacitance per cell (F)",
                              min_value=10.0, max_value=3000.0,
                              value=600.0, step=10.0, key="es_cap_c")
    cap_esr = st.number_input("ESR per cell (Ω)",
                              min_value=1e-4, max_value=0.01,
                              value=0.0007, step=1e-4, format="%.4f",
                              key="es_cap_esr")

run_clicked = st.button("Run both scenarios", type="primary")


# --- Execution --------------------------------------------------------

def _apply(base: dict, storage_type: str) -> dict:
    data = copy.deepcopy(base)
    data.setdefault("simulation", {})["dt"] = float(search_dt)
    pt = data.setdefault("powertrain", {})
    pt["energy_storage_type"] = storage_type
    if storage_type == "battery":
        pt["battery_voltage_nominal"] = float(bat_nominal_v)
        pt["battery_internal_resistance"] = float(bat_ir)
        pt["battery_max_current"] = float(bat_imax)
    else:
        pt["battery_voltage_nominal"] = float(cap_nominal_v)
        pt["supercap_num_cells"] = int(cap_cells)
        pt["supercap_cell_voltage"] = float(cap_nominal_v) / int(cap_cells)
        pt["supercap_cell_capacitance"] = float(cap_cap)
        pt["supercap_cell_esr"] = float(cap_esr)
        pt["supercap_min_voltage"] = float(cap_min_v)
        # Stack-level IR = num_cells * esr (used as battery_internal_resistance
        # fallback in the powertrain model for the 80 kW cap derivation).
        pt["battery_internal_resistance"] = float(cap_esr) * int(cap_cells)
    return data


if run_clicked:
    base_data = load_as_dict(base_name)

    progress = st.progress(0.0, text="Running battery run...")
    bat_out = sim_runner.run(_apply(base_data, "battery"), use_cache=False)
    progress.progress(0.5, text="Running supercap run...")
    cap_out = sim_runner.run(_apply(base_data, "supercapacitor"), use_cache=False)
    progress.progress(1.0)
    progress.empty()

    if not bat_out.ok:
        st.error("Battery run failed: " + "; ".join(bat_out.errors))
        st.stop()
    if not cap_out.ok:
        st.error("Supercap run failed: " + "; ".join(cap_out.errors))
        st.stop()

    br, cr = bat_out.result, cap_out.result
    bh, ch = bat_out.history, cap_out.history

    # --- Headline metrics -------------------------------------------

    def _pack_current_kw(history: pd.DataFrame) -> float:
        """Peak pack current (A) = |P| / V, sampled across the run."""
        if history.empty or "dc_bus_voltage" not in history.columns:
            return 0.0
        p = history["power_consumed"].abs()
        v = history["dc_bus_voltage"].replace(0, np.nan)
        return float((p / v).max())

    def _energy_used_kj(history: pd.DataFrame) -> float:
        """Integrate |P| dt over the run, in kJ."""
        if history.empty or "power_consumed" not in history.columns:
            return 0.0
        t = history["time"].to_numpy()
        p = history["power_consumed"].abs().to_numpy()
        return float(np.trapz(p, t) / 1000.0)

    m_cols = st.columns(5)
    m_cols[0].metric("Final time (s)",
                     f"{br.final_time:.3f} / {cr.final_time:.3f}",
                     f"supercap {1000 * (cr.final_time - br.final_time):+.0f} ms")
    m_cols[1].metric("Final velocity (m/s)",
                     f"{br.final_velocity:.1f} / {cr.final_velocity:.1f}")
    m_cols[2].metric("Peak moving-avg power (kW)",
                     f"{br.max_power_used/1000:.1f} / {cr.max_power_used/1000:.1f}")
    m_cols[3].metric("Peak pack current (A)",
                     f"{_pack_current_kw(bh):.0f} / {_pack_current_kw(ch):.0f}",
                     help="Supercap usually higher because voltage sags under load so I = P/V rises.")
    m_cols[4].metric("Energy drawn (kJ)",
                     f"{_energy_used_kj(bh):.1f} / {_energy_used_kj(ch):.1f}",
                     help="Integrated |P| dt over the run.")

    st.caption(
        "Metric format: **battery / supercap**. The delta on final time tells "
        "you which technology is faster for this chassis."
    )

    # --- Plots ------------------------------------------------------

    def _overlay_plot(title: str, y_col: str, y_label: str,
                      y_scale: float = 1.0,
                      hline: float | None = None,
                      hline_label: str | None = None) -> go.Figure:
        fig = go.Figure()
        for label, hist, colour in (
            ("Battery", bh, "#2563eb"),
            ("Supercap", ch, "#ef4444"),
        ):
            if y_col in hist.columns:
                y = hist[y_col].to_numpy() * y_scale
                fig.add_trace(go.Scatter(
                    x=hist["time"], y=y, mode="lines",
                    name=label, line=dict(color=colour, width=2),
                ))
        if hline is not None:
            fig.add_hline(y=hline, line=dict(color="#555", dash="dash"),
                          annotation_text=hline_label,
                          annotation_position="top right")
        fig.update_layout(
            title=title, xaxis_title="Time (s)", yaxis_title=y_label,
            template="plotly_white", hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1.0),
        )
        return fig

    tabs = st.tabs(["DC bus voltage", "Power", "Pack current (est.)",
                    "Cumulative energy", "State of charge", "Velocity"])

    with tabs[0]:
        st.plotly_chart(_overlay_plot("DC bus voltage vs time",
                                      "dc_bus_voltage", "Voltage (V)"),
                        use_container_width=True)
        st.caption(
            "Battery voltage stays near nominal (only IR sag); supercap "
            "voltage decays monotonically as charge leaves the cells."
        )

    with tabs[1]:
        st.plotly_chart(_overlay_plot("Power vs time",
                                      "power_consumed", "Power (kW)",
                                      y_scale=1e-3, hline=80.0,
                                      hline_label="EV 2.2 limit (80 kW)"),
                        use_container_width=True)

    with tabs[2]:
        # Derived pack current = P / V_bus. We compute on the fly so the trace
        # exists whether or not the underlying model exposed it.
        fig = go.Figure()
        for label, hist, colour in (
            ("Battery", bh, "#2563eb"),
            ("Supercap", ch, "#ef4444"),
        ):
            if "dc_bus_voltage" in hist.columns and "power_consumed" in hist.columns:
                v = hist["dc_bus_voltage"].replace(0, np.nan)
                i = (hist["power_consumed"].abs() / v).fillna(0)
                fig.add_trace(go.Scatter(x=hist["time"], y=i, mode="lines",
                                         name=label, line=dict(color=colour, width=2)))
        fig.update_layout(title="Pack current |P|/V_bus vs time",
                          xaxis_title="Time (s)", yaxis_title="Current (A)",
                          template="plotly_white", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "The supercap almost always shows higher pack current at the "
            "same power output because its terminal voltage droops under load."
        )

    with tabs[3]:
        fig = go.Figure()
        for label, hist, colour in (
            ("Battery", bh, "#2563eb"),
            ("Supercap", ch, "#ef4444"),
        ):
            if "power_consumed" in hist.columns:
                t = hist["time"].to_numpy()
                p = hist["power_consumed"].abs().to_numpy()
                e_cum = np.concatenate([[0.0], np.cumsum(
                    0.5 * (p[:-1] + p[1:]) * np.diff(t)
                )]) / 1000.0
                fig.add_trace(go.Scatter(x=t, y=e_cum, mode="lines",
                                         name=label, line=dict(color=colour, width=2)))
        fig.update_layout(title="Cumulative energy drawn vs time",
                          xaxis_title="Time (s)", yaxis_title="Energy (kJ)",
                          template="plotly_white", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        st.plotly_chart(_overlay_plot("State of charge",
                                      "energy_storage_soc", "SoC (-)",
                                      hline=0.0),
                        use_container_width=True)

    with tabs[5]:
        st.plotly_chart(_overlay_plot("Velocity vs time",
                                      "velocity", "Velocity (m/s)"),
                        use_container_width=True)

    # --- Recommendation ---------------------------------------------

    st.subheader("Recommendation for this config")

    faster = "battery" if br.final_time <= cr.final_time else "supercap"
    slower = "supercap" if faster == "battery" else "battery"
    delta_ms = abs(br.final_time - cr.final_time) * 1000.0

    bat_v_drop = bh["dc_bus_voltage"].iloc[0] - bh["dc_bus_voltage"].iloc[-1]
    cap_v_drop = ch["dc_bus_voltage"].iloc[0] - ch["dc_bus_voltage"].iloc[-1]

    st.markdown(
        f"""
- **Faster over 75 m:** {faster} by **{delta_ms:.0f} ms**.
- **Bus voltage at the finish line:** battery held within
  **{bat_v_drop:+.1f} V** of start; supercap dropped
  **{cap_v_drop:+.1f} V**.
- **Peak pack current:** battery **{_pack_current_kw(bh):.0f} A**,
  supercap **{_pack_current_kw(ch):.0f} A**. Inverter / wiring sizing
  scales with peak current.
- **Why the faster one wins here:** look at the DC bus plot; if one
  technology hit the 80 kW cap on the full power-limited phase and the
  other dropped below due to voltage decay, that's the delta. If they're
  tied on power, the difference is purely IR² losses.
- **When supercap is preferable in real FS designs:** very high peak
  power-to-energy ratio events (acceleration, skidpad), high-cycle-life
  tolerance of repeated discharges, ability to absorb regen bursts
  without thermal issues. On the 22 km endurance event, the battery wins
  because the supercap's energy density is much lower and it would need
  charging mid-run.
        """
    )
else:
    st.info(
        "Tune the battery and supercap parameters on the left and right, "
        "then click **Run both scenarios**."
    )
