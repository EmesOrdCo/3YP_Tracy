"""Monte Carlo robustness analysis for the Streamlit UI.

Given a base config dict and a list of ``UncertainParam`` specifications,
each trial draws a random sample from the specified distribution, applies it
to a deep copy of the base config, runs a simulation, and records the output
metric plus compliance flags.

Over N trials this produces a **distribution** of outcomes (not a single
point estimate), from which the UI computes:

- Mean / std / 95 % confidence interval of the objective.
- Probabilities of non-compliance (wheelie, power violation, etc.).
- A variance-contribution tornado: for each input, the fraction of the
  output variance linearly attributable to it, via corr^2 of standardised
  input vs output (a first-order approximation that sums to <= 1).

The module is deliberately free of a direct Streamlit dependency so the
analysis can be unit-tested and reused by CLI scripts or reports.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config_io import dict_to_config
from .param_schema import ParamSpec, find, get_value


# Distributions supported by the sampler. Adding more just needs a new
# clause in ``UncertainParam.sample``.
_DISTRIBUTIONS = ("gaussian", "uniform")


@dataclass(frozen=True)
class UncertainParam:
    """Uncertainty specification for a single config parameter.

    ``nominal`` is the mean / centre of the distribution. ``spread`` is
    interpreted per distribution:

    - gaussian: 1 sigma (standard deviation).
    - uniform: half-width of the [mean - spread, mean + spread] interval.

    Hard bounds default to the schema's (min, max) if omitted so drawn
    samples never break config validation.
    """
    dotted: str
    nominal: float
    spread: float
    distribution: str = "gaussian"
    hard_min: Optional[float] = None
    hard_max: Optional[float] = None

    def _bounds(self) -> Tuple[Optional[float], Optional[float]]:
        spec = find(self.dotted)
        lo = self.hard_min
        hi = self.hard_max
        if spec is not None:
            if lo is None and spec.min is not None:
                lo = float(spec.min)
            if hi is None and spec.max is not None:
                hi = float(spec.max)
        return lo, hi

    def sample(self, rng: np.random.Generator) -> float:
        """Draw a single sample. Samples that fall outside the hard bounds
        are clipped rather than rejected - preserves the specified N."""
        if self.distribution == "gaussian":
            x = float(rng.normal(self.nominal, self.spread))
        elif self.distribution == "uniform":
            x = float(rng.uniform(self.nominal - self.spread, self.nominal + self.spread))
        else:
            raise ValueError(f"Unknown distribution: {self.distribution}")
        lo, hi = self._bounds()
        if lo is not None:
            x = max(lo, x)
        if hi is not None:
            x = min(hi, x)
        return x


# Objectives available for the MC report.
_OBJECTIVES: Dict[str, Dict] = {
    "final_time": {
        "label": "Final 75 m time (s)",
        "units": "s",
        "direction": "minimise",
        "extract": lambda r: float(r.final_time),
    },
    "final_velocity": {
        "label": "Final velocity (m/s)",
        "units": "m/s",
        "direction": "maximise",
        "extract": lambda r: float(r.final_velocity),
    },
}


@dataclass
class MonteCarloResult:
    """Structured return from ``run_monte_carlo``."""
    samples: pd.DataFrame            # one row per trial with inputs + outputs
    uncertain_params: List[UncertainParam]
    objective: str
    nominal_metric: Optional[float] = None  # deterministic run of the base config
    nominal_compliant: Optional[bool] = None

    @property
    def objective_meta(self) -> Dict:
        return _OBJECTIVES[self.objective]

    @property
    def n_valid(self) -> int:
        return int((~self.samples["__failed"]).sum())

    def metric_array(self) -> np.ndarray:
        return self.samples.loc[~self.samples["__failed"], "__metric"].to_numpy()

    def summary(self) -> Dict:
        m = self.metric_array()
        if m.size == 0:
            return {"count": 0}
        return {
            "count": int(m.size),
            "mean": float(np.mean(m)),
            "std": float(np.std(m, ddof=1)) if m.size > 1 else 0.0,
            "min": float(np.min(m)),
            "p05": float(np.percentile(m, 5)),
            "p50": float(np.percentile(m, 50)),
            "p95": float(np.percentile(m, 95)),
            "max": float(np.max(m)),
            "p_wheelie": float(self.samples["__wheelie"].mean()),
            "p_non_compliant": float((~self.samples["__compliant"]).mean()),
            "p_power_violation": float((~self.samples["__power_ok"]).mean()),
            "p_failed": float(self.samples["__failed"].mean()),
        }

    def variance_decomposition(self) -> pd.DataFrame:
        """Linear first-order contribution of each input to Var(metric).

        Uses corr(X_i, Y)^2 as the variance fraction attributable to input
        X_i. Independent Gaussian inputs imply sum(S_i) <= 1 (equality
        when the response is exactly linear); the shortfall is an
        interaction / nonlinearity budget. Useful as a tornado: the tallest
        bar is the knob to reduce first.
        """
        valid = self.samples[~self.samples["__failed"]]
        if valid.empty or len(self.uncertain_params) == 0:
            return pd.DataFrame(columns=["parameter", "corr2", "corr"])

        y = valid["__metric"].to_numpy()
        if np.std(y) < 1e-12:
            rows = [{"parameter": p.dotted, "corr": 0.0, "corr2": 0.0}
                    for p in self.uncertain_params]
        else:
            rows = []
            for p in self.uncertain_params:
                col = f"__x__{p.dotted}"
                if col not in valid.columns:
                    continue
                x = valid[col].to_numpy()
                if np.std(x) < 1e-12:
                    corr = 0.0
                else:
                    corr = float(np.corrcoef(x, y)[0, 1])
                rows.append({
                    "parameter": p.dotted,
                    "corr": corr,
                    "corr2": corr * corr,
                })
        df = pd.DataFrame(rows)
        df = df.sort_values("corr2", ascending=False).reset_index(drop=True)
        return df


# --- Main entry point -----------------------------------------------------

def run_monte_carlo(
    base_dict: Dict,
    uncertain: Iterable[UncertainParam],
    *,
    n_trials: int = 200,
    objective: str = "final_time",
    seed: int = 42,
    search_dt: float = 0.005,
    search_max_time: float = 12.0,
    run_callback: Optional[Callable[[Dict], "object"]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> MonteCarloResult:
    """Run N Monte Carlo trials and return the full sample DataFrame.

    ``run_callback`` accepts a config dict and returns a ``sim_runner``
    ``RunOutcome`` (kept injectable so the tests can swap in a fake).
    """
    if run_callback is None:
        from .sim_runner import run as _run
        run_callback = _run

    if objective not in _OBJECTIVES:
        raise ValueError(f"Unknown objective: {objective}")
    extract = _OBJECTIVES[objective]["extract"]

    rng = np.random.default_rng(seed)
    uncertain = list(uncertain)

    # Nominal (deterministic) baseline for the report header.
    nominal_data = copy.deepcopy(base_dict)
    sim_params = nominal_data.setdefault("simulation", {})
    sim_params["dt"] = float(search_dt)
    sim_params["max_time"] = float(search_max_time)
    nominal_outcome = run_callback(nominal_data)
    nominal_metric = None
    nominal_compliant = None
    if nominal_outcome.ok:
        nominal_metric = extract(nominal_outcome.result)
        nominal_compliant = bool(nominal_outcome.result.compliant)

    rows: List[Dict] = []
    for trial in range(n_trials):
        data = copy.deepcopy(base_dict)
        sim_params = data.setdefault("simulation", {})
        sim_params["dt"] = float(search_dt)
        sim_params["max_time"] = float(search_max_time)

        sample: Dict[str, float] = {}
        for p in uncertain:
            section, _, key = p.dotted.partition(".")
            if not section or not key:
                continue
            value = p.sample(rng)
            data.setdefault(section, {})[key] = value
            sample[p.dotted] = value

        outcome = run_callback(data)

        row = {"__trial": trial}
        for dotted, value in sample.items():
            row[f"__x__{dotted}"] = value

        if outcome.ok:
            r = outcome.result
            row.update({
                "__failed": False,
                "__error": "",
                "__metric": extract(r),
                "__final_time": float(r.final_time),
                "__final_velocity": float(r.final_velocity),
                "__max_power_kw": float(r.max_power_used) / 1000.0,
                "__compliant": bool(r.compliant),
                "__wheelie": bool(r.wheelie_detected),
                "__power_ok": bool(r.power_compliant),
            })
        else:
            row.update({
                "__failed": True,
                "__error": "; ".join(outcome.errors),
                "__metric": float("nan"),
                "__final_time": float("nan"),
                "__final_velocity": float("nan"),
                "__max_power_kw": float("nan"),
                "__compliant": False,
                "__wheelie": False,
                "__power_ok": False,
            })
        rows.append(row)

        if progress_callback is not None:
            progress_callback(trial + 1, n_trials)

    return MonteCarloResult(
        samples=pd.DataFrame(rows),
        uncertain_params=uncertain,
        objective=objective,
        nominal_metric=nominal_metric,
        nominal_compliant=nominal_compliant,
    )


# --- Convenient default uncertainty spec ---------------------------------

def default_uncertain_params(base_dict: Dict) -> List[UncertainParam]:
    """Realistic FS-team uncertainty spec, centred on the base config.

    The spreads below reflect approximate run-to-run or measurement
    uncertainty in each quantity, gathered from talking to FS teams and
    the project's logbook assumptions. They're sensible defaults; users
    can override any of them on the page.
    """
    specs: List[Tuple[str, float, str]] = [
        # (dotted, spread, distribution)
        ("mass.total_mass", 5.0, "gaussian"),
        ("mass.cg_x", 0.02, "gaussian"),
        ("mass.cg_z", 0.01, "gaussian"),
        ("tires.mu_max", 0.05, "gaussian"),
        ("control.launch_torque_limit", 50.0, "gaussian"),
        ("environment.surface_mu_scaling", 0.05, "gaussian"),
        ("environment.ambient_temperature", 5.0, "uniform"),
    ]

    out: List[UncertainParam] = []
    for dotted, spread, dist in specs:
        spec = find(dotted)
        if spec is None:
            continue
        nominal = float(get_value(base_dict, spec, spec.min or 0.0))
        out.append(UncertainParam(
            dotted=dotted,
            nominal=nominal,
            spread=spread,
            distribution=dist,
        ))
    return out
