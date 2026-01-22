"""Wheelie detection check."""

from typing import List, Tuple
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..dynamics.state import SimulationState
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from dynamics.state import SimulationState


def check_wheelie(
    state_history: List[SimulationState],
    wheelie_threshold: float = 0.1
) -> Tuple[bool, float, float]:
    """
    Check if vehicle experiences a wheelie (front wheels lift off).
    
    A wheelie occurs when the front normal force drops below a threshold.
    This indicates the front wheels are lifting off the ground, which:
    - Loss of front wheel traction and steering control
    - Potentially unstable vehicle behavior
    - May violate vehicle stability requirements
    
    Args:
        state_history: List of simulation states
        wheelie_threshold: Minimum front normal force (N) to avoid wheelie warning.
                          Default 0.1 N (essentially zero, but accounts for numerical precision)
        
    Returns:
        Tuple of (wheelie_detected, min_front_normal_force, time_of_wheelie)
        - wheelie_detected: True if front normal force ever drops below threshold
        - min_front_normal_force: Minimum front normal force during simulation (N)
        - time_of_wheelie: Time of first wheelie occurrence (s), or -1 if none detected
    """
    min_front_normal = float('inf')
    time_of_wheelie = -1.0
    wheelie_detected = False
    
    for state in state_history:
        # Skip initial state (time = 0.0) since forces haven't been calculated yet
        # Only check states after the simulation has started (time > 0 or position > 0)
        if state.time <= 0.0 and state.position <= 0.0:
            continue
            
        front_normal = state.normal_force_front
        
        # Track minimum front normal force
        if front_normal < min_front_normal:
            min_front_normal = front_normal
        
        # Check if wheelie occurs (front normal force drops below threshold)
        if front_normal <= wheelie_threshold and time_of_wheelie < 0:
            wheelie_detected = True
            time_of_wheelie = state.time
    
    # If no wheelie detected, min_front_normal should be positive
    if not wheelie_detected:
        min_front_normal = max(0.0, min_front_normal) if min_front_normal != float('inf') else 0.0
    
    return wheelie_detected, min_front_normal, time_of_wheelie


def calculate_wheelie_limit_acceleration(
    mass: float,
    cg_x: float,
    cg_z: float,
    wheelbase: float,
    front_downforce: float = 0.0
) -> float:
    """
    Calculate the maximum acceleration before wheelie occurs.
    
    This calculates the acceleration at which front normal force becomes zero.
    Derived from: front_normal = front_static - load_transfer + downforce = 0
    
    Args:
        mass: Vehicle mass (kg)
        cg_x: Distance from front axle to CG (m)
        cg_z: Height of CG above ground (m)
        wheelbase: Vehicle wheelbase (m)
        front_downforce: Aerodynamic downforce on front (N)
        
    Returns:
        Maximum acceleration before wheelie (m/s²)
    """
    g = 9.81  # m/s²
    total_weight = mass * g
    
    # Static front load
    b = wheelbase - cg_x  # Distance from CG to front axle
    front_static = total_weight * (b / wheelbase)
    
    # Load transfer formula: ΔFz = (m * a * h_cg) / wheelbase
    # Front loses load during acceleration
    # Wheelie occurs when: front_static - load_transfer + front_downforce = 0
    # Solving for acceleration:
    # front_static - (m * a * cg_z) / wheelbase + front_downforce = 0
    # (m * a * cg_z) / wheelbase = front_static + front_downforce
    # a = (front_static + front_downforce) * wheelbase / (m * cg_z)
    
    if cg_z > 0 and mass > 0:
        max_accel = (front_static + front_downforce) * wheelbase / (mass * cg_z)
        return max_accel
    else:
        return float('inf')  # Can't wheelie if CG height is zero

