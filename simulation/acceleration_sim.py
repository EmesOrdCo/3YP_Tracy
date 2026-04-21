"""Main acceleration simulation runner."""

from typing import Dict, List, Optional
from dataclasses import dataclass
# Import with fallback for both installed and development modes
import sys
from pathlib import Path

def _import_with_fallback():
    """Import modules with fallback for development mode."""
    try:
        # Try relative imports first (when used as installed package)
        from ..config.vehicle_config import VehicleConfig
        from ..config.config_loader import load_config
        from ..dynamics.solver import DynamicsSolver
        from ..dynamics.state import SimulationState
        from ..rules.power_limit import check_power_limit
        from ..rules.time_limits import check_time_limit
        from ..rules.scoring import calculate_acceleration_score
        from ..rules.wheelie_check import check_wheelie
        return (
            VehicleConfig, load_config, DynamicsSolver, SimulationState,
            check_power_limit, check_time_limit, calculate_acceleration_score, check_wheelie
        )
    except (ImportError, ValueError):
        # Fall back to absolute imports (development mode)
        # Add package root to path if needed
        package_root = Path(__file__).parent.parent.parent.resolve()
        if str(package_root) not in sys.path:
            sys.path.insert(0, str(package_root))
        
        from config.vehicle_config import VehicleConfig
        from config.config_loader import load_config
        from dynamics.solver import DynamicsSolver
        from dynamics.state import SimulationState
        from rules.power_limit import check_power_limit
        from rules.time_limits import check_time_limit
        from rules.scoring import calculate_acceleration_score
        from rules.wheelie_check import check_wheelie
        return (
            VehicleConfig, load_config, DynamicsSolver, SimulationState,
            check_power_limit, check_time_limit, calculate_acceleration_score, check_wheelie
        )

# Import all dependencies
(VehicleConfig, load_config, DynamicsSolver, SimulationState,
 check_power_limit, check_time_limit, calculate_acceleration_score, check_wheelie) = _import_with_fallback()


@dataclass
class SimulationResult:
    """Result of acceleration simulation."""
    final_state: SimulationState
    compliant: bool
    power_compliant: bool
    time_compliant: bool
    max_power_used: float
    final_time: float
    final_distance: float
    final_velocity: float
    score: Optional[float] = None
    fastest_time: Optional[float] = None
    wheelie_detected: bool = False
    min_front_normal_force: float = 0.0
    wheelie_time: float = -1.0
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            'compliant': self.compliant,
            'power_compliant': self.power_compliant,
            'time_compliant': self.time_compliant,
            'max_power_used': self.max_power_used,
            'final_time': self.final_time,
            'final_distance': self.final_distance,
            'final_velocity': self.final_velocity,
            'score': self.score,
            'fastest_time': self.fastest_time,
            'wheelie_detected': self.wheelie_detected,
            'min_front_normal_force': self.min_front_normal_force,
            'wheelie_time': self.wheelie_time
        }


class AccelerationSimulation:
    """Main acceleration simulation class."""
    
    def __init__(self, config: VehicleConfig):
        """
        Initialize acceleration simulation.
        
        Args:
            config: Vehicle configuration
        """
        self.config = config
        self.solver = DynamicsSolver(config)
    
    def run(self, fastest_time: Optional[float] = None) -> SimulationResult:
        """
        Run acceleration simulation.
        
        Args:
            fastest_time: Fastest time in competition (for scoring), optional
            
        Returns:
            SimulationResult object
        """
        # Solve dynamics
        final_state = self.solver.solve()
        
        # Check power limit (EV 2.2)
        power_compliant, max_power, _ = check_power_limit(
            self.solver.state_history,
            self.config.powertrain.max_power_accumulator_outlet
        )
        
        # Check time limit (D 5.3.1)
        time_compliant, final_time = check_time_limit(final_state, max_time=25.0)
        
        # Check for wheelie (front wheel lift-off)
        wheelie_detected, min_front_normal, wheelie_time = check_wheelie(
            self.solver.state_history
        )
        
        # Overall compliance. A wheelie (front Fz -> 0) invalidates the run
        # because it indicates the vehicle lost steering / stability; we also
        # can't trust the longitudinal dynamics in that regime.
        compliant = power_compliant and time_compliant and not wheelie_detected
        
        # Calculate score if fastest time provided
        score = None
        if fastest_time is not None:
            score = calculate_acceleration_score(
                final_state.time,
                fastest_time,
                max_points=75.0  # Default max points for acceleration
            )
        
        # Create result
        result = SimulationResult(
            final_state=final_state,
            compliant=compliant,
            power_compliant=power_compliant,
            time_compliant=time_compliant,
            max_power_used=max_power,
            final_time=final_state.time,
            final_distance=final_state.position,
            final_velocity=final_state.velocity,
            score=score,
            fastest_time=fastest_time,
            wheelie_detected=wheelie_detected,
            min_front_normal_force=min_front_normal,
            wheelie_time=wheelie_time
        )
        
        return result
    
    def get_state_history(self) -> List[SimulationState]:
        """
        Get state history from simulation.
        
        Returns:
            List of simulation states
        """
        return self.solver.state_history


