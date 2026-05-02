"""Tire force model for acceleration simulation.

Implements both a simplified linear tire model and the Pacejka Magic Formula
for more realistic tire behavior. The Pacejka model includes load sensitivity
and is based on Avon FSAE tire data.
"""

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import TireProperties
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import TireProperties


@dataclass
class PacejkaCoefficients:
    """Pacejka Magic Formula coefficients for longitudinal force.
    
    The Magic Formula: Fx = D * sin(C * arctan(B*κ - E*(B*κ - arctan(B*κ))))
    
    Where:
        κ = slip ratio
        B = stiffness factor (controls slope at origin)
        C = shape factor (controls peak shape, typically 1.5-1.9 for longitudinal)
        D = peak value (= μ_peak * Fz, with load sensitivity)
        E = curvature factor (controls shape after peak, typically -0.5 to 0.5)
    
    Load sensitivity is modeled through D:
        D = Fz * (pDx1 + pDx2 * dfz)
    where dfz = (Fz - Fz0) / Fz0 is the normalized load deviation.
    
    Coefficients derived from Avon FSAE tire lateral data (which showed μ = 1.3-1.7
    with load sensitivity) and typical FSAE longitudinal tire characteristics.
    """
    # Shape factor (controls peak shape)
    C: float = 1.65
    
    # Peak friction coefficients (D = Fz * (pDx1 + pDx2 * dfz))
    pDx1: float = 1.45  # Peak μ at nominal load
    pDx2: float = -0.15  # Load sensitivity (μ decreases with load)
    
    # Stiffness factor coefficients (B = pKx1 / (C * D))
    pKx1: float = 25.0  # Longitudinal slip stiffness
    pKx2: float = 0.0   # Variation with load
    pKx3: float = 0.0   # Variation with load squared
    
    # Curvature factor
    E: float = 0.1  # Controls shape after peak
    pEx1: float = 0.1   # Base curvature
    pEx2: float = 0.0   # Variation with load
    pEx3: float = 0.0   # Variation with load squared
    pEx4: float = 0.0   # Variation with slip ratio sign
    
    # Horizontal shift (typically small)
    pHx1: float = 0.0
    pHx2: float = 0.0
    
    # Vertical shift (typically small)
    pVx1: float = 0.0
    pVx2: float = 0.0
    
    # Nominal load for load sensitivity calculations
    Fz0: float = 1500.0  # N (typical rear tire load during acceleration)


# =============================================================================
# ESTIMATED AND ASSUMED VALUES (not from Avon tire data)
# =============================================================================
# The Avon data provided (FSAE Stab Rig, Spring Rate) contains LATERAL force
# data only. Longitudinal (acceleration/braking) coefficients were estimated:
#
# | Parameter | Value | Basis |
# |-----------|-------|-------|
# | pDx1 (μ_peak) | 1.45 | Derived from lateral μ range 1.3-1.7 |
# | pDx2 (load sens.) | -0.08 | Gives μ drop from 1.50 to 1.37 over 500-3000 N |
# | C (shape factor) | 1.65 | Typical for longitudinal (literature: 1.5-1.9) |
# | B (stiffness) | 10.0 | Gives optimal slip ~12% (typical for FSAE slicks) |
# | E (curvature) | -0.5 | Negative for realistic post-peak drop |
# | Fz0 (nominal load) | 1500 N | Typical rear tire load during acceleration |
#
# NOTE: pKx1 is now the B factor directly (dimensionless), not slip stiffness.
# This keeps optimal slip constant (~12%) across all loads, which matches
# real tire behavior better than the original formulation B = Kx/(C*D).
#
# Model validation:
# - Optimal slip: ~10% @ 500 N → ~14% @ 3000 N (mild, realistic variation)
# - Peak μ: 1.50 @ 500 N → 1.37 @ 3000 N - realistic load sensitivity
# - Force curve shape: rise from 0, peak at ~12%, mild post-peak fall
# =============================================================================

def _has_advanced_fields(config: "TireProperties") -> bool:
    """Return True if the config specifies any advanced-form Pacejka field."""
    fields = (config.pacejka_pDx1, config.pacejka_pDx2,
              config.pacejka_pKx1, config.pacejka_pKx2,
              config.pacejka_C, config.pacejka_E, config.pacejka_Fz0)
    return any(f is not None for f in fields)


