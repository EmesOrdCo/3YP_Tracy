"""Power limit checking (EV 2.2 / D 9.4.1)."""

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


def _moving_average(values: List[float], times: List[float],
                    window_s: float) -> List[float]:
    """Centred-right moving average matching the FS DL 500 ms definition.

    Averages over the preceding ``window_s`` seconds of samples for each point
    (i.e. at time t the returned value is the mean power over [t - window, t]).
    Assumes times are monotonically non-decreasing.
    """
    n = len(values)
    out = [0.0] * n
    if n == 0:
        return out

    left = 0
    running_sum = 0.0
    for right in range(n):
        running_sum += values[right]
        while times[right] - times[left] > window_s and left < right:
            running_sum -= values[left]
            left += 1
        count = right - left + 1
        out[right] = running_sum / count if count > 0 else 0.0
    return out


def check_power_limit(
    state_history: List[SimulationState],
    max_power: float = 80e3,
    average_window_s: float = 0.5,
) -> Tuple[bool, float, float]:
    """
    Check if motoring power exceeds the EV 2.2 limit, per the D 9.4.1 definition.

    Formula Student rules:
      - EV 2.2.1: TS power at the outlet of the TSAC must not exceed 80 kW.
      - EV 2.2.2: Regenerating energy is unrestricted.
      - D 9.4.1: Violations are judged from the data logger after a 500 ms
        moving average on the power signal.

    This checker therefore:
      - Uses ``state.power_consumed`` signed (positive = motoring, negative =
        regen) and ignores regen (negative) samples when evaluating the cap.
      - Applies a 500 ms trailing moving average before comparing to
        ``max_power``.

    Args:
        state_history: Ordered list of simulation states (must carry ``time``
            and ``power_consumed``).
        max_power: Maximum allowed motoring power (W). Default 80 kW.
        average_window_s: Moving-average window (s). Default 0.5 s per D 9.4.1.

    Returns:
        Tuple of (compliant, max_power_used, time_of_violation):
          - compliant: True iff the 500 ms-averaged motoring power stays at or
            below ``max_power`` throughout.
          - max_power_used: Peak averaged motoring power observed (W). Not
            clamped to ``max_power``, so callers can see by how much the
            vehicle overshot.
          - time_of_violation: Time of first violation (s), or -1.0 if
            compliant.
    """
    if not state_history:
        return True, 0.0, -1.0

    # Positive-only (motoring) power series.
    motoring = [max(0.0, state.power_consumed) for state in state_history]
    times = [state.time for state in state_history]

    if average_window_s > 0:
        series = _moving_average(motoring, times, average_window_s)
    else:
        series = motoring

    # Absolute tolerance (1 W) absorbs floating-point noise from the running
    # sum in _moving_average so power held exactly at the cap doesn't trip.
    tol = 1.0

    max_power_used = 0.0
    time_of_violation = -1.0
    for t, p in zip(times, series):
        if p > max_power_used:
            max_power_used = p
        if p > max_power + tol and time_of_violation < 0:
            time_of_violation = t

    compliant = max_power_used <= max_power + tol
    return compliant, max_power_used, time_of_violation
