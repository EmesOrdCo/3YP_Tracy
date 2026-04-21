"""Nelder-Mead optimiser adapted from run_quick_optimization.py.

Key differences vs the script version:
  - Works on a config dict in memory (no JSON I/O).
  - Accepts a user-selected subset of the 7 decision variables and custom bounds.
  - Supports a progress callback so the Streamlit page can show live progress.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from .config_io import dict_to_config


# Aspirational lower bounds for weight / drag / losses: targets the team
# works towards. Applied when the optimiser runs with apply_presets=True.
MINIMIZE_PARAMS: Dict[str, float] = {
    "mass.total_mass": 200.0,
    "mass.cg_z": 0.22,
    "mass.unsprung_mass_front": 10.0,
    "mass.unsprung_mass_rear": 10.0,
    "mass.i_pitch": 120.0,
    "tires.rolling_resistance_coeff": 0.010,
    "powertrain.battery_internal_resistance": 0.008,
    "powertrain.wheel_inertia": 0.05,
    "aerodynamics.cda": 0.55,
}

# Aspirational upper bounds for grip and efficiency.
MAXIMIZE_PARAMS: Dict[str, float] = {
    "tires.mu_max": 1.8,
    "powertrain.motor_efficiency": 0.96,
    "powertrain.drivetrain_efficiency": 0.97,
}

# Hardware-pinned values (YASA P400R motor, BAMOCAR-PG-D3-700/400 inverter,
# 200-cell supercap stack @ 600 V nominal). Sourced from the datasheets in
# the project root. Changing these means changing the real car.
FIXED_PARAMS: Dict = {
    "powertrain.max_power_accumulator_outlet": 80000.0,  # FS EV 2.2 rule
    "simulation.target_distance": 75.0,
    "aerodynamics.cl_front": 0.0,
    "aerodynamics.cl_rear": 0.0,
    # YASA P400R
    "powertrain.motor_torque_constant": 0.822,
    "powertrain.motor_max_current": 285.0,  # BAMOCAR peak (400 A peak AC = 285 A RMS)
    "powertrain.motor_max_speed": 838.0,    # YASA max 8000 rpm
    # Supercap stack (Eaton C46W-3R0-0600, 200 cells in series)
    "powertrain.battery_voltage_nominal": 600.0,
    "powertrain.battery_max_current": 300.0,
    "powertrain.battery_internal_resistance": 0.14,
    "powertrain.energy_storage_type": "supercapacitor",
    "powertrain.supercap_cell_voltage": 3.0,
    "powertrain.supercap_cell_capacitance": 600.0,
    "powertrain.supercap_cell_esr": 0.0007,
    "powertrain.supercap_num_cells": 200,
    "powertrain.supercap_min_voltage": 350.0,
    "powertrain.differential_ratio": 1.0,
    "environment.air_density": 1.225,
    "environment.ambient_temperature": 20.0,
    "environment.track_grade": 0.0,
    "environment.wind_speed": 0.0,
    "environment.surface_mu_scaling": 1.0,
    "mass.wheelbase": 1.6,
    "mass.front_track": 1.2,
    "mass.rear_track": 1.2,
    "mass.i_yaw": 100.0,
    "tires.mass": 3.0,
    "suspension.ride_height_front": 0.05,
    "suspension.ride_height_rear": 0.05,
    "suspension.wheel_rate_front": 35000.0,
    "suspension.wheel_rate_rear": 35000.0,
}


def _apply_to_dict(data: Dict, dotted: str, value: float) -> None:
    """Set data[section][key] = value for a 'section.key' path."""
    section, _, key = dotted.partition(".")
    if not section or not key:
        return
    data.setdefault(section, {})[key] = value


# Default decision variables + bounds (pulled from run_quick_optimization.py).
VARIABLES: Dict[str, Dict] = {
    "cg_x_ratio": {
        "label": "CG X ratio (cg_x / wheelbase)",
        "bounds": (0.55, 0.90),  # less rear-biased to tame wheelies
        "apply": lambda cfg, v: setattr(cfg.mass, "cg_x", float(v) * cfg.mass.wheelbase),
        "get_default": lambda cfg: cfg.mass.cg_x / cfg.mass.wheelbase
                                   if cfg.mass.wheelbase else 0.5,
    },
    "gear_ratio": {
        "label": "Gear ratio",
        "bounds": (4.0, 10.0),  # strong motor -> shorter gears are viable
        "apply": lambda cfg, v: setattr(cfg.powertrain, "gear_ratio", float(v)),
        "get_default": lambda cfg: cfg.powertrain.gear_ratio,
    },
    "radius_loaded": {
        "label": "Tire loaded radius (m)",
        "bounds": (0.200, 0.260),  # 19" tyres ~ 0.247 m
        "apply": lambda cfg, v: setattr(cfg.tires, "radius_loaded", float(v)),
        "get_default": lambda cfg: cfg.tires.radius_loaded,
    },
    "mu_slip_optimal": {
        "label": "Optimal slip ratio (simple tire model)",
        "bounds": (0.08, 0.20),
        "apply": lambda cfg, v: setattr(cfg.tires, "mu_slip_optimal", float(v)),
        "get_default": lambda cfg: cfg.tires.mu_slip_optimal,
    },
    "launch_torque_limit": {
        "label": "Launch torque limit (N.m)",
        "bounds": (400.0, 1500.0),
        "apply": lambda cfg, v: setattr(cfg.control, "launch_torque_limit", float(v)),
        "get_default": lambda cfg: cfg.control.launch_torque_limit,
    },
    "anti_squat_ratio": {
        "label": "Anti-squat ratio",
        "bounds": (0.0, 0.6),
        "apply": lambda cfg, v: setattr(cfg.suspension, "anti_squat_ratio", float(v)),
        "get_default": lambda cfg: cfg.suspension.anti_squat_ratio,
    },
}


@dataclass
class OptimizationProgress:
    """Snapshot of progress for the UI callback."""
    evaluations: int
    best_time: float
    best_x: Optional[np.ndarray]
    start_index: int
    total_starts: int


@dataclass
class OptimizationResult:
    best_time: float
    best_x: np.ndarray
    best_variables: Dict[str, float]
    best_config_dict: Dict
    final_simulation_result: object  # SimulationResult
    n_evaluations: int
    elapsed_s: float
    variable_names: List[str]
    bounds: List[Tuple[float, float]]


def _make_candidate_config(base_dict: Dict, variables: List[str],
                           x: np.ndarray, dt: float, max_time: float,
                           *, apply_presets: bool = False) -> Dict:
    """Return a new config dict with decision variables applied.

    If ``apply_presets`` is True, the MINIMIZE/MAXIMIZE/FIXED sets from
    run_quick_optimization.py are overlaid on top of the base config before the
    decision variables are applied. This reproduces the CLI script behaviour
    exactly (and will in general move away from the user's base values).
    """
    # Deep-copy so we don't mutate the user's base.
    data = copy.deepcopy(base_dict)

    if apply_presets:
        for dotted, value in FIXED_PARAMS.items():
            _apply_to_dict(data, dotted, value)
        for dotted, value in MINIMIZE_PARAMS.items():
            _apply_to_dict(data, dotted, value)
        for dotted, value in MAXIMIZE_PARAMS.items():
            _apply_to_dict(data, dotted, value)

    cfg = dict_to_config(data)
    for name, value in zip(variables, x):
        VARIABLES[name]["apply"](cfg, value)
    cfg.dt = dt
    cfg.max_time = max_time

    # Round-trip back to dict (canonical form expected by the rest of the GUI).
    from .config_io import config_to_dict
    return config_to_dict(cfg)


def _evaluate(candidate_dict: Dict) -> Tuple[float, Optional[object]]:
    """Run one simulation and return (objective, SimulationResult or None)."""
    try:
        cfg = dict_to_config(candidate_dict)
    except TypeError:
        return 1e6, None
    errors = cfg.validate()
    if errors:
        return 1e6, None

    from simulation.acceleration_sim import AccelerationSimulation
    try:
        sim = AccelerationSimulation(cfg)
        result = sim.run()
    except Exception:  # noqa: BLE001
        return 1e6, None

    penalty = 0.0
    if not result.power_compliant:
        penalty += 1e5
    if not result.time_compliant:
        penalty += 1e4
    if result.wheelie_detected:
        penalty += 1e3
    target = cfg.target_distance
    if result.final_distance < target - 1e-3:
        penalty += 1e6
    return float(result.final_time) + penalty, result


def optimize(base_dict: Dict,
             variables: List[str],
             bounds: List[Tuple[float, float]],
             *,
             n_starts: int = 5,
             max_iter: int = 200,
             search_dt: float = 0.005,
             final_dt: float = 0.001,
             final_max_time: float = 30.0,
             search_max_time: float = 10.0,
             seed: int = 42,
             apply_presets: bool = False,
             progress_callback: Optional[Callable[[OptimizationProgress], None]] = None,
             ) -> OptimizationResult:
    """Run multi-start Nelder-Mead over the selected decision variables."""
    import time

    if len(variables) != len(bounds):
        raise ValueError("variables and bounds must have the same length.")
    if len(variables) == 0:
        raise ValueError("At least one decision variable must be selected.")

    rng = np.random.RandomState(seed)

    counters = {"n_evals": 0, "best": float("inf"), "best_x": None, "start_idx": 0}

    def objective(x: np.ndarray) -> float:
        candidate = _make_candidate_config(base_dict, variables, x,
                                           dt=search_dt,
                                           max_time=search_max_time,
                                           apply_presets=apply_presets)
        val, _ = _evaluate(candidate)
        counters["n_evals"] += 1
        if val < counters["best"]:
            counters["best"] = val
            counters["best_x"] = np.array(x, dtype=float)
        if progress_callback is not None and counters["n_evals"] % 5 == 0:
            progress_callback(OptimizationProgress(
                evaluations=counters["n_evals"],
                best_time=counters["best"],
                best_x=counters["best_x"],
                start_index=counters["start_idx"],
                total_starts=n_starts,
            ))
        return val

    # Generate starting points: midpoint + (n_starts - 1) random.
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    starts = [0.5 * (lo + hi)]
    for _ in range(max(n_starts - 1, 0)):
        starts.append(lo + rng.random_sample(len(bounds)) * (hi - lo))

    best_val = float("inf")
    best_x = None

    t0 = time.time()
    for i, x0 in enumerate(starts):
        counters["start_idx"] = i + 1
        if progress_callback is not None:
            progress_callback(OptimizationProgress(
                evaluations=counters["n_evals"],
                best_time=counters["best"],
                best_x=counters["best_x"],
                start_index=i + 1,
                total_starts=n_starts,
            ))
        res = minimize(
            objective, x0,
            method="Nelder-Mead",
            options={"maxiter": max_iter, "xatol": 0.002, "fatol": 0.01},
        )
        if res.fun < best_val:
            best_val = float(res.fun)
            best_x = np.array(res.x, dtype=float)

    elapsed = time.time() - t0

    # Final verification run at full accuracy.
    if best_x is None:
        raise RuntimeError("Optimisation failed to find any candidate.")
    final_dict = _make_candidate_config(base_dict, variables, best_x,
                                        dt=final_dt, max_time=final_max_time,
                                        apply_presets=apply_presets)
    final_val, final_result = _evaluate(final_dict)
    if final_result is None:
        raise RuntimeError("Final verification run failed.")

    best_vars = {name: float(val) for name, val in zip(variables, best_x)}
    return OptimizationResult(
        best_time=float(final_result.final_time),
        best_x=best_x,
        best_variables=best_vars,
        best_config_dict=final_dict,
        final_simulation_result=final_result,
        n_evaluations=counters["n_evals"],
        elapsed_s=elapsed,
        variable_names=list(variables),
        bounds=list(bounds),
    )
