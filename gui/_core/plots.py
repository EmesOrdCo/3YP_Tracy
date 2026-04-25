"""Plotly figure builders for the GUI.

Each function accepts a history DataFrame (schema matches SimulationState.to_dict)
and returns a go.Figure. Every function also takes an optional existing figure
and label so they can overlay multiple runs on Page 2 (Compare).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go


def _new_fig(title: str, yaxis_title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="Time (s)",
        yaxis_title=yaxis_title,
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=50, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
    )
    return fig


def _add_trace(fig: go.Figure, df: pd.DataFrame, y: str, *,
               label: Optional[str], default_name: str,
               dash: Optional[str] = None) -> None:
    if df is None or df.empty or y not in df.columns:
        return
    fig.add_trace(go.Scatter(
        x=df["time"], y=df[y],
        mode="lines",
        name=label if label else default_name,
        line=dict(dash=dash) if dash else None,
    ))


def velocity_plot(df: pd.DataFrame, label: Optional[str] = None,
                  fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("Velocity vs time", "Velocity (m/s)")
    _add_trace(fig, df, "velocity", label=label, default_name="Velocity")
    return fig


def acceleration_plot(df: pd.DataFrame, label: Optional[str] = None,
                      fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("Acceleration vs time", "Acceleration (m/s^2)")
    _add_trace(fig, df, "acceleration", label=label, default_name="Acceleration")
    return fig


def power_plot(df: pd.DataFrame, label: Optional[str] = None,
               fig: Optional[go.Figure] = None,
               show_limit: bool = True) -> go.Figure:
    fig = fig or _new_fig("Accumulator power vs time", "Power (kW)")
    _add_trace(fig, df, "power_consumed_kw", label=label, default_name="Power")
    if show_limit and not fig.layout.shapes:
        fig.add_hline(y=80.0, line=dict(color="red", dash="dash"),
                      annotation_text="EV 2.2 limit (80 kW)",
                      annotation_position="top left")
    return fig


def normal_forces_plot(df: pd.DataFrame, label: Optional[str] = None,
                       fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("Normal forces vs time", "Normal force (N)")
    prefix = f"{label} " if label else ""
    _add_trace(fig, df, "normal_force_front", label=f"{prefix}Front", default_name="Front")
    _add_trace(fig, df, "normal_force_rear", label=f"{prefix}Rear", default_name="Rear",
               dash="dash")
    return fig


def tire_forces_plot(df: pd.DataFrame, label: Optional[str] = None,
                     fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("Longitudinal tire forces vs time", "Tire force (N)")
    prefix = f"{label} " if label else ""
    _add_trace(fig, df, "tire_force_rear", label=f"{prefix}Rear (drive)",
               default_name="Rear")
    _add_trace(fig, df, "drive_force", label=f"{prefix}Net drive",
               default_name="Net drive", dash="dot")
    _add_trace(fig, df, "drag_force", label=f"{prefix}Drag",
               default_name="Drag", dash="dash")
    return fig


def slip_plot(df: pd.DataFrame, label: Optional[str] = None,
              fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("Slip ratio vs time", "Slip ratio (-)")
    prefix = f"{label} " if label else ""
    _add_trace(fig, df, "slip_ratio_rear", label=f"{prefix}Rear slip",
               default_name="Rear slip")
    _add_trace(fig, df, "optimal_slip_ratio", label=f"{prefix}Optimal",
               default_name="Optimal", dash="dash")
    return fig


def soc_plot(df: pd.DataFrame, label: Optional[str] = None,
             fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("Energy storage state vs time", "State of charge (-)")
    _add_trace(fig, df, "energy_storage_soc", label=label, default_name="SoC")
    return fig


def voltage_plot(df: pd.DataFrame, label: Optional[str] = None,
                 fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("DC bus voltage vs time", "Voltage (V)")
    _add_trace(fig, df, "dc_bus_voltage", label=label, default_name="DC bus")
    return fig


def distance_plot(df: pd.DataFrame, label: Optional[str] = None,
                  fig: Optional[go.Figure] = None) -> go.Figure:
    fig = fig or _new_fig("Distance vs time", "Distance (m)")
    _add_trace(fig, df, "position", label=label, default_name="Distance")
    return fig


def tyre_temp_plot(df: pd.DataFrame, label: Optional[str] = None,
                   fig: Optional[go.Figure] = None) -> go.Figure:
    """Front / rear tyre carcass temperature across the run.

    Only really informative when ``tires.thermal_model_enabled`` is True;
    otherwise the two series stay flat at the initial temperature.
    """
    fig = fig or _new_fig("Tyre temperature vs time", "Temperature (°C)")
    prefix = f"{label} " if label else ""
    _add_trace(fig, df, "tyre_temp_front", label=f"{prefix}Front",
               default_name="Front")
    _add_trace(fig, df, "tyre_temp_rear", label=f"{prefix}Rear",
               default_name="Rear", dash="dash")
    return fig
