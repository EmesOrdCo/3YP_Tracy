"""Unit tests for tire model."""

import unittest
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.vehicle_config import TireProperties
from vehicle.tire_model import (
    TireModel,
    SimpleTireModel,
    PacejkaTireModel,
    PacejkaCoefficients,
    longitudinal_slip_ratio,
)


class TestSimpleTireModel(unittest.TestCase):
    """Test simple (piecewise-linear) tire model functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = TireProperties(
            radius_loaded=0.2286,  # 9 inches
            mass=3.0,
            mu_max=1.5,
            mu_slip_optimal=0.15,
            rolling_resistance_coeff=0.015,
            tire_model_type="simple"
        )
        self.tire_model = TireModel(self.config, use_pacejka=False)
    
    def test_slip_ratio_calculation(self):
        """Test slip ratio calculation."""
        # No slip case
        slip = self.tire_model.calculate_slip_ratio(
            wheel_angular_velocity=10.0,
            vehicle_velocity=2.286  # 10 * 0.2286
        )
        self.assertAlmostEqual(slip, 0.0, places=3)
        
        # Positive slip (wheel spinning faster)
        slip = self.tire_model.calculate_slip_ratio(
            wheel_angular_velocity=20.0,
            vehicle_velocity=2.286
        )
        self.assertGreater(slip, 0.0)
        
        # Negative slip (wheel spinning slower - braking)
        slip = self.tire_model.calculate_slip_ratio(
            wheel_angular_velocity=5.0,
            vehicle_velocity=2.286
        )
        self.assertLess(slip, 0.0)
    
    def test_friction_coefficient(self):
        """Test friction coefficient calculation for simple model."""
        simple_model = SimpleTireModel(self.config)
        
        # At optimal slip
        mu = simple_model._calculate_friction_coefficient(0.15)
        self.assertAlmostEqual(mu, self.config.mu_max, places=2)
        
        # Below optimal
        mu_low = simple_model._calculate_friction_coefficient(0.075)
        self.assertLess(mu_low, self.config.mu_max)
        
        # Above optimal
        mu_high = simple_model._calculate_friction_coefficient(0.5)
        self.assertLess(mu_high, self.config.mu_max)
        
        # Zero slip
        mu_zero = simple_model._calculate_friction_coefficient(0.0)
        self.assertAlmostEqual(mu_zero, 0.0, places=2)
    
    def test_longitudinal_force(self):
        """Test tire force calculation."""
        normal_force = 2000.0  # N
        slip_ratio = 0.15  # Optimal
        
        fx, frr = self.tire_model.calculate_longitudinal_force(
            normal_force, slip_ratio, 10.0
        )
        
        # Force should be positive for positive slip
        self.assertGreater(fx, 0.0)
        
        # Rolling resistance should oppose motion
        self.assertLess(frr, 0.0)
        
        # Force magnitude should be reasonable
        self.assertLess(fx, normal_force * self.config.mu_max * 1.1)
    
    def test_rolling_resistance(self):
        """Test rolling resistance calculation."""
        normal_force = 2000.0
        
        fx, frr = self.tire_model.calculate_longitudinal_force(
            normal_force, 0.0, 10.0
        )
        
        # Rolling resistance should be approximately coefficient * normal force
        expected_rr = self.config.rolling_resistance_coeff * normal_force
        self.assertAlmostEqual(abs(frr), expected_rr, places=1)


class TestPacejkaTireModel(unittest.TestCase):
    """Test Pacejka Magic Formula tire model functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = TireProperties(
            radius_loaded=0.2286,
            mass=3.0,
            mu_max=1.5,
            mu_slip_optimal=0.12,
            rolling_resistance_coeff=0.015,
            tire_model_type="pacejka"
        )
        self.tire_model = TireModel(self.config, use_pacejka=True)
    
    def test_slip_ratio_calculation(self):
        """Test slip ratio calculation."""
        # No slip case
        slip = self.tire_model.calculate_slip_ratio(
            wheel_angular_velocity=10.0,
            vehicle_velocity=2.286
        )
        self.assertAlmostEqual(slip, 0.0, places=3)
        
        # Positive slip (wheel spinning faster)
        slip = self.tire_model.calculate_slip_ratio(
            wheel_angular_velocity=20.0,
            vehicle_velocity=2.286
        )
        self.assertGreater(slip, 0.0)
    
    def test_magic_formula_shape(self):
        """Test that Pacejka model produces expected curve shape."""
        normal_force = 1500.0  # Nominal load
        
        # Test force at various slip ratios
        slip_ratios = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]
        forces = []
        
        for slip in slip_ratios:
            fx, _ = self.tire_model.calculate_longitudinal_force(
                normal_force, slip, 10.0
            )
            forces.append(fx)
        
        # Force should be zero at zero slip
        self.assertAlmostEqual(forces[0], 0.0, places=1)
        
        # Force should increase initially
        self.assertGreater(forces[1], forces[0])
        self.assertGreater(forces[2], forces[1])
        
        # Force should reach a peak somewhere
        peak_force = max(forces)
        self.assertGreater(peak_force, 0.0)
        
        # Peak should be around μ * Fz
        mu_peak = self.tire_model.get_peak_friction_coefficient(normal_force)
        expected_peak = mu_peak * normal_force
        self.assertAlmostEqual(peak_force, expected_peak, delta=expected_peak * 0.15)
    
    def test_load_sensitivity(self):
        """Test that friction coefficient decreases with load."""
        # Light load
        mu_light = self.tire_model.get_peak_friction_coefficient(750.0)
        
        # Heavy load
        mu_heavy = self.tire_model.get_peak_friction_coefficient(3000.0)
        
        # Heavy load should have lower μ (load sensitivity)
        self.assertGreater(mu_light, mu_heavy)
    
    def test_optimal_slip_ratio(self):
        """Test optimal slip ratio calculation."""
        optimal_slip = self.tire_model.get_optimal_slip_ratio(1500.0)
        
        # Should be in reasonable range for FSAE tires
        self.assertGreater(optimal_slip, 0.05)
        self.assertLess(optimal_slip, 0.25)
    
    def test_longitudinal_force_at_peak(self):
        """Test force at optimal slip ratio."""
        normal_force = 1500.0
        optimal_slip = self.tire_model.get_optimal_slip_ratio(normal_force)
        
        fx, frr = self.tire_model.calculate_longitudinal_force(
            normal_force, optimal_slip, 10.0
        )
        
        # Force should be close to peak
        mu_peak = self.tire_model.get_peak_friction_coefficient(normal_force)
        expected_peak = mu_peak * normal_force
        
        # Allow 5% tolerance (peak might not be exactly at calculated optimal)
        self.assertAlmostEqual(fx, expected_peak, delta=expected_peak * 0.10)
    
    def test_rolling_resistance(self):
        """Test rolling resistance calculation."""
        normal_force = 2000.0
        
        fx, frr = self.tire_model.calculate_longitudinal_force(
            normal_force, 0.0, 10.0
        )
        
        # Rolling resistance should be approximately coefficient * normal force
        expected_rr = self.config.rolling_resistance_coeff * normal_force
        self.assertAlmostEqual(abs(frr), expected_rr, places=1)
    
    def test_zero_normal_force(self):
        """Test behavior with zero normal force."""
        fx, frr = self.tire_model.calculate_longitudinal_force(
            0.0, 0.15, 10.0
        )
        
        # Should return zero forces
        self.assertEqual(fx, 0.0)
        self.assertEqual(frr, 0.0)


