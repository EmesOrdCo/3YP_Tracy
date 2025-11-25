"""Time limit checking (D 5.3.1)."""

from typing import Tuple
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


def check_time_limit(
    final_state: SimulationState,
    max_time: float = 25.0
) -> Tuple[bool, float]:
    """
    Check if time limit is exceeded (D 5.3.1).
    
    Formula Student rule D 5.3.1: Runs with time > 25s will be disqualified.
    
    Args:
        final_state: Final simulation state
        max_time: Maximum allowed time (s), default 25.0
        
    Returns:
        Tuple of (compliant, final_time)
        - compliant: True if time is within limit
        - final_time: Final time (s)
    """
    final_time = final_state.time
    compliant = final_time <= max_time
    return compliant, final_time

