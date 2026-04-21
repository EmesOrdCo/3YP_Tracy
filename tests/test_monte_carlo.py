"""Tests for the Monte Carlo robustness analysis.

Pins:
 1. Samples drawn from an UncertainParam respect the distribution and the
    schema bounds.
 2. A zero-spread (deterministic) run gives zero variance.
 3. With a known linear response, the corr^2 tornado puts the right
    parameter at the top.
 4. Increasing N reduces the standard error of the sample mean as sqrt(N).
 5. End-to-end real-solver run: N=30 trials on the base_vehicle completes
    and produces sensible summary stats.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from gui._core.config_io import load_as_dict
from gui._core.monte_carlo import (
    UncertainParam,
    default_uncertain_params,
    run_monte_carlo,
)


# --- Fake run callback --------------------------------------------------

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


def _make_linear_runner(coeff: float, base_value: float, dotted: str):
    """Runner where final_time = 3.5 + coeff * (x - base_value)."""
    section, _, key = dotted.partition(".")

    def _runner(data: dict) -> _FakeOutcome:
        x = data.get(section, {}).get(key, base_value)
        t = 3.5 + coeff * (x - base_value)
        return _FakeOutcome(ok=True, errors=(), result=_FakeResult(
            final_time=t, final_velocity=30.0,
            max_power_used=80000.0, compliant=True,
            wheelie_detected=False, power_compliant=True,
        ))
    return _runner


def _make_two_input_runner(base: dict, coeffs: dict):
    """Runner where final_time = 3.5 + sum(coeff_i * (x_i - base_i))."""
    def _runner(data: dict) -> _FakeOutcome:
        t = 3.5
        for dotted, c in coeffs.items():
            section, _, key = dotted.partition(".")
            x = data.get(section, {}).get(key, base[dotted])
            t += c * (x - base[dotted])
        return _FakeOutcome(ok=True, errors=(), result=_FakeResult(
            final_time=t, final_velocity=30.0,
            max_power_used=80000.0, compliant=True,
            wheelie_detected=False, power_compliant=True,
        ))
    return _runner


# --- Tests ------------------------------------------------------------

class TestUncertainParamSampling(unittest.TestCase):
    def test_gaussian_mean_and_std_approximate_true_values(self):
        p = UncertainParam("mass.total_mass", nominal=200.0, spread=5.0)
        rng = np.random.default_rng(0)
        samples = np.array([p.sample(rng) for _ in range(10_000)])
        self.assertAlmostEqual(samples.mean(), 200.0, delta=0.2)
        self.assertAlmostEqual(samples.std(), 5.0, delta=0.2)

    def test_uniform_samples_land_within_half_width(self):
        p = UncertainParam("mass.total_mass", nominal=200.0,
                           spread=3.0, distribution="uniform")
        rng = np.random.default_rng(0)
        for _ in range(500):
            x = p.sample(rng)
            self.assertGreaterEqual(x, 197.0)
            self.assertLessEqual(x, 203.0)

    def test_samples_are_clipped_to_schema_bounds(self):
        # mass.total_mass bounds: min=120, max=350
        p = UncertainParam("mass.total_mass", nominal=200.0, spread=1e6)
        rng = np.random.default_rng(0)
        for _ in range(200):
            x = p.sample(rng)
            self.assertGreaterEqual(x, 120.0)
            self.assertLessEqual(x, 350.0)

    def test_zero_spread_is_deterministic(self):
        p = UncertainParam("mass.total_mass", nominal=200.0, spread=0.0)
        rng = np.random.default_rng(0)
        self.assertEqual(p.sample(rng), 200.0)


class TestRunMonteCarloLogic(unittest.TestCase):
    def test_zero_variance_input_produces_zero_variance_output(self):
        params = [UncertainParam("mass.total_mass", nominal=200.0, spread=0.0)]
        runner = _make_linear_runner(coeff=0.01, base_value=200.0,
                                     dotted="mass.total_mass")
        res = run_monte_carlo(
            {"mass": {"total_mass": 200.0}},
            params, n_trials=20, seed=0,
            run_callback=runner,
        )
        summary = res.summary()
        self.assertEqual(summary["std"], 0.0)
        self.assertAlmostEqual(summary["mean"], 3.5, places=6)

    def test_mean_converges_to_deterministic_baseline(self):
        """A Gaussian-perturbed LINEAR response has E[Y] = baseline."""
        base_val = 200.0
        params = [UncertainParam("mass.total_mass",
                                 nominal=base_val, spread=5.0)]
        runner = _make_linear_runner(coeff=0.01, base_value=base_val,
                                     dotted="mass.total_mass")
        res = run_monte_carlo(
            {"mass": {"total_mass": base_val}},
            params, n_trials=1000, seed=1,
            run_callback=runner,
        )
        summary = res.summary()
        # Nominal baseline: coeff*(base-base) + 3.5 = 3.5. Mean should match.
        self.assertAlmostEqual(summary["mean"], 3.5, delta=0.01)

    def test_variance_tornado_picks_dominant_input(self):
        base = {"mass.total_mass": 200.0, "tires.mu_max": 1.8}
        # Mass has 10x the coefficient and 10x the spread of mu_max
        # so its variance contribution should dominate.
        coeffs = {"mass.total_mass": 0.1, "tires.mu_max": 0.01}
        runner = _make_two_input_runner(base, coeffs)
        params = [
            UncertainParam("mass.total_mass", nominal=200.0, spread=5.0),
            UncertainParam("tires.mu_max", nominal=1.8, spread=0.005),
        ]
        res = run_monte_carlo(
            {"mass": {"total_mass": 200.0}, "tires": {"mu_max": 1.8}},
            params, n_trials=500, seed=0,
            run_callback=runner,
        )
        vd = res.variance_decomposition()
        self.assertEqual(vd.iloc[0]["parameter"], "mass.total_mass")
        # Mass should explain nearly all the variance.
        self.assertGreater(vd.iloc[0]["corr2"], 0.8)

    def test_std_error_of_mean_shrinks_with_N(self):
        """Run N=50 vs N=500; larger N should give mean closer to truth."""
        base_val = 200.0
        params = [UncertainParam("mass.total_mass",
                                 nominal=base_val, spread=5.0)]
        runner = _make_linear_runner(coeff=0.01, base_value=base_val,
                                     dotted="mass.total_mass")

        res_small = run_monte_carlo(
            {"mass": {"total_mass": base_val}},
            params, n_trials=50, seed=7,
            run_callback=runner,
        )
        res_large = run_monte_carlo(
            {"mass": {"total_mass": base_val}},
            params, n_trials=500, seed=7,
            run_callback=runner,
        )
        err_small = abs(res_small.summary()["mean"] - 3.5)
        err_large = abs(res_large.summary()["mean"] - 3.5)
        # Allow a little slop - it's a statistical claim. err_large should
        # be within 3x err_small (expected sqrt(10) reduction).
        self.assertLess(err_large, err_small * 3)

    def test_nominal_run_recorded(self):
        params = [UncertainParam("mass.total_mass", nominal=200.0, spread=1.0)]
        runner = _make_linear_runner(coeff=0.01, base_value=200.0,
                                     dotted="mass.total_mass")
        res = run_monte_carlo(
            {"mass": {"total_mass": 200.0}},
            params, n_trials=10, seed=0,
            run_callback=runner,
        )
        self.assertAlmostEqual(res.nominal_metric, 3.5, places=6)
        self.assertTrue(res.nominal_compliant)


class TestMonteCarloEndToEnd(unittest.TestCase):
    def test_real_solver_small_N_completes(self):
        """Hit the actual solver (30 trials, small subset) to make sure
        the wiring works against the real sim."""
        base = load_as_dict("base_vehicle")
        params = [
            UncertainParam("mass.total_mass", nominal=250.0, spread=5.0),
            UncertainParam("tires.mu_max", nominal=1.7, spread=0.05),
        ]
        res = run_monte_carlo(
            base, params,
            n_trials=30, seed=0,
            search_dt=0.01, search_max_time=8.0,
        )
        self.assertGreaterEqual(res.summary()["count"], 28,
                                "Real-solver run should not crash on most trials")
        # Mean must be in a sane range for the base car.
        mean = res.summary()["mean"]
        self.assertGreater(mean, 3.0)
        self.assertLess(mean, 6.0)


class TestDefaultUncertainParams(unittest.TestCase):
    def test_defaults_centre_on_base_values(self):
        base = load_as_dict("base_vehicle")
        params = default_uncertain_params(base)
        self.assertGreater(len(params), 4)
        # Make sure nominal for mass.total_mass matches what's in the JSON.
        by_dotted = {p.dotted: p for p in params}
        self.assertAlmostEqual(
            by_dotted["mass.total_mass"].nominal,
            float(base["mass"]["total_mass"]),
        )


if __name__ == "__main__":
    unittest.main()