class TestTireModelWrapper(unittest.TestCase):
    """Test TireModel wrapper class functionality."""
    
    def test_pacejka_selection(self):
        """Test that Pacejka model is selected when specified."""
        config = TireProperties(
            radius_loaded=0.2286,
            mass=3.0,
            mu_max=1.5,
            mu_slip_optimal=0.12,
            rolling_resistance_coeff=0.015,
            tire_model_type="pacejka"
        )
        model = TireModel(config, use_pacejka=True)
        self.assertTrue(model.use_pacejka)
        self.assertIsInstance(model._model, PacejkaTireModel)
    
    def test_simple_selection(self):
        """Test that simple model is selected when specified."""
        config = TireProperties(
            radius_loaded=0.2286,
            mass=3.0,
            mu_max=1.5,
            mu_slip_optimal=0.15,
            rolling_resistance_coeff=0.015,
            tire_model_type="simple"
        )
        model = TireModel(config, use_pacejka=False)
        self.assertFalse(model.use_pacejka)
        self.assertIsInstance(model._model, SimpleTireModel)
    
    def test_backward_compatibility(self):
        """Test backward compatibility with legacy attributes."""
        config = TireProperties(
            radius_loaded=0.2286,
            mass=3.0,
            mu_max=1.5,
            mu_slip_optimal=0.15,
            rolling_resistance_coeff=0.015
        )
        model = TireModel(config)
        
        # Legacy attributes should still be accessible
        self.assertEqual(model.mu_max, 1.5)
        self.assertEqual(model.mu_slip_optimal, 0.15)
        self.assertEqual(model.rolling_resistance_coeff, 0.015)
        self.assertEqual(model.radius, 0.2286)


class TestLongitudinalSlipRegularisation(unittest.TestCase):
    """Reference-speed behaviour for slip near rest (launch stability)."""

    def test_high_speed_matches_road_reference(self):
        slip = longitudinal_slip_ratio(10.5, 10.0)
        self.assertAlmostEqual(slip, 0.05, places=5)

    def test_near_rest_small_positive_slip(self):
        slip = longitudinal_slip_ratio(0.01, 0.0)
        self.assertAlmostEqual(slip, 0.2, places=5)

    def test_near_rest_tiny_negative_vehicle_velocity(self):
        slip = longitudinal_slip_ratio(0.001, -0.0001)
        self.assertGreater(slip, -0.5)
        self.assertLess(slip, 0.5)


if __name__ == '__main__':
    unittest.main()

