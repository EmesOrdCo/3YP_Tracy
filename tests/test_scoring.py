"""Unit tests for scoring calculator."""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rules.scoring import calculate_acceleration_score, calculate_tmax


class TestScoring(unittest.TestCase):
    """Test scoring functionality."""
    
    def test_tmax_calculation(self):
        """Test Tmax calculation."""
        fastest_time = 4.5
        tmax = calculate_tmax(fastest_time)
        self.assertAlmostEqual(tmax, 6.75, places=2)
    
    def test_score_calculation(self):
        """Test score calculation."""
        fastest_time = 4.5
        team_time = 5.0
        
        score = calculate_acceleration_score(team_time, fastest_time, max_points=75.0)
        
        # Score should be positive
        self.assertGreater(score, 0.0)
        
        # Score should be less than max points
        self.assertLessEqual(score, 75.0)
        
        # Faster time should give higher score
        faster_score = calculate_acceleration_score(4.7, fastest_time, max_points=75.0)
        slower_score = calculate_acceleration_score(5.0, fastest_time, max_points=75.0)
        self.assertGreater(faster_score, slower_score)
    
    def test_score_at_fastest_time(self):
        """Test score when team equals fastest time."""
        fastest_time = 4.5
        team_time = 4.5
        
        score = calculate_acceleration_score(team_time, fastest_time, max_points=75.0)
        
        # Should get maximum score
        self.assertAlmostEqual(score, 75.0, places=1)
    
    def test_score_at_tmax(self):
        """Test score at Tmax threshold."""
        fastest_time = 4.5
        tmax = calculate_tmax(fastest_time)
        
        score = calculate_acceleration_score(tmax, fastest_time, max_points=75.0)
        
        # Should get minimum score (0.05 * max_points)
        self.assertAlmostEqual(score, 0.05 * 75.0, places=1)
    
    def test_score_beyond_tmax(self):
        """Test score beyond Tmax is capped."""
        fastest_time = 4.5
        tmax = calculate_tmax(fastest_time)
        
        score_at_tmax = calculate_acceleration_score(tmax, fastest_time, max_points=75.0)
        score_beyond = calculate_acceleration_score(tmax + 1.0, fastest_time, max_points=75.0)
        
        # Should be same (capped)
        self.assertAlmostEqual(score_at_tmax, score_beyond, places=1)


if __name__ == '__main__':
    unittest.main()

