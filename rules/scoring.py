"""Scoring calculator (D 5.3.2)."""

from typing import Optional


def calculate_acceleration_score(
    team_time: float,
    fastest_time: float,
    max_points: float = 75.0
) -> float:
    """
    Calculate acceleration event score using Formula Student formula (D 5.3.2).
    
    Formula: M_ACCELERATION_SCORE = 0.95 * Pmax * ((Tmax / Tteam - 1) / 0.5) + 0.05 * Pmax
    
    Where:
    - Pmax = maximum points for the event (default 75)
    - Tteam = team's best time including penalties
    - Tmax = 1.5 times the fastest time
    
    Args:
        team_time: Team's time (s)
        fastest_time: Fastest time in competition (s)
        max_points: Maximum points for event (default 75)
        
    Returns:
        Score (points)
    """
    # Calculate Tmax
    t_max = 1.5 * fastest_time
    
    # Cap team time to Tmax
    t_team = min(team_time, t_max)
    
    # Calculate score
    if t_team <= 0:
        return 0.0
    
    score = 0.95 * max_points * ((t_max / t_team - 1) / 0.5) + 0.05 * max_points
    
    # Ensure score is non-negative
    return max(0.0, score)


def calculate_tmax(fastest_time: float) -> float:
    """
    Calculate Tmax (1.5 times fastest time).
    
    Args:
        fastest_time: Fastest time (s)
        
    Returns:
        Tmax (s)
    """
    return 1.5 * fastest_time


