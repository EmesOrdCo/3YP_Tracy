"""Tests for the anti-wheelie launch controller and related physics.

These tests pin the behaviour of the three guards added to `DynamicsSolver`:

1. ``_wheelie_torque_cap`` - static pitch-moment balance.
2. Closed-loop front-Fz feedback - scales torque when measured front load
   drops toward the wheelie threshold.
3. Slip-ratio governor - zeros torque if rear slip exceeds ~2x optimum.

Also covers the motor field-weakening envelope (``create_motor_from_config``)
and the supercapacitor voltage-decay behaviour, since those sit upstream of
the controller and directly shape the torque request.
"""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from config.vehicle_config import (
    AerodynamicsProperties,
    ControlProperties,
    EnvironmentProperties,
    MassProperties,
    PowertrainProperties,
    SuspensionProperties,
    TireProperties,
    VehicleConfig,
)
from dynamics.solver import DynamicsSolver
from simulation.acceleration_sim import AccelerationSimulation
from vehicle.motor_model import create_motor_from_config, create_yasa_p400r


CONFIG_DIR = Path(__file__).parent.parent / "config" / "vehicle_configs"


def _base_config() -> VehicleConfig:
    return load_config(CONFIG_DIR / "base_vehicle.json")


class TestWheelieTorqueCap(unittest.TestCase):
    """Static pitch-moment balance in ``DynamicsSolver._wheelie_torque_cap``."""

    def setUp(self) -> None:
        self.solver = DynamicsSolver(_base_config())

    def test_forward_cg_allows_more_torque_than_rear_cg(self):
        """Moving CG forward should raise the wheelie torque cap."""
        cfg_rear = _base_config()
        cfg_rear.mass.cg_x = 0.80 * cfg_rear.mass.wheelbase
        cfg_fwd = _base_config()
        cfg_fwd.mass.cg_x = 0.55 * cfg_fwd.mass.wheelbase

        solver_rear = DynamicsSolver(cfg_rear)
        solver_fwd = DynamicsSolver(cfg_fwd)

        cap_rear = solver_rear._wheelie_torque_cap(0.0, 0.0, 0.0, cfg_rear.mass.total_mass)
        cap_fwd = solver_fwd._wheelie_torque_cap(0.0, 0.0, 0.0, cfg_fwd.mass.total_mass)

        self.assertGreater(
            cap_fwd, cap_rear,
            f"Forward CG should tolerate more drive torque: rear={cap_rear:.0f}, fwd={cap_fwd:.0f}"
        )

    def test_drag_and_rolling_resistance_raise_the_cap(self):
        """Drag + rolling resistance mean the drive force needs to be larger
        for the *same* net longitudinal acceleration, so the torque cap is
        higher when those resistive forces are non-zero."""
        cfg = _base_config()
        solver = DynamicsSolver(cfg)
        cap_no_drag = solver._wheelie_torque_cap(0.0, 0.0, 0.0, cfg.mass.total_mass)
        cap_with_drag = solver._wheelie_torque_cap(
            0.0, drag_force=500.0, rr_total=50.0,
            effective_mass=cfg.mass.total_mass,
        )
        self.assertGreater(cap_with_drag, cap_no_drag)

    def test_front_downforce_raises_the_cap(self):
        """Extra front Fz from aero downforce should raise the torque cap."""
        cfg = _base_config()
        solver = DynamicsSolver(cfg)
        cap_no_df = solver._wheelie_torque_cap(0.0, 0.0, 0.0, cfg.mass.total_mass)
        cap_with_df = solver._wheelie_torque_cap(
            downforce_front=500.0, drag_force=0.0, rr_total=0.0,
            effective_mass=cfg.mass.total_mass,
        )
        self.assertGreater(cap_with_df, cap_no_df)

    def test_zero_cg_height_returns_infinity(self):
        """If cg_z = 0, the car physically can't wheelie; cap must be +inf."""
        cfg = _base_config()
        cfg.mass.cg_z = 0.0
        solver = DynamicsSolver(cfg)
        cap = solver._wheelie_torque_cap(0.0, 0.0, 0.0, cfg.mass.total_mass)
        self.assertEqual(cap, float("inf"))