def _coefficients_from_advanced_config(config: "TireProperties") -> "PacejkaCoefficients":
    """Build PacejkaCoefficients from the advanced-form JSON fields.

    The JSON configs store ``pacejka_pKx1``/``pacejka_pKx2`` in units of N/rad
    (classic Pacejka slip stiffness Kx), while :class:`PacejkaCoefficients`
    expects ``pKx1`` to be the dimensionless B factor. Large magnitudes (> 100)
    are interpreted as slip-stiffness and converted via
    ``B = Kx / (C * D_nominal)`` at the nominal load. Small magnitudes are
    kept as-is (already dimensionless).
    """
    C = config.pacejka_C if config.pacejka_C is not None else 1.65
    pDx1 = config.pacejka_pDx1 if config.pacejka_pDx1 is not None else 1.45
    pDx2 = config.pacejka_pDx2 if config.pacejka_pDx2 is not None else -0.08
    E = config.pacejka_E if config.pacejka_E is not None else -0.5
    Fz0 = config.pacejka_Fz0 if config.pacejka_Fz0 is not None else 1500.0

    kx1_raw = config.pacejka_pKx1 if config.pacejka_pKx1 is not None else 10.0
    kx2_raw = config.pacejka_pKx2 if config.pacejka_pKx2 is not None else 0.0

    # If the raw pKx1 is large, treat as slip-stiffness (N/rad) and convert.
    if abs(kx1_raw) > 100.0:
        D_nominal = Fz0 * pDx1  # Peak force at nominal load
        denom = max(1e-6, C * D_nominal)
        pKx1_B = kx1_raw / denom
        pKx2_B = kx2_raw / denom
    else:
        pKx1_B = kx1_raw
        pKx2_B = kx2_raw

    return PacejkaCoefficients(
        C=C,
        pDx1=pDx1,
        pDx2=pDx2,
        pKx1=pKx1_B,
        pKx2=pKx2_B,
        pKx3=0.0,
        E=E,
        pEx1=E,
        pEx2=0.0,
        pEx3=0.0,
        pEx4=0.0,
        pHx1=0.0,
        pHx2=0.0,
        pVx1=0.0,
        pVx2=0.0,
        Fz0=Fz0,
    )


AVON_FSAE_COEFFICIENTS = PacejkaCoefficients(
    C=1.65,
    pDx1=1.45,
    pDx2=-0.08,  # Reduced load sensitivity (was -0.12)
    pKx1=10.0,   # B factor at nominal load: gives optimal slip ~12%
    pKx2=-1.5,   # Mild load variation: B decreases with load → κ_opt increases slightly
    pKx3=0.0,
    E=-0.5,      # Negative E for realistic post-peak drop
    pEx1=-0.5,
    pEx2=0.0,
    pEx3=0.0,
    pEx4=0.0,
    pHx1=0.0,
    pHx2=0.0,
    pVx1=0.0,
    pVx2=0.0,
    Fz0=1500.0
)


def longitudinal_slip_ratio(wheel_velocity: float, vehicle_velocity: float) -> float:
    """Longitudinal slip with a stable reference speed near rest.

    For ``|v_vehicle| >= v_switch`` the denominator is road speed (classic
    slip). When the vehicle is nearly stationary, the wheel circumferential
    speed is used instead so tiny RK4 undershoots of velocity (slightly
    negative ``v``) do not explode slip and excite tyre-force limit cycles at
    launch.
    """
    eps = 0.05
    v_switch = 1.0
    if abs(vehicle_velocity) >= v_switch:
        v_ref = max(abs(vehicle_velocity), eps)
    else:
        wv_abs = abs(wheel_velocity)
        if wv_abs > eps:
            v_ref = max(wv_abs, eps)
        else:
            v_ref = max(abs(vehicle_velocity), eps)
    slip = (wheel_velocity - vehicle_velocity) / v_ref
    return float(np.clip(slip, -1.0, 1.0))


