"""Cached wrapper around AccelerationSimulation for use by Streamlit pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from . import PACKAGE_ROOT  # noqa: F401  (side effect: sys.path wiring)
from .config_io import dict_to_config, make_hashable


@dataclass
class RunOutcome:
    """Structured result bundle for the UI."""
    ok: bool
    errors: List[str]
    result: Optional[object] = None   # simulation.acceleration_sim.SimulationResult
    history: Optional[pd.DataFrame] = None
    config_dict: Optional[Dict] = None


def _state_history_to_df(history) -> pd.DataFrame:
    """Convert a list of SimulationState to a tidy DataFrame."""
    if not history:
        return pd.DataFrame()
    rows = [s.to_dict() for s in history]
    df = pd.DataFrame(rows)
    # Convenience columns for plotting.
    if "power_consumed" in df.columns:
        df["power_consumed_kw"] = df["power_consumed"] / 1000.0
    if "velocity" in df.columns:
        df["velocity_kmh"] = df["velocity"] * 3.6
    return df


def _run_inner(config_dict: Dict, fastest_time: Optional[float]) -> RunOutcome:
    """Actual sim execution. Kept as a plain function for easier testing."""
    try:
        config = dict_to_config(config_dict)
    except TypeError as exc:
        return RunOutcome(ok=False, errors=[f"Config build error: {exc}"],
                          config_dict=config_dict)

    errors = config.validate()
    if errors:
        return RunOutcome(ok=False, errors=errors, config_dict=config_dict)

    # Import here so Streamlit's hot-reload doesn't fight with sys.path on cold start.
    from simulation.acceleration_sim import AccelerationSimulation

    try:
        sim = AccelerationSimulation(config)
        result = sim.run(fastest_time=fastest_time)
    except Exception as exc:  # noqa: BLE001 - surface anything back to UI
        return RunOutcome(ok=False, errors=[f"Simulation failed: {exc}"],
                          config_dict=config_dict)

    df = _state_history_to_df(sim.get_state_history())
    return RunOutcome(ok=True, errors=[], result=result, history=df,
                      config_dict=config_dict)


@st.cache_resource(show_spinner=False, max_entries=128)
def _run_cached(config_key: Tuple, fastest_time: Optional[float],
                _config_dict_payload: Dict) -> RunOutcome:
    """Cache keyed by config_key + fastest_time; payload is not hashed.

    Uses cache_resource (not cache_data) to avoid pickling issues with
    RunOutcome, which contains custom dataclasses whose identity can change
    across Streamlit hot-reloads. cache_resource stores objects by reference.
    """
    return _run_inner(_config_dict_payload, fastest_time)


def run(config_dict: Dict, fastest_time: Optional[float] = None,
        use_cache: bool = True) -> RunOutcome:
    """Run a simulation from a config dict, optionally using the Streamlit cache."""
    if use_cache:
        key = make_hashable(config_dict)
        return _run_cached(key, fastest_time, config_dict)
    return _run_inner(config_dict, fastest_time)
