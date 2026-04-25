"""Streamlit entry point for the Formula Student acceleration GUI.

Run with:
    streamlit run gui/app.py
or (after ``pip install -e .``):
    fs-gui
"""

from pathlib import Path
import sys


def _cli_entry() -> None:
    """Console-script entry for ``fs-gui``. Launches streamlit on this file."""
    import subprocess

    app_path = Path(__file__).resolve()
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path), *sys.argv[1:]]
    sys.exit(subprocess.call(cmd))


# Make project-root imports work regardless of how streamlit is launched.
_PKG_ROOT = Path(__file__).resolve().parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))

import streamlit as st

from gui._core.config_io import list_configs, load_as_dict
from gui._core import sim_runner


st.set_page_config(
    page_title="FS Acceleration Simulator",
    page_icon=":racing_car:",
    layout="wide",
)

st.title("Formula Student Acceleration Simulator")

st.markdown(
    """
This is an interactive front-end for the physics-based 0-75 m acceleration simulator.
Use the pages in the sidebar to:

- **Single Run** - edit a vehicle configuration and run one simulation with detailed plots.
- **Compare Configs** - overlay several saved configurations side-by-side.
- **Parameter Sweep** - sweep one or two parameters and visualise the result surface.
- **Optimizer** - run the Nelder-Mead optimiser to minimise the 0-75 m time subject to the
  Formula Student power and wheelie constraints.

All heavy lifting is done by the same solver, config, and rules modules as the CLI scripts -
this GUI is a thin presentation layer on top.
"""
)

st.subheader("Available configurations")

configs = list_configs()
if not configs:
    st.warning("No configs found under config/vehicle_configs/.")
else:
    st.write(", ".join(f"`{c}`" for c in configs))

st.subheader("Quick check: default (base_vehicle) run")

if "base_vehicle" in configs:
    if st.button("Run base_vehicle simulation"):
        outcome = sim_runner.run(load_as_dict("base_vehicle"))
        if not outcome.ok:
            for err in outcome.errors:
                st.error(err)
        else:
            r = outcome.result
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Final time", f"{r.final_time:.3f} s")
            c2.metric("Final velocity", f"{r.final_velocity:.1f} m/s",
                      f"{r.final_velocity * 3.6:.1f} km/h")
            c3.metric("Max power", f"{r.max_power_used / 1000:.2f} kW")
            c4.metric("Final distance", f"{r.final_distance:.2f} m")
else:
    st.info("Add a base_vehicle.json to config/vehicle_configs/ to enable this shortcut.")