class PacejkaTireModel:
    """Pacejka Magic Formula tire model for longitudinal forces.
    
    Implements the simplified Pacejka Magic Formula with load sensitivity,
    suitable for acceleration simulation of FSAE vehicles.
    """
    
    def __init__(
        self,
        config: TireProperties,
        coefficients: Optional[PacejkaCoefficients] = None,
        surface_mu_scaling: float = 1.0
    ):
        """Initialize Pacejka tire model.
        
        Args:
            config: Tire properties configuration
            coefficients: Pacejka coefficients (uses AVON_FSAE defaults if None)
            surface_mu_scaling: Grip multiplier for surface conditions (1.0=dry, ~0.6=wet)
        """
        self.config = config
        self.radius = config.radius_loaded
        self.rolling_resistance_coeff = config.rolling_resistance_coeff
        self.surface_mu_scaling = surface_mu_scaling
        # Memoisation for get_optimal_slip_ratio (see method docstring).
        self._optimal_slip_cache: Dict[int, float] = {}

        # Use provided coefficients or derive from config.
        # Precedence:
        #   1. explicit ``coefficients`` argument
        #   2. advanced-form config fields (pDx1/pDx2/pKx1/pKx2/C/E/Fz0) — the
        #      form used in config/vehicle_configs/*.json
        #   3. legacy quartet (B/C/D/E) converted to the advanced form
        #   4. AVON_FSAE_COEFFICIENTS
        if coefficients is not None:
            self.coef = coefficients
        elif _has_advanced_fields(config):
            self.coef = _coefficients_from_advanced_config(config)
        elif (config.pacejka_B is not None and config.pacejka_C is not None and
              config.pacejka_D is not None and config.pacejka_E is not None):
            # Legacy quartet (B dimensionless, D = mu_peak).
            self.coef = PacejkaCoefficients(
                C=config.pacejka_C,
                pDx1=config.pacejka_D,
                pDx2=-0.12,
                pKx1=config.pacejka_B,
                E=config.pacejka_E,
                pEx1=config.pacejka_E,
                Fz0=1500.0,
            )
        else:
            self.coef = AVON_FSAE_COEFFICIENTS
    
    def calculate_longitudinal_force(
        self,
        normal_force: float,
        slip_ratio: float,
        velocity: float
    ) -> Tuple[float, float]:
        """Calculate longitudinal tire force using Pacejka Magic Formula.
        
        Args:
            normal_force: Normal force on tire (N)
            slip_ratio: Slip ratio (-1 to 1, positive = acceleration)
            velocity: Vehicle velocity (m/s)
            
        Returns:
            Tuple of (longitudinal_force, rolling_resistance_force) in N
        """
        if normal_force <= 0:
            return 0.0, 0.0
        
        # Calculate Pacejka coefficients with load sensitivity
        Fz = normal_force
        Fz0 = self.coef.Fz0
        dfz = (Fz - Fz0) / Fz0  # Normalized load deviation
        
        # Peak value D (with load sensitivity and surface condition)
        mu_peak = (self.coef.pDx1 + self.coef.pDx2 * dfz) * self.surface_mu_scaling
        mu_peak = max(0.1, mu_peak)  # Ensure positive
        D = Fz * mu_peak
        
        # Shape factor C
        C = self.coef.C
        
        # Stiffness factor B (now used directly as dimensionless factor)
        # pKx1 is the B factor at nominal load, with optional load variation
        B = self.coef.pKx1 + self.coef.pKx2 * dfz + self.coef.pKx3 * dfz**2
        B = max(1.0, B)  # Ensure positive and reasonable
        
        # Curvature factor E
        E = (self.coef.pEx1 + self.coef.pEx2 * dfz + self.coef.pEx3 * dfz**2) * \
            (1.0 - self.coef.pEx4 * np.sign(slip_ratio))
        E = np.clip(E, -2.0, 1.0)  # Stability limit
        
        # Horizontal shift
        Sh = self.coef.pHx1 + self.coef.pHx2 * dfz
        
        # Vertical shift
        Sv = Fz * (self.coef.pVx1 + self.coef.pVx2 * dfz)
        
        # Apply horizontal shift to slip ratio
        kappa = slip_ratio + Sh
        
        # Magic Formula
        Bk = B * kappa
        Fx = D * np.sin(C * np.arctan(Bk - E * (Bk - np.arctan(Bk)))) + Sv
        
        # Rolling resistance
        frr = self.rolling_resistance_coeff * normal_force
        if velocity > 0:
            frr = -abs(frr)
        elif velocity < 0:
            frr = abs(frr)
        else:
            frr = 0.0
        
        return float(Fx), float(frr)
    
    def calculate_slip_ratio(
        self,
        wheel_angular_velocity: float,
        vehicle_velocity: float
    ) -> float:
        """Calculate slip ratio from wheel and vehicle velocities.
        
        Args:
            wheel_angular_velocity: Wheel angular velocity (rad/s)
            vehicle_velocity: Vehicle velocity (m/s)
            
        Returns:
            Slip ratio
        """
        wheel_velocity = wheel_angular_velocity * self.radius
        return longitudinal_slip_ratio(wheel_velocity, vehicle_velocity)
    
    def get_optimal_slip_ratio(self, normal_force: float = None) -> float:
        """Calculate the slip ratio that produces maximum force.

        Uses numerical search to find the true argmax of the Magic Formula,
        which accounts for the curvature factor E. The analytical approximation
        kappa_opt ~= tan(pi/(2C))/B is only valid when E = 0.

        The solver calls this once per fixed-point iteration per RK4 substep,
        which can be 20+ times per simulated timestep; the result is cached
        per normal-force bucket (rounded to 5 N) so repeated calls within a
        single step are O(1).

        Args:
            normal_force: Normal force (optional, affects B through load
                sensitivity).

        Returns:
            Optimal slip ratio for maximum traction.
        """
        if normal_force is None:
            normal_force = self.coef.Fz0

        # Round to a 5 N bucket for caching. 5 N is far below the O(1000 N)
        # axle load; the effect on the resulting optimal slip is negligible.
        key = int(round(max(0.0, normal_force) / 5.0))
        cache = self._optimal_slip_cache  # built on first call below
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Search over slip ratios from 1% to 40% on a 60-point grid — this
        # resolves the peak to ~0.7% slip, enough for solver stability.
        fz = key * 5.0
        slip_range = np.linspace(0.01, 0.40, 60)
        best_slip = 0.12
        best_fx = -float("inf")
        for s in slip_range:
            fx = self.calculate_longitudinal_force(fz, s, 10.0)[0]
            if fx > best_fx:
                best_fx = fx
                best_slip = float(s)
        cache[key] = best_slip
        return best_slip
    
    def get_peak_friction_coefficient(self, normal_force: float = None) -> float:
        """Get the peak friction coefficient at given load.
        
        Args:
            normal_force: Normal force (optional)
            
        Returns:
            Peak friction coefficient μ_peak
        """
        if normal_force is None:
            normal_force = self.coef.Fz0
        
        dfz = (normal_force - self.coef.Fz0) / self.coef.Fz0
        mu_peak = (self.coef.pDx1 + self.coef.pDx2 * dfz) * self.surface_mu_scaling
        return max(0.1, mu_peak)


