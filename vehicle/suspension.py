"""Suspension model for load transfer and geometry effects."""

import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import SuspensionProperties
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import SuspensionProperties


class SuspensionModel:
    """Suspension geometry and load transfer model."""
    
    def __init__(self, config: SuspensionProperties):
        """
        Initialize suspension model.
        
        Args:
            config: Suspension properties configuration
        """
        self.config = config
        self.anti_squat_ratio = config.anti_squat_ratio
        self.ride_height_front = config.ride_height_front
        self.ride_height_rear = config.ride_height_rear
    
    def calculate_anti_squat_effect(
        self,
        longitudinal_acceleration: float,
        normal_force_rear: float,
    ) -> float:
        """
        Legacy API: return a small positive load "added" to the rear axle that
        scales with anti_squat_ratio. Kept for compatibility; new code should
        use :meth:`load_transfer_correction` instead.
        """
        if self.anti_squat_ratio > 0:
            return normal_force_rear * self.anti_squat_ratio * 0.1
        return 0.0

    def load_transfer_correction(
        self,
        mass: float,
        longitudinal_acceleration: float,
        cg_height: float,
        wheelbase: float,
    ) -> float:
        """
        Return how much of the longitudinal load transfer is handled by
        suspension geometry rather than spring compression.

        In this simplified model we treat ``anti_squat_ratio`` in [0, 1] as the
        fraction of the elastic rear load transfer that is replaced by
        suspension geometry action. The axle LOADS themselves don't change in a
        strict 2-axle quasi-static model (physics demands the full transfer),
        but at low fidelity this acts as a tuning knob for how aggressively the
        rear hooks up off the line:

            rear_gain  = +anti_squat_ratio * (m * a * h_cg / L) * scale
            front_gain = -rear_gain

        where ``scale`` is a small effective factor (0.2) so that this remains
        a perturbation. Returns ``rear_gain``.

        A 100% anti-squat setup will therefore see slightly higher rear normal
        during acceleration in this model — roughly matching the observed
        on-track benefit of suspensions that maintain rear ride height during
        launch.

        Args:
            mass: Vehicle mass (kg).
            longitudinal_acceleration: Longitudinal acceleration (m/s^2).
            cg_height: CG height above ground (m).
            wheelbase: Wheelbase (m).

        Returns:
            Signed delta to rear normal force (N). Front delta = -rear_delta.
        """
        if self.anti_squat_ratio <= 0 or wheelbase <= 0 or longitudinal_acceleration <= 0:
            return 0.0
        geometric_fraction = min(1.0, self.anti_squat_ratio) * 0.2
        elastic_transfer = mass * longitudinal_acceleration * cg_height / wheelbase
        return float(geometric_fraction * elastic_transfer)