class TestFzFeedback(unittest.TestCase):
    """Closed-loop anti-wheelie Fz feedback in the solver.

    Below the static-cap case we rely on the Fz-feedback guard to catch
    transient overshoots (Pacejka peak passing through during slip spin-up).
    The solver exposes this via ``_fz_feedback_threshold`` and
    ``_last_fz_front``; we drive those directly to probe torque scaling.
    """

    def test_torque_scales_linearly_to_zero_as_front_load_collapses(self):
        cfg = _base_config()
        solver = DynamicsSolver(cfg)

        class _State:
            time = 0.5
            velocity = 5.0
            wheel_angular_velocity_rear = 25.0

        # Above threshold: no scaling.
        solver._last_fz_front = solver._fz_feedback_threshold + 500.0
        t_above = solver._calculate_requested_torque(_State(), 900.0, 0.10, float("inf"))

        # At half the threshold: torque roughly halved.
        solver._last_fz_front = solver._fz_feedback_threshold * 0.5
        t_half = solver._calculate_requested_torque(_State(), 900.0, 0.10, float("inf"))

        # At zero: torque fully cut.
        solver._last_fz_front = 0.0
        t_zero = solver._calculate_requested_torque(_State(), 900.0, 0.10, float("inf"))

        self.assertGreater(t_above, 0.0)
        self.assertAlmostEqual(t_half, 0.5 * t_above, delta=0.02 * t_above)
        self.assertAlmostEqual(t_zero, 0.0, delta=1e-6)


class TestSlipGovernor(unittest.TestCase):
    """Slip-ratio governor cuts torque above 2x optimal slip."""

    def test_torque_is_zero_when_slip_exceeds_ceiling(self):
        cfg = _base_config()
        solver = DynamicsSolver(cfg)

        class _State:
            time = 0.5
            velocity = 5.0
            wheel_angular_velocity_rear = 60.0  # wheel spinning fast -> slip > ceiling

        solver._last_fz_front = 1e6  # disable Fz feedback so we only test the governor

        # current_slip_ratio = 0.5 (well above ~2 * 0.13 = 0.26 ceiling).
        torque = solver._calculate_requested_torque(_State(), 900.0, 0.5, float("inf"))
        self.assertEqual(torque, 0.0)

    def test_torque_nonzero_at_moderate_slip(self):
        cfg = _base_config()
        solver = DynamicsSolver(cfg)

        class _State:
            time = 0.5
            velocity = 5.0
            wheel_angular_velocity_rear = 25.0  # small overshoot above vehicle speed

        solver._last_fz_front = 1e6

        # Moderate slip, below ceiling.
        torque = solver._calculate_requested_torque(_State(), 900.0, 0.10, float("inf"))
        self.assertGreater(torque, 0.0)


class TestMotorFieldWeakening(unittest.TestCase):
    """``create_motor_from_config`` should produce a consistent envelope that
    respects motor_max_speed and bus voltage."""

    def test_base_speed_scales_with_bus_voltage(self):
        """Doubling rated_voltage should raise the field-weakening base speed.

        The relationship isn't exactly linear because ``create_motor_from_config``
        floors peak_power at 80 kW (so the FS rule is always reachable) which
        clips the low-voltage branch; we just require monotonicity plus a
        meaningful change.
        """
        cfg_low = _base_config()
        cfg_low.powertrain.battery_voltage_nominal = 350.0
        motor_low = create_motor_from_config(cfg_low.powertrain)

        cfg_high = _base_config()
        cfg_high.powertrain.battery_voltage_nominal = 700.0
        motor_high = create_motor_from_config(cfg_high.powertrain)

        self.assertGreater(
            motor_high.base_speed_at_rated_voltage,
            motor_low.base_speed_at_rated_voltage + 10.0,
            msg="Higher rated voltage must push the field-weakening knee up.",
        )

    def test_base_speed_never_exceeds_max_speed(self):
        """A small motor with huge peak_power shouldn't push base_speed past max_speed."""
        cfg = _base_config()
        cfg.powertrain.motor_max_speed = 400.0  # artificially low
        cfg.powertrain.motor_max_current = 800.0  # very high -> large peak_power
        motor = create_motor_from_config(cfg.powertrain)
        self.assertLess(motor.base_speed_at_rated_voltage, motor.max_speed)

    def test_torque_envelope_drops_past_max_speed(self):
        """Above motor_max_speed the torque must collapse to zero."""
        motor = create_yasa_p400r()
        torque_below, _, _ = motor.calculate_max_torque(
            0.9 * motor.max_speed, motor.rated_voltage,
        )
        torque_above, _, _ = motor.calculate_max_torque(
            1.05 * motor.max_speed, motor.rated_voltage,
        )
        self.assertGreater(torque_below, 0.0)
        self.assertEqual(torque_above, 0.0)


