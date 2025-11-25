"""Unit tests for powertrain model."""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.vehicle_config import PowertrainProperties
from vehicle.powertrain import PowertrainModel


class TestPowertrainModel(unittest.TestCase):
    """Test powertrain model functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = PowertrainProperties(
            motor_torque_constant=0.5,
            motor_max_current=200.0,
            motor_max_speed=1000.0,
            battery_voltage_nominal=300.0,
            battery_internal_resistance=0.01,
            battery_max_current=300.0,
            gear_ratio=10.0,
            max_power_accumulator_outlet=80000.0
        )
        self.powertrain = PowertrainModel(self.config)
    
    def test_motor_speed_calculation(self):
        """Test motor speed calculation."""
        wheel_speed = 50.0  # rad/s
        motor_speed = self.powertrain.calculate_motor_speed(wheel_speed)
        self.assertAlmostEqual(motor_speed, 500.0, places=1)
    
    def test_power_limit_enforcement(self):
        """Test power limit enforcement."""
        # Request high torque at high speed (should hit power limit)
        requested_torque = 1000.0  # N·m at wheels
        motor_speed = 800.0  # rad/s (high speed)
        vehicle_velocity = 20.0  # m/s
        
        wheel_torque, motor_current, power = self.powertrain.calculate_torque(
            requested_torque, motor_speed, vehicle_velocity
        )
        
        # Power should not exceed limit
        self.assertLessEqual(power, self.config.max_power_accumulator_outlet * 1.01)  # Small tolerance
    
    def test_current_limit_enforcement(self):
        """Test motor current limit enforcement."""
        # Request torque that would exceed current limit
        requested_torque = 10000.0  # Very high
        motor_speed = 100.0
        vehicle_velocity = 2.0
        
        wheel_torque, motor_current, power = self.powertrain.calculate_torque(
            requested_torque, motor_speed, vehicle_velocity
        )
        
        # Current should be limited
        max_current = self.config.motor_max_current
        self.assertLessEqual(abs(motor_current), max_current * 1.01)  # Small tolerance


if __name__ == '__main__':
    unittest.main()

