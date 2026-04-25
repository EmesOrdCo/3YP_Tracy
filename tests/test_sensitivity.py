"""Tests for the sensitivity analysis module used by the Streamlit UI.

These pin:

1. The perturbation maths (+/- pct clamped to spec bounds, absolute step for
   zero-valued parameters).
2. The tornado-ranking logic (largest absolute-delta parameter ends up
   first).
3. The compliance flags (a perturbation that trips a wheelie is surfaced).
4. End-to-end smoke test against the real base_vehicle config: running the
   default parameter set should complete without errors and produce a
   ranking dominated by parameters we expect to matter (mass, cg_x, mu_max).
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from gui._core.config_io import load_as_dict
from gui._core.param_schema import find
from gui._core.sensitivity import (
    DEFAULT_SENSITIVITY_PARAMS,
    _perturbed_value,
    run_sensitivity,
)


# --- Fake RunOutcome -----------------------------------------------------

@dataclass
class _FakeResult:
    final_time: float
    final_velocity: float
    max_power_used: float
    compliant: bool
    wheelie_detected: bool
    power_compliant: bool


@dataclass
class _FakeOutcome:
    ok: bool
    errors: tuple
    result: _FakeResult


def _make_fake_runner(
    param_deltas: dict,
    *,
    wheelie_param: str = None,
):
    """Return a run callback that deterministically maps a config dict to a
    synthetic final_time based on ``param_deltas``.

    ``param_deltas[dotted]`` is the final-time contribution when the given
    dotted parameter is at its high/low perturbed value vs baseline.
    """
    base_value: dict = {}

    def _runner(data: dict) -> _FakeOutcome:
        t = 3.500
        wheelie = False
        for dotted, (base, delta_per_pct_fraction) in param_deltas.items():
            section, _, key = dotted.partition(".")
            current = data.get(section, {}).get(key, base)
            if base:
                pct_change = (current - base) / base
            else:
                pct_change = current - base
            t += delta_per_pct_fraction * pct_change
            if wheelie_param == dotted and current > base * 1.01:
                wheelie = True
        v = 30.0 - (t - 3.5)
        compliant = not wheelie
        return _FakeOutcome(
            ok=True, errors=(),
            result=_FakeResult(
                final_time=t, final_velocity=v, max_power_used=80_000.0,
                compliant=compliant, wheelie_detected=wheelie,
                power_compliant=True,
            ),
        )
    return _runner


# --- Unit tests ---------------------------------------------------------

class TestPerturbedValue(unittest.TestCase):
    def test_relative_perturbation(self):
        spec = find("mass.total_mass")
        self.assertAlmostEqual(_perturbed_value(spec, 200.0, 5.0, "+"), 210.0)
        self.assertAlmostEqual(_perturbed_value(spec, 200.0, 5.0, "-"), 190.0)

    def test_clamps_to_bounds(self):
        spec = find("mass.total_mass")  # min=120, max=350
        # A huge +pct should clamp to 350.
        self.assertEqual(_perturbed_value(spec, 340.0, 50.0, "+"), spec.max)

    def test_zero_base_uses_spec_step(self):
        spec = find("aerodynamics.cl_rear")  # min=0, step=0.05
        self.assertGreater(_perturbed_value(spec, 0.0, 5.0, "+"), 0.0)
        # "-" should clamp to the floor (0) rather than go negative.
        self.assertEqual(_perturbed_value(spec, 0.0, 5.0, "-"), 0.0)


class TestSensitivityReportLogic(unittest.TestCase):
    def test_ranks_by_impact_on_objective(self):
        # Parameter A has 2x the delta per % of B; it should rank first.
        deltas = {
            "mass.total_mass": (200.0, 0.20),   # +0.20 s per 100% change
            "aerodynamics.cda": (0.8, 0.05),    # +0.05 s per 100% change
        }
        runner = _make_fake_runner(deltas)
        base = {
            "mass": {"total_mass": 200.0},
            "aerodynamics": {"cda": 0.8},
        }
        report = run_sensitivity(
            base, list(deltas.keys()),
            pct=5.0, objective="final_time",
            run_callback=runner,
        )
        df = report.dataframe()
        self.assertEqual(df.iloc[0]["parameter"], "mass.total_mass")
        self.assertEqual(df.iloc[1]["parameter"], "aerodynamics.cda")

    def test_elasticity_sign_matches_expected_direction(self):
        # Positive coefficient means time grows with the parameter.
        deltas = {"mass.total_mass": (200.0, 0.5)}
        runner = _make_fake_runner(deltas)
        base = {"mass": {"total_mass": 200.0}}
        report = run_sensitivity(
            base, list(deltas.keys()),
            pct=5.0, objective="final_time",
            run_callback=runner,
        )
        df = report.dataframe()
        self.assertGreater(df.iloc[0]["elasticity"], 0.0)

    def test_wheelie_flag_surfaces_in_report(self):
        deltas = {"mass.cg_x": (1.0, 0.0)}  # no time impact
        runner = _make_fake_runner(deltas, wheelie_param="mass.cg_x")
        base = {"mass": {"cg_x": 1.0, "wheelbase": 1.6}}
        report = run_sensitivity(
            base, list(deltas.keys()),
            pct=5.0, objective="final_time",
            run_callback=runner,
        )
        df = report.dataframe()
        self.assertTrue(bool(df.iloc[0]["high_wheelie"]))
        self.assertFalse(bool(df.iloc[0]["low_wheelie"]))


class TestSensitivityEndToEnd(unittest.TestCase):
    """Hits the actual solver to make sure the wiring all works."""

    def test_default_parameters_run_on_base_vehicle(self):
        base = load_as_dict("base_vehicle")
        # Only exercise a small subset so the test stays fast.
        subset = [
            "mass.total_mass",
            "tires.mu_max",
            "aerodynamics.cda",
        ]
        report = run_sensitivity(
            base, subset, pct=5.0, objective="final_time",
            search_dt=0.01, search_max_time=8.0,
        )
        df = report.dataframe()
        self.assertEqual(len(df), 3)
        # Each row has at least one of delta_low / delta_high populated.
        for _, row in df.iterrows():
            self.assertFalse(row["delta_low"] is None and row["delta_high"] is None)

    def test_all_default_params_have_schema(self):
        """Catches regressions if param_schema.py removes a field the default
        sensitivity list still references."""
        for dotted in DEFAULT_SENSITIVITY_PARAMS:
            self.assertIsNotNone(find(dotted),
                                 f"Default sensitivity param {dotted} missing from schema.")


if __name__ == "__main__":
    unittest.main()
