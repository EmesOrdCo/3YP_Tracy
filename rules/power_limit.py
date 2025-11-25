"""Power limit checking (EV 2.2)."""

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


def check_power_limit(
    state_history: List[SimulationState],
    max_power: float = 80e3
) -> Tuple[bool, float, float]:
    """
    Check if power limit is exceeded (EV 2.2).
    
    Formula Student rule EV 2.2: TS power at accumulator outlet must not exceed 80 kW.
    
    Args:
        state_history: List of simulation states
        max_power: Maximum allowed power (W), default 80 kW
        
    Returns:
        Tuple of (compliant, max_power_used, time_of_violation)
        - compliant: True if power never exceeds limit
        - max_power_used: Maximum power used during simulation (W)
        - time_of_violation: Time of first violation (s), or -1 if compliant
    """
    max_power_used = 0.0
    time_of_violation = -1.0
    
    for state in state_history:
        power = abs(state.power_consumed)
        if power > max_power_used:
            max_power_used = power
            if power > max_power and time_of_violation < 0:
                time_of_violation = state.time
    
    compliant = max_power_used <= max_power
    return compliant, max_power_used, time_of_violation


