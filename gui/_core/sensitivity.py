"""One-at-a-time sensitivity analysis for the Streamlit UI.

Given a base config dict and a list of ``ParamSpec``s, each parameter is
perturbed by ±pct% (or ±abs_step for zero-valued params), a simulation is
run, and the delta in final time (or other metric) is recorded. The result
is a tornado-style ranking of the parameters by their impact on the chosen
objective.

This is deliberately a small, focused analysis: no search, no
optimisation, no coupling between parameters. Use the Optimizer page if you
want the global minimum; use this page to understand **which knobs matter
most** and by how much.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from .config_io import dict_to_config
from .param_schema import NUMERIC_PARAMS, ParamSpec, find, get_value


# Good default set: one parameter per physical subsystem the team can
# actually tune, chosen to cover mass / grip / aero / powertrain / control.
DEFAULT_SENSITIVITY_PARAMS: Tuple[str, ...] = (
    "mass.total_mass",
    "mass.cg_x",
    "mass.cg_z",
    "mass.wheelbase",
    "tires.mu_max",
    "tires.radius_loaded",
    "tires.rolling_resistance_coeff",
    "powertrain.gear_ratio",
    "powertrain.motor_torque_constant",
    "powertrain.motor_max_current",
    "powertrain.battery_voltage_nominal",
    "powertrain.battery_internal_resistance",
    "powertrain.wheel_inertia",
    "aerodynamics.cda",
    "suspension.anti_squat_ratio",
    "control.launch_torque_limit",
)

# Objectives the user can rank parameters by.
OBJECTIVES: Dict[str, Dict] = {
    "final_time": {
        "label": "Final 75 m time (s)",
        "direction": "minimise",
        "units": "s",
        "extract": lambda r: float(r.final_time),
    },
    "final_velocity": {
        "label": "Final velocity (m/s)",
        "direction": "maximise",
        "units": "m/s",
        "extract": lambda r: float(r.final_velocity),
    },
    "max_power": {
        "label": "Peak moving-average power (kW)",
        "direction": "inspect",
        "units": "kW",
        "extract": lambda r: float(r.max_power_used) / 1000.0,
    },
}


@dataclass
class ParamPerturbation:
    """Result of one (parameter, direction) perturbation."""
    spec: ParamSpec
    direction: str              # "-" or "+"
    base_value: float
    perturbed_value: float
    ok: bool
    metric: Optional[float] = None
    compliant: bool = True
    wheelie: bool = False
    power_compliant: bool = True
    errors: Tuple[str, ...] = ()


@dataclass
class SensitivityReport:
    base_metric: float
    base_compliant: bool
    perturbations: List[ParamPerturbation] = field(default_factory=list)
    pct: float = 5.0
    objective: str = "final_time"

    @property
    def objective_meta(self) -> Dict:
        return OBJECTIVES[self.objective]

    def dataframe(self) -> pd.DataFrame:
        """One row per parameter with low/high deltas + compliance flags."""
        # Group perturbations by parameter.
        rows: Dict[str, Dict] = {}
        for p in self.perturbations:
            key = p.spec.dotted
            row = rows.setdefault(key, {
                "parameter": key,
                "label": p.spec.label,
                "unit": p.spec.unit,
                "base_value": p.base_value,
                "value_low": None,
                "value_high": None,
                "metric_low": None,
                "metric_high": None,
                "delta_low": None,
                "delta_high": None,
                "elasticity": None,
                "low_compliant": True,
                "high_compliant": True,
                "low_wheelie": False,
                "high_wheelie": False,
                "notes": [],
            })
            if p.direction == "-":
                row["value_low"] = p.perturbed_value
                row["metric_low"] = p.metric
                row["low_compliant"] = p.compliant
                row["low_wheelie"] = p.wheelie
                if p.ok and p.metric is not None:
                    row["delta_low"] = p.metric - self.base_metric
                else:
                    row["notes"].append(f"low: {'; '.join(p.errors)}")
            else:
                row["value_high"] = p.perturbed_value
                row["metric_high"] = p.metric
                row["high_compliant"] = p.compliant
                row["high_wheelie"] = p.wheelie
                if p.ok and p.metric is not None:
                    row["delta_high"] = p.metric - self.base_metric
                else:
                    row["notes"].append(f"high: {'; '.join(p.errors)}")

        # Elasticity: (% change in metric) / (% change in param), averaged
        # across both sides when both are available. Undefined at zero-valued
        # base param (we still report absolute delta).
        for row in rows.values():
            elastic_samples = []
            for side, v_key, m_key in (
                ("-", "value_low", "metric_low"),
                ("+", "value_high", "metric_high"),
            ):
                v = row[v_key]
                m = row[m_key]
                if v is None or m is None:
                    continue
                if row["base_value"] == 0 or self.base_metric == 0:
                    continue
                dv_pct = (v - row["base_value"]) / row["base_value"]
                dm_pct = (m - self.base_metric) / self.base_metric
                if dv_pct != 0:
                    elastic_samples.append(dm_pct / dv_pct)
            if elastic_samples:
                row["elasticity"] = sum(elastic_samples) / len(elastic_samples)
            row["notes"] = "; ".join(row["notes"]) if row["notes"] else ""

        df = pd.DataFrame(rows.values())
        if df.empty:
            return df

        # Sort by the larger of |delta_low| and |delta_high| descending.
        def _impact(row) -> float:
            vals = [abs(v) for v in (row["delta_low"], row["delta_high"]) if v is not None]
            return max(vals) if vals else 0.0
        df["impact"] = df.apply(_impact, axis=1)
        df = df.sort_values("impact", ascending=False).reset_index(drop=True)
        return df


# --- Perturbation helpers -------------------------------------------------

def _perturbed_value(spec: ParamSpec, base: float, pct: float, direction: str) -> float:
    """Return ``base`` perturbed by ``pct`` percent (or abs_step if base == 0).

    The returned value is clamped to the spec's [min, max] if those are
    defined so the perturbation never breaks config validation. ``direction``
    is ``"-"`` or ``"+"``.
    """
    sign = -1.0 if direction == "-" else 1.0
    if base == 0.0:
        step = float(spec.step) if spec.step is not None else max(1e-3, pct / 100.0)
        new = base + sign * step
    else:
        new = base * (1.0 + sign * pct / 100.0)
    if spec.min is not None:
        new = max(float(spec.min), new)
    if spec.max is not None:
        new = min(float(spec.max), new)
    return float(new)


def _apply(data: Dict, spec: ParamSpec, value: float) -> Dict:
    out = copy.deepcopy(data)
    out.setdefault(spec.section, {})[spec.key] = value
    return out


# --- Main entry point -----------------------------------------------------

def run_sensitivity(
    base_dict: Dict,
    dotted_params: List[str],
    *,
    pct: float = 5.0,
    objective: str = "final_time",
    search_dt: float = 0.005,
    search_max_time: float = 12.0,
    run_callback: Optional[Callable[[Dict], "object"]] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> SensitivityReport:
    """Run a one-at-a-time sensitivity sweep.

    ``run_callback`` takes a config dict and returns a sim_runner
    ``RunOutcome``. Accepting it as a parameter keeps this function free of a
    direct Streamlit dependency so it can be unit-tested.
    """
    if run_callback is None:
        # Lazy import so importing this module doesn't require streamlit.
        from .sim_runner import run as _run
        run_callback = _run

    if objective not in OBJECTIVES:
        raise ValueError(f"Unknown objective: {objective}")
    extract = OBJECTIVES[objective]["extract"]

    def _prep(data: Dict) -> Dict:
        data = copy.deepcopy(data)
        sim = data.setdefault("simulation", {})
        sim["dt"] = float(search_dt)
        sim["max_time"] = float(search_max_time)
        return data

    # --- Baseline run ---
    base_ready = _prep(base_dict)
    if progress_callback:
        progress_callback(0, 1 + 2 * len(dotted_params), "base run")
    base_outcome = run_callback(base_ready)
    if not base_outcome.ok:
        raise RuntimeError(
            "Base config failed to simulate: " + "; ".join(base_outcome.errors)
        )
    base_metric = extract(base_outcome.result)
    base_compliant = bool(base_outcome.result.compliant)

    report = SensitivityReport(
        base_metric=base_metric,
        base_compliant=base_compliant,
        pct=pct,
        objective=objective,
    )

    # --- Perturb each parameter one at a time ---
    total = 1 + 2 * len(dotted_params)
    step = 1
    for dotted in dotted_params:
        spec = find(dotted)
        if spec is None or spec.widget != "number":
            # Skip bool / choice / unknown parameters - they can't be perturbed
            # by a continuous percentage.
            continue
        base_value = float(get_value(base_dict, spec, spec.min or 0.0))

        for direction in ("-", "+"):
            new_value = _perturbed_value(spec, base_value, pct, direction)
            if new_value == base_value:
                # Perturbation fell outside the spec bounds (already at the
                # min or max); report as skipped so the user sees it.
                report.perturbations.append(ParamPerturbation(
                    spec=spec, direction=direction,
                    base_value=base_value, perturbed_value=new_value,
                    ok=False, errors=("at bound",),
                ))
                step += 1
                continue

            if progress_callback:
                progress_callback(step, total, f"{dotted} {direction}{pct:g}%")
            cfg_data = _prep(_apply(base_dict, spec, new_value))
            outcome = run_callback(cfg_data)
            if outcome.ok:
                r = outcome.result
                metric = extract(r)
                report.perturbations.append(ParamPerturbation(
                    spec=spec, direction=direction,
                    base_value=base_value, perturbed_value=new_value,
                    ok=True, metric=metric,
                    compliant=bool(r.compliant),
                    wheelie=bool(r.wheelie_detected),
                    power_compliant=bool(r.power_compliant),
                ))
            else:
                report.perturbations.append(ParamPerturbation(
                    spec=spec, direction=direction,
                    base_value=base_value, perturbed_value=new_value,
                    ok=False, errors=tuple(outcome.errors),
                ))
            step += 1

    if progress_callback:
        progress_callback(total, total, "done")
    return report