class SimpleTireModel:
    """Simple piecewise-linear tire model (original implementation).
    
    Provides a fallback when Pacejka coefficients are not available.
    """
    
    def __init__(self, config: TireProperties):
        """Initialize simple tire model.
        
        Args:
            config: Tire properties configuration
        """
        self.config = config
        self.radius = config.radius_loaded
        self.mu_max = config.mu_max
        self.mu_slip_optimal = config.mu_slip_optimal
        self.rolling_resistance_coeff = config.rolling_resistance_coeff
    
    def calculate_longitudinal_force(
        self,
        normal_force: float,
        slip_ratio: float,
        velocity: float
    ) -> Tuple[float, float]:
        """Calculate longitudinal tire force and rolling resistance.
        
        Args:
            normal_force: Normal force on tire (N)
            slip_ratio: Slip ratio (0 = no slip, 1 = wheel spinning)
            velocity: Vehicle velocity (m/s)
            
        Returns:
            Tuple of (longitudinal_force, rolling_resistance_force) in N
        """
        mu = self._calculate_friction_coefficient(slip_ratio)
        fx = mu * normal_force
        
        frr = self.rolling_resistance_coeff * normal_force
        if velocity > 0:
            frr = -abs(frr)
        elif velocity < 0:
            frr = abs(frr)
        else:
            frr = 0.0
        
        return fx, frr
    
    def _calculate_friction_coefficient(self, slip_ratio: float) -> float:
        """Calculate friction coefficient as function of slip ratio."""
        slip_ratio = abs(slip_ratio)
        optimal_slip = self.mu_slip_optimal
        
        if slip_ratio <= optimal_slip:
            mu = (self.mu_max / optimal_slip) * slip_ratio
        else:
            mu = self.mu_max * (1.0 - (slip_ratio - optimal_slip) / (1.0 - optimal_slip))
            mu = max(0.0, mu)
        
        return mu
    
    def calculate_slip_ratio(
        self,
        wheel_angular_velocity: float,
        vehicle_velocity: float
    ) -> float:
        """Calculate slip ratio from wheel and vehicle velocities."""
        wheel_velocity = wheel_angular_velocity * self.radius
        return longitudinal_slip_ratio(wheel_velocity, vehicle_velocity)


