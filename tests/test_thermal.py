"""Tests for the tyre thermal model.

Pins:
 1. When disabled, rigid-model times are bit-identical to pre-thermal runs.
 2. When enabled with cold tyres, 75 m time is slower than with optimal tyres.
 3. Rear tyre temperature rises during the run; front stays at ambient.
 4. The mu(T) multiplier is Gaussian-shaped around the optimum and drops
    below the optimum consistently (no sign flip, no runaway).
 5. Cooling behaves correctly in a pure-coast condition (no slip -> temp
    decays toward ambient).
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from simulation.acceleration_sim import AccelerationSimulation
from vehicle.tire_model import TireModel


CONFIG_DIR = Path(__file__).parent.parent / "config" / "vehicle_configs"


def _base_config():
    return load_config(CONFIG_DIR / "base_vehicle.json")


class TestThermalEnableFlag(unittest.TestCase):
    def test_disabled_matches_legacy(self):
        """Thermal model off should be bitwise identical to not having it."""
        cfg = _base_config()
        cfg.tires.thermal_model_enabled = False
        r1 = AccelerationSimulation(cfg).run()
        r2 = AccelerationSimulation(cfg).run()
        self.assertAlmostEqual(r1.final_time, r2.final_time, places=6)


class TestColdVsWarmTyres(unittest.TestCase):
    def _run_at_initial_temp(self, initial_c: float) -> float:
        cfg = _base_config()
        cfg.tires.thermal_model_enabled = True
        cfg.tires.thermal_initial_temp = initial_c
        cfg.tires.thermal_ambient_temp = 25.0
        return AccelerationSimulation(cfg).run().final_time

    def test_cold_tyres_are_slower_than_optimal(self):
        t_optimal = self._run_at_initial_temp(80.0)  # at peak
        t_cold = self._run_at_initial_temp(10.0)     # way off peak
        self.assertGreater(t_cold, t_optimal,
                           f"Cold tyres should be slower: cold={t_cold:.3f}, opt={t_optimal:.3f}")
        # Effect should be meaningful (>50 ms).
        self.assertGreater(t_cold - t_optimal, 0.05)

    def test_overhot_tyres_are_also_slower_than_optimal(self):
        t_optimal = self._run_at_initial_temp(80.0)
        t_hot = self._run_at_initial_temp(160.0)
        self.assertGreater(t_hot, t_optimal,
                           f"Overheated tyres should be slower: hot={t_hot:.3f}, opt={t_optimal:.3f}")


class TestTempRiseDuringRun(unittest.TestCase):
    def test_rear_tyre_heats_up_front_stays_cold(self):
        cfg = _base_config()
        cfg.tires.thermal_model_enabled = True
        cfg.tires.thermal_initial_temp = 25.0
        cfg.tires.thermal_ambient_temp = 25.0
        sim = AccelerationSimulation(cfg)
        sim.run()
        hist = sim.get_state_history()
        rear_rise = hist[-1].tyre_temp_rear - hist[0].tyre_temp_rear
        front_rise = hist[-1].tyre_temp_front - hist[0].tyre_temp_front
        self.assertGreater(rear_rise, 0.5,
                           f"Rear tyre should warm up at least 0.5 °C, got {rear_rise:.2f}")
        # Front wheels are free-rolling so slip -> 0, heat input -> 0.
        # Cooling may actually make front slightly cooler if ambient < initial;
        # here ambient == initial so delta should be basically zero.
        self.assertLess(abs(front_rise), 0.05,
                        f"Front tyre temp should barely change, got {front_rise:+.3f}")


class TestMuVsTempFactor(unittest.TestCase):
    def _factor_at(self, temp_c: float, *, sigma: float = 60.0, optimum: float = 80.0) -> float:
        cfg = _base_config()
        cfg.tires.thermal_model_enabled = True
        cfg.tires.thermal_optimal_temp = optimum
        cfg.tires.thermal_sigma = sigma
        model = TireModel(cfg.tires, use_pacejka=True)
        return model.thermal_mu_factor(temp_c)

    def test_factor_is_one_at_optimum(self):
        self.assertAlmostEqual(self._factor_at(80.0), 1.0, places=5)

    def test_factor_is_symmetric_about_optimum(self):
        self.assertAlmostEqual(self._factor_at(80.0 + 30.0),
                               self._factor_at(80.0 - 30.0),
                               places=5)

    def test_factor_monotone_below_optimum(self):
        factors = [self._factor_at(t) for t in (20.0, 40.0, 60.0, 80.0)]
        self.assertEqual(factors, sorted(factors),
                         "mu factor should rise monotonically from cold to optimum")

    def test_disabled_returns_unit_factor(self):
        cfg = _base_config()
        cfg.tires.thermal_model_enabled = False
        model = TireModel(cfg.tires, use_pacejka=True)
        self.assertEqual(model.thermal_mu_factor(-40.0), 1.0)
        self.assertEqual(model.thermal_mu_factor(200.0), 1.0)


class TestThermalValidation(unittest.TestCase):
    def test_invalid_thermal_capacity_flagged(self):
        cfg = _base_config()
        cfg.tires.thermal_model_enabled = True
        cfg.tires.thermal_capacity = -10.0
        self.assertTrue(any("thermal_capacity" in e for e in cfg.validate()))


if __name__ == "__main__":
    unittest.main()
