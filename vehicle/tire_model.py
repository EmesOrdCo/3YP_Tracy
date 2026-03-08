"""Tire force model for acceleration simulation.

Implements both a simplified linear tire model and the Pacejka Magic Formula
for more realistic tire behavior. The Pacejka model includes load sensitivity
and is based on Avon FSAE tire data.
"""

import numpy as np
from typing import Tuple, Optional
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
# | pDx2 (load sens.) | -0.12 | Estimated from lateral load sensitivity trend |
# | C (shape factor) | 1.65 | Typical for longitudinal (literature: 1.5-1.9) |
# | pKx1 (slip stiffness) | 35000 N/unit-slip | Literature for FSAE slicks |
# | pKx2 (stiffness/load) | -3000 | Assumed proportional reduction |
# | E (curvature) | 0.1 | Typical value (literature: -0.5 to 0.5) |
# | Fz0 (nominal load) | 1500 N | Assumed typical rear tire load |
#
# Assumptions: longitudinal μ ≈ lateral μ; optimal slip ~12-15%.
# =============================================================================

AVON_FSAE_COEFFICIENTS = PacejkaCoefficients(
    C=1.65,
    pDx1=1.45,
    pDx2=-0.12,
    pKx1=35000.0,  # Slip stiffness in N per unit slip at nominal load
    pKx2=-3000.0,  # Variation with load (N per unit slip per unit dfz)
    pKx3=0.0,
    E=0.1,
    pEx1=0.1,
    pEx2=0.0,
    pEx3=0.0,
    pEx4=0.0,
    pHx1=0.0,
    pHx2=0.0,
    pVx1=0.0,
    pVx2=0.0,
    Fz0=1500.0
)


class PacejkaTireModel:
    """Pacejka Magic Formula tire model for longitudinal forces.
    
    Implements the simplified Pacejka Magic Formula with load sensitivity,
    suitable for acceleration simulation of FSAE vehicles.
    """
    
    def __init__(
        self,
        config: TireProperties,
        coefficients: Optional[PacejkaCoefficients] = None
    ):
        """Initialize Pacejka tire model.
        
        Args:
            config: Tire properties configuration
            coefficients: Pacejka coefficients (uses AVON_FSAE defaults if None)
        """
        self.config = config
        self.radius = config.radius_loaded
        self.rolling_resistance_coeff = config.rolling_resistance_coeff
        
        # Use provided coefficients or defaults
        if coefficients is not None:
            self.coef = coefficients
        elif (config.pacejka_B is not None and config.pacejka_C is not None and
              config.pacejka_D is not None and config.pacejka_E is not None):
            # Use coefficients from config if all are provided
            self.coef = PacejkaCoefficients(
                C=config.pacejka_C,
                pDx1=config.pacejka_D,
                pDx2=-0.12,  # Default load sensitivity
                pKx1=config.pacejka_B * config.pacejka_C * config.pacejka_D,
                E=config.pacejka_E,
                pEx1=config.pacejka_E,
                Fz0=1500.0
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
        
        # Peak value D (with load sensitivity)
        mu_peak = self.coef.pDx1 + self.coef.pDx2 * dfz
        mu_peak = max(0.1, mu_peak)  # Ensure positive
        D = Fz * mu_peak
        
        # Shape factor C
        C = self.coef.C
        
        # Stiffness factor B
        Kx = self.coef.pKx1 + self.coef.pKx2 * dfz + self.coef.pKx3 * dfz**2
        Kx = max(1.0, Kx)  # Ensure positive
        B = Kx / (C * D) if D > 0 else 10.0
        
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
        
        if abs(vehicle_velocity) < 0.1:
            if abs(wheel_velocity) > 0.1:
                return 1.0 if wheel_velocity > 0 else -1.0
            else:
                return 0.0
        
        slip = (wheel_velocity - vehicle_velocity) / abs(vehicle_velocity)
        return np.clip(slip, -1.0, 1.0)
    
    def get_optimal_slip_ratio(self, normal_force: float = None) -> float:
        """Calculate the slip ratio that produces maximum force.
        
        For the Magic Formula with E ≈ 0, the peak occurs at:
        κ_opt ≈ tan(π / (2*C)) / B
        
        For typical values (C ≈ 1.65), this gives κ_opt ≈ 1.5 / B
        
        Args:
            normal_force: Normal force (optional, affects B through load sensitivity)
            
        Returns:
            Optimal slip ratio for maximum traction
        """
        if normal_force is None:
            normal_force = self.coef.Fz0
        
        Fz = normal_force
        Fz0 = self.coef.Fz0
        dfz = (Fz - Fz0) / Fz0
        
        mu_peak = self.coef.pDx1 + self.coef.pDx2 * dfz
        D = Fz * mu_peak
        C = self.coef.C
        Kx = self.coef.pKx1 + self.coef.pKx2 * dfz
        B = Kx / (C * D) if D > 0 else 10.0
        
        # For Magic Formula: peak at x where d/dx[sin(C*arctan(Bx))] = 0
        # This occurs at Bx = tan(π/(2C)), so x = tan(π/(2C)) / B
        kappa_opt = np.tan(np.pi / (2 * C)) / B
        return float(np.clip(kappa_opt, 0.05, 0.25))
    
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
        mu_peak = self.coef.pDx1 + self.coef.pDx2 * dfz
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
        
        if abs(vehicle_velocity) < 0.1:
            if abs(wheel_velocity) > 0.1:
                return 1.0 if wheel_velocity > 0 else -1.0
            else:
                return 0.0
        
        slip = (wheel_velocity - vehicle_velocity) / abs(vehicle_velocity)
        return np.clip(slip, -1.0, 1.0)


class TireModel:
    """Tire force model for longitudinal acceleration.
    
    This is a wrapper class that selects between Pacejka and Simple tire models
    based on configuration. It maintains backward compatibility with existing code.
    """
    
    def __init__(
        self,
        config: TireProperties,
        use_pacejka: bool = True,
        pacejka_coefficients: Optional[PacejkaCoefficients] = None
    ):
        """Initialize tire model.
        
        Args:
            config: Tire properties configuration
            use_pacejka: If True, use Pacejka model; if False, use simple model
            pacejka_coefficients: Optional custom Pacejka coefficients
        """
        self.config = config
        self.radius = config.radius_loaded
        self.use_pacejka = use_pacejka
        
        if use_pacejka:
            self._model = PacejkaTireModel(config, pacejka_coefficients)
        else:
            self._model = SimpleTireModel(config)
        
        # Expose legacy attributes for backward compatibility
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
            slip_ratio: Slip ratio (0 = no slip, 1 = wheel spinning, tire stationary)
            velocity: Vehicle velocity (m/s)
            
        Returns:
            Tuple of (longitudinal_force, rolling_resistance_force) in N
        """
        return self._model.calculate_longitudinal_force(normal_force, slip_ratio, velocity)
    
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


