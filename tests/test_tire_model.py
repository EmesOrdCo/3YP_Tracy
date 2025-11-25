"""Unit tests for tire model."""

import unittest
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.vehicle_config import TireProperties
from vehicle.tire_model import TireModel


class TestTireModel(unittest.TestCase):
    """Test tire model functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = TireProperties(
            radius_loaded=0.2286,  # 9 inches
            mass=3.0,
            mu_max=1.5,
            mu_slip_optimal=0.15,
            rolling_resistance_coeff=0.015
        )
        self.tire_model = TireModel(self.config)
    
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
        """Test friction coefficient calculation."""
        # At optimal slip
        mu = self.tire_model._calculate_friction_coefficient(0.15)
        self.assertAlmostEqual(mu, self.config.mu_max, places=2)
        
        # Below optimal
        mu_low = self.tire_model._calculate_friction_coefficient(0.075)
        self.assertLess(mu_low, self.config.mu_max)
        
        # Above optimal
        mu_high = self.tire_model._calculate_friction_coefficient(0.5)
        self.assertLess(mu_high, self.config.mu_max)
        
        # Zero slip
        mu_zero = self.tire_model._calculate_friction_coefficient(0.0)
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


if __name__ == '__main__':
    unittest.main()

