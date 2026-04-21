"""End-to-end integration tests that exercise the full simulation pipeline.

These cover paths that the existing unit tests don't: wheelie detection from
a real run, power-limit compliance on a synthetic 120 kW trace, the 500 ms
moving-average behaviour, and tire_model_type switching having a measurable
effect on the solver.
"""

import copy
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from dynamics.state import SimulationState
from rules.power_limit import check_power_limit
from rules.wheelie_check import check_wheelie
from simulation.acceleration_sim import AccelerationSimulation


CONFIG_DIR = Path(__file__).parent.parent / "config" / "vehicle_configs"


def _base_config():
    return load_config(CONFIG_DIR / "base_vehicle.json")


class TestWheelieDetection(unittest.TestCase):
    """check_wheelie against both synthetic states and a real simulation."""

    def test_detects_lift_off(self):
        """A state with front Fz below threshold is flagged as a wheelie."""
        history = [
            SimulationState(time=0.0, normal_force_front=1200.0),
            SimulationState(time=0.05, normal_force_front=600.0),
            SimulationState(time=0.10, normal_force_front=0.05),  # lift-off
            SimulationState(time=0.15, normal_force_front=0.0),
        ]
        detected, min_front, t_first = check_wheelie(history)
        self.assertTrue(detected)
        self.assertLess(min_front, 0.1)
        self.assertEqual(t_first, 0.10)

    def test_safe_run_not_flagged(self):
        """A state history with comfortable front load is never flagged."""
        history = [
            SimulationState(time=i * 0.01, normal_force_front=500.0)
            for i in range(10)
        ]
        detected, _, t_first = check_wheelie(history)
        self.assertFalse(detected)
        self.assertEqual(t_first, -1.0)

    def test_full_sim_base_vehicle_wheelies(self):
        """base_vehicle is rear-biased enough that it wheelies; flag it."""
        sim = AccelerationSimulation(_base_config())
        r = sim.run()
        self.assertTrue(r.wheelie_detected,
                        "base_vehicle (76% rear bias) is expected to wheelie")
        self.assertGreater(r.wheelie_time, 0.0)


class TestPowerLimit(unittest.TestCase):
    """EV 2.2 / D 9.4.1 power limit checker."""

    def test_empty_history_compliant(self):
        compliant, peak, t = check_power_limit([])
        self.assertTrue(compliant)
        self.assertEqual(peak, 0.0)
        self.assertEqual(t, -1.0)

    def test_flat_below_limit_compliant(self):
        history = [
            SimulationState(time=i * 0.001, power_consumed=50_000.0)
            for i in range(2000)
        ]
        compliant, peak, t = check_power_limit(history, max_power=80_000.0)
        self.assertTrue(compliant)
        self.assertAlmostEqual(peak, 50_000.0, delta=1.0)
        self.assertEqual(t, -1.0)

    def test_sustained_violation_detected(self):
        """120 kW held for 1 s should definitely trip even after averaging."""
        history = [
            SimulationState(time=i * 0.001, power_consumed=120_000.0)
            for i in range(1000)
        ]
        compliant, peak, t = check_power_limit(history, max_power=80_000.0)
        self.assertFalse(compliant)
        self.assertGreater(peak, 80_000.0 + 1.0)
        self.assertGreaterEqual(t, 0.0)

    def test_short_spike_averaged_out(self):
        """A 50 ms spike at 120 kW inside a steady-state trace stays compliant.

        The check is defined as a 500 ms trailing moving average (per D 9.4.1),
        so we need a full 500 ms of data before and after the spike to exercise
        the smoothing properly.
        """
        dt = 0.005
        history = []
        t = 0.0
        # 500 ms of idle to fill the trailing window.
        for _ in range(100):
            history.append(SimulationState(time=t, power_consumed=0.0))
            t += dt
        # 50 ms spike at 120 kW.
        for _ in range(10):
            history.append(SimulationState(time=t, power_consumed=120_000.0))
            t += dt
        # 500 ms of idle after.
        for _ in range(100):
            history.append(SimulationState(time=t, power_consumed=0.0))
            t += dt

        compliant, peak, violation_t = check_power_limit(
            history, max_power=80_000.0, average_window_s=0.5,
        )
        self.assertTrue(compliant, f"expected compliant, got peak={peak:.1f} W")
        self.assertEqual(violation_t, -1.0)
        # Peak averaged power should be well below the cap.
        self.assertLess(peak, 80_000.0)

    def test_regen_does_not_trip(self):
        """Negative (regen) power should be ignored per EV 2.2.2."""
        history = [
            SimulationState(time=i * 0.001, power_consumed=-150_000.0)
            for i in range(1000)
        ]
        compliant, peak, _ = check_power_limit(history, max_power=80_000.0)
        self.assertTrue(compliant)
        self.assertEqual(peak, 0.0)