class TireModel:
    """Tire force model for longitudinal acceleration.
    
    This is a wrapper class that selects between Pacejka and Simple tire models
    based on configuration. It maintains backward compatibility with existing code.
    """
    
    def __init__(
        self,
        config: TireProperties,
        use_pacejka: bool = True,
        pacejka_coefficients: Optional[PacejkaCoefficients] = None,
        surface_mu_scaling: float = 1.0
    ):
        """Initialize tire model.
        
        Args:
            config: Tire properties configuration
            use_pacejka: If True, use Pacejka model; if False, use simple model
            pacejka_coefficients: Optional custom Pacejka coefficients
            surface_mu_scaling: Grip multiplier (1.0=dry, ~0.6=wet)
        """
        self.config = config
        self.radius = config.radius_loaded
        self.use_pacejka = use_pacejka
        self.surface_mu_scaling = surface_mu_scaling

        if use_pacejka:
            self._model = PacejkaTireModel(config, pacejka_coefficients, surface_mu_scaling)
        else:
            self._model = SimpleTireModel(config)

        # Expose legacy attributes for backward compatibility
        self.mu_max = config.mu_max
        self.mu_slip_optimal = config.mu_slip_optimal
        self.rolling_resistance_coeff = config.rolling_resistance_coeff

        # Thermal multiplier cached so repeated calls within a step are O(1).
        self._thermal_enabled = bool(getattr(config, "thermal_model_enabled", False))
        self._thermal_opt = float(getattr(config, "thermal_optimal_temp", 80.0))
        self._thermal_sigma = max(1.0, float(getattr(config, "thermal_sigma", 60.0)))

    def thermal_mu_factor(self, tyre_temp_c: float) -> float:
        """Gaussian grip window around the optimal tyre temperature.

        Returns 1.0 when the thermal model is off, so legacy paths are
        untouched. When enabled, peak grip drops smoothly away from the
        optimal temperature in both directions (cold AND over-heated tyres
        are slower). See Section 3 of the project report.
        """
        if not self._thermal_enabled:
            return 1.0
        z = (tyre_temp_c - self._thermal_opt) / self._thermal_sigma
        return float(np.exp(-0.5 * z * z))
    
    def calculate_longitudinal_force(
        self,
        normal_force: float,
        slip_ratio: float,
        velocity: float,
        tyre_temp_c: Optional[float] = None,
    ) -> Tuple[float, float]:
        """Calculate longitudinal tire force and rolling resistance.

        Args:
            normal_force: Normal force on tire (N)
            slip_ratio: Slip ratio (0 = no slip, 1 = wheel spinning, tire stationary)
            velocity: Vehicle velocity (m/s)
            tyre_temp_c: Tyre carcass temperature (°C). When the thermal
                model is enabled, Fx and peak mu are scaled by a Gaussian
                window around the optimal temperature. ``None`` disables the
                thermal scaling (legacy callers).

        Returns:
            Tuple of (longitudinal_force, rolling_resistance_force) in N
        """
        fx, frr = self._model.calculate_longitudinal_force(normal_force, slip_ratio, velocity)
        if tyre_temp_c is not None and self._thermal_enabled:
            factor = self.thermal_mu_factor(tyre_temp_c)
            fx *= factor
            # Rolling resistance isn't strongly temperature-dependent within
            # the operating window, leave it alone.
        return fx, frr
    
    def calculate_slip_ratio(
        self,
        wheel_angular_velocity: float,
        vehicle_velocity: float
    ) -> float:
        """Calculate slip ratio from wheel and vehicle velocities.
        
        Args:
            wheel_angular_velocity: Wheel angular velocity (rad/s)
            vehicle_velocity: Vehicle velocity (m/s)
            
        Returns:
            Slip ratio
        """
        return self._model.calculate_slip_ratio(wheel_angular_velocity, vehicle_velocity)
    
    def get_optimal_slip_ratio(self, normal_force: float = None) -> float:
        """Get optimal slip ratio for maximum traction.
        
        Args:
            normal_force: Normal force (optional, only used by Pacejka model)
            
        Returns:
            Optimal slip ratio
        """
        if self.use_pacejka and hasattr(self._model, 'get_optimal_slip_ratio'):
            return self._model.get_optimal_slip_ratio(normal_force)
        else:
            return self.mu_slip_optimal
    
    def get_peak_friction_coefficient(self, normal_force: float = None) -> float:
        """Get peak friction coefficient at given load.
        
        Args:
            normal_force: Normal force (optional, only used by Pacejka model)
            
        Returns:
            Peak friction coefficient
        """
        if self.use_pacejka and hasattr(self._model, 'get_peak_friction_coefficient'):
            return self._model.get_peak_friction_coefficient(normal_force)
        else:
            return self.mu_max


