"""Integration tests for dynamics solver."""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from simulation.acceleration_sim import AccelerationSimulation


class TestDynamicsSolver(unittest.TestCase):
    """Test dynamics solver integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        config_path = Path(__file__).parent.parent / "config" / "vehicle_configs" / "base_vehicle.json"
        self.config = load_config(config_path)
        self.sim = AccelerationSimulation(self.config)
    
    def test_simulation_completes(self):
        """Test that simulation runs to completion."""
        result = self.sim.run()
        
        # Should complete
        self.assertGreater(result.final_distance, 0.0)
        self.assertGreater(result.final_time, 0.0)
        
        # Should reach target distance (75m)
        self.assertGreaterEqual(result.final_distance, self.config.target_distance - 1.0)  # Allow small error
    
    def test_results_are_valid(self):
        """Test that results are physically valid."""
        result = self.sim.run()
        
        # Times should be positive
        self.assertGreater(result.final_time, 0.0)
        
        # Velocity should be non-negative
        self.assertGreaterEqual(result.final_velocity, 0.0)
        
        # Power should be positive
        self.assertGreaterEqual(result.max_power_used, 0.0)
    
    def test_state_history_exists(self):
        """Test that state history is recorded."""
        result = self.sim.run()
        state_history = self.sim.get_state_history()
        
        # Should have multiple states
        self.assertGreater(len(state_history), 10)
        
        # First state should be at start
        first_state = state_history[0]
        self.assertAlmostEqual(first_state.position, 0.0, places=2)
        self.assertAlmostEqual(first_state.velocity, 0.0, places=2)
        self.assertAlmostEqual(first_state.time, 0.0, places=3)


if __name__ == '__main__':
    unittest.main()