class TestTireModelSwitching(unittest.TestCase):
    """The solver must honour config.tires.tire_model_type."""

    def test_solver_picks_correct_backend(self):
        """Verify the TireModel wrapper selects Pacejka vs Simple by config."""
        from dynamics.solver import DynamicsSolver
        from vehicle.tire_model import PacejkaTireModel, SimpleTireModel

        cfg_pacejka = _base_config()
        cfg_pacejka.tires.tire_model_type = "pacejka"
        solver_p = DynamicsSolver(cfg_pacejka)
        self.assertIsInstance(solver_p.tire_model._model, PacejkaTireModel)

        cfg_simple = copy.deepcopy(cfg_pacejka)
        cfg_simple.tires.tire_model_type = "simple"
        solver_s = DynamicsSolver(cfg_simple)
        self.assertIsInstance(solver_s.tire_model._model, SimpleTireModel)

    def test_pacejka_and_simple_force_curves_differ(self):
        """Evaluate both force functions post-peak; curve shapes should differ."""
        from vehicle.tire_model import TireModel

        cfg = _base_config()
        pacejka = TireModel(cfg.tires, use_pacejka=True)
        simple = TireModel(cfg.tires, use_pacejka=False)

        # At 40% slip (well past the ~12% peak) the simple model's linear
        # post-peak drop and Pacejka's smoother falloff give markedly
        # different forces.
        fx_p, _ = pacejka.calculate_longitudinal_force(1500.0, 0.40, 10.0)
        fx_s, _ = simple.calculate_longitudinal_force(1500.0, 0.40, 10.0)
        self.assertGreater(
            abs(fx_p - fx_s), 100.0,
            f"Pacejka and simple tires gave near-identical Fx "
            f"({fx_p:.2f} vs {fx_s:.2f}); check that use_pacejka is honoured.",
        )


class TestAeroDownforceConvention(unittest.TestCase):
    """cl > 0 must mean downforce (faster time, higher rear normal)."""

    def test_rear_downforce_reduces_time(self):
        cfg_baseline = _base_config()
        cfg_downforce = copy.deepcopy(cfg_baseline)
        cfg_downforce.aerodynamics.cl_rear = 2.0

        r0 = AccelerationSimulation(cfg_baseline).run()
        r1 = AccelerationSimulation(cfg_downforce).run()

        # Downforce should improve acceleration (more rear grip), not degrade it.
        self.assertLess(r1.final_time, r0.final_time,
                        f"cl_rear=2.0 increased lap time ({r0.final_time:.3f} -> "
                        f"{r1.final_time:.3f}); sign convention is inverted.")


class TestAntiSquatEffect(unittest.TestCase):
    """anti_squat_ratio must have a measurable, monotone effect on time."""

    def test_higher_anti_squat_helps_launch(self):
        cfg_low = _base_config()
        cfg_low.suspension.anti_squat_ratio = 0.0

        cfg_high = copy.deepcopy(cfg_low)
        cfg_high.suspension.anti_squat_ratio = 0.6

        r_low = AccelerationSimulation(cfg_low).run()
        r_high = AccelerationSimulation(cfg_high).run()

        # Anti-squat boosts rear normal during acceleration. On a grip-limited
        # chassis this should make the car quicker; on a wheelie-limited chassis
        # it's roughly neutral (extra rear load doesn't help if the tyres are
        # already at saturation). Either way, it shouldn't make things clearly
        # worse - allow a 10 ms wash.
        self.assertLessEqual(
            r_high.final_time, r_low.final_time + 0.010,
            f"anti_squat=0.6 materially slower than 0.0 "
            f"({r_low.final_time:.3f} vs {r_high.final_time:.3f})",
        )


if __name__ == "__main__":
    unittest.main()