class TestSupercapDecay(unittest.TestCase):
    """Supercap voltage must decay under load; battery voltage should not."""

    def _run_and_sample_voltage(self, storage_type: str):
        cfg = _base_config()
        cfg.powertrain.energy_storage_type = storage_type
        sim = AccelerationSimulation(cfg)
        result = sim.run()
        hist = sim.get_state_history()
        v_start = hist[1].dc_bus_voltage
        v_end = hist[-1].dc_bus_voltage
        return v_start, v_end, result.final_time

    def test_supercap_voltage_decays_during_run(self):
        v0, v1, _ = self._run_and_sample_voltage("supercapacitor")
        self.assertGreater(v0, v1, f"Supercap voltage should fall: start={v0:.1f}, end={v1:.1f}")
        drop = v0 - v1
        # Full 75 m run at ~80 kW should drop several volts from a 600 V stack.
        self.assertGreater(drop, 1.0, f"Supercap drop {drop:.2f} V too small")

    def test_battery_voltage_holds_during_run(self):
        v0, v1, _ = self._run_and_sample_voltage("battery")
        # Battery model applies an instantaneous IR drop proportional to draw
        # (~20 V for the supercap-sized internal resistance in base_vehicle at
        # 80 kW). What matters is that it stays in a tight band rather than
        # decaying monotonically like a supercap, so we cap the whole-run
        # range at 10 % of the starting voltage.
        self.assertLess(abs(v0 - v1), 0.10 * v0,
                        f"Battery voltage wandered too much: {v0:.1f} -> {v1:.1f}")


class TestConfigValidate(unittest.TestCase):
    """VehicleConfig.validate() should catch obvious bad inputs."""

    def _minimal_cfg(self) -> VehicleConfig:
        return VehicleConfig(
            mass=MassProperties(200.0, 1.0, 0.22, 1.6, 1.2, 1.2, 100.0, 120.0, 10.0, 10.0),
            tires=TireProperties(radius_loaded=0.23, mass=3.0, mu_max=1.6,
                                 mu_slip_optimal=0.14, rolling_resistance_coeff=0.01,
                                 tire_model_type="pacejka"),
            powertrain=PowertrainProperties(
                motor_torque_constant=0.822, motor_max_current=285.0,
                motor_max_speed=838.0, battery_voltage_nominal=600.0,
                battery_internal_resistance=0.14, battery_max_current=300.0,
                gear_ratio=5.0,
            ),
            aerodynamics=AerodynamicsProperties(cda=0.8),
            suspension=SuspensionProperties(),
            control=ControlProperties(),
            environment=EnvironmentProperties(),
        )

    def test_clean_config_has_no_errors(self):
        self.assertEqual(self._minimal_cfg().validate(), [])

    def test_cg_outside_wheelbase_is_flagged(self):
        cfg = self._minimal_cfg()
        cfg.mass.cg_x = cfg.mass.wheelbase + 0.1
        self.assertTrue(any("cg_x" in e for e in cfg.validate()))

    def test_negative_cg_height_is_flagged(self):
        cfg = self._minimal_cfg()
        cfg.mass.cg_z = -0.05
        self.assertTrue(any("cg_z" in e for e in cfg.validate()))

    def test_unsprung_exceeding_total_is_flagged(self):
        cfg = self._minimal_cfg()
        cfg.mass.unsprung_mass_front = 150.0
        cfg.mass.unsprung_mass_rear = 150.0
        self.assertTrue(any("unsprung" in e for e in cfg.validate()))

    def test_supercap_min_voltage_above_full_stack_is_flagged(self):
        cfg = self._minimal_cfg()
        cfg.powertrain.energy_storage_type = "supercapacitor"
        cfg.powertrain.supercap_num_cells = 200
        cfg.powertrain.supercap_cell_voltage = 3.0
        cfg.powertrain.supercap_min_voltage = 1000.0  # > 600 V stack
        self.assertTrue(any("supercap_min_voltage" in e for e in cfg.validate()))

    def test_over_80kw_power_cap_is_flagged(self):
        cfg = self._minimal_cfg()
        cfg.powertrain.max_power_accumulator_outlet = 120_000.0
        self.assertTrue(any("80 kW" in e or "EV 2.2" in e for e in cfg.validate()))


if __name__ == "__main__":
    unittest.main()
