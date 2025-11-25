"""Design optimization wrapper for vehicle parameters."""

from typing import Dict, List, Tuple, Optional, Callable
import numpy as np
from scipy.optimize import minimize, differential_evolution
import copy

import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import VehicleConfig
    from ..simulation.acceleration_sim import AccelerationSimulation, SimulationResult
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import VehicleConfig
    from simulation.acceleration_sim import AccelerationSimulation, SimulationResult


class VehicleOptimizer:
    """Optimize vehicle parameters for best performance."""
    
    def __init__(self, base_config: VehicleConfig):
        """
        Initialize optimizer.
        
        Args:
            base_config: Base vehicle configuration
        """
        self.base_config = base_config
    
    def optimize(
        self,
        parameter_bounds: Dict[str, Tuple[float, float]],
        objective: str = 'minimize_time',
        fastest_time: Optional[float] = None,
        method: str = 'differential_evolution',
        **kwargs
    ) -> Tuple[VehicleConfig, SimulationResult, Dict]:
        """
        Optimize vehicle parameters.
        
        Args:
            parameter_bounds: Dictionary mapping parameter paths to (min, max) bounds
            objective: Objective function ('minimize_time', 'maximize_score')
            fastest_time: Optional fastest time for scoring
            method: Optimization method ('differential_evolution', 'minimize')
            **kwargs: Additional arguments for optimizer
            
        Returns:
            Tuple of (optimized_config, best_result, optimization_info)
        """
        param_names = list(parameter_bounds.keys())
        bounds = [parameter_bounds[name] for name in param_names]
        
        # Create objective function
        def objective_func(x):
            config = self._vector_to_config(x, param_names)
            result = self._evaluate_config(config, fastest_time)
            
            if objective == 'minimize_time':
                return result.final_time
            elif objective == 'maximize_score':
                return -result.score if result.score else 1e6  # Negate for minimization
            else:
                raise ValueError(f"Unknown objective: {objective}")
        
        # Run optimization
        if method == 'differential_evolution':
            result = differential_evolution(
                objective_func,
                bounds,
                **kwargs
            )
        elif method == 'minimize':
            # Use center of bounds as initial guess
            x0 = [0.5 * (b[0] + b[1]) for b in bounds]
            result = minimize(
                objective_func,
                x0,
                bounds=bounds,
                **kwargs
            )
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Create optimized config
        optimized_config = self._vector_to_config(result.x, param_names)
        
        # Evaluate final result
        final_result = self._evaluate_config(optimized_config, fastest_time)
        
        info = {
            'success': result.success,
            'message': result.message,
            'fun': result.fun,
            'nit': getattr(result, 'nit', None),
            'nfev': getattr(result, 'nfev', None)
        }
        
        return optimized_config, final_result, info
    
    def _evaluate_config(self, config: VehicleConfig, fastest_time: Optional[float]) -> SimulationResult:
        """
        Evaluate a configuration by running simulation.
        
        Args:
            config: Vehicle configuration
            fastest_time: Optional fastest time for scoring
            
        Returns:
            Simulation result
        """
        sim = AccelerationSimulation(config)
        return sim.run(fastest_time=fastest_time)
    
    def _vector_to_config(self, x: np.ndarray, param_names: List[str]) -> VehicleConfig:
        """
        Convert parameter vector to configuration.
        
        Args:
            x: Parameter vector
            param_names: List of parameter names
            
        Returns:
            VehicleConfig object
        """
        config = copy.deepcopy(self.base_config)
        
        for param_name, value in zip(param_names, x):
            config = self._set_parameter(config, param_name, value)
        
        return config
    
    def _set_parameter(self, config: VehicleConfig, parameter_path: str, value: float) -> VehicleConfig:
        """Set a parameter value in config."""
        parts = parameter_path.split('.')
        
        if len(parts) == 2:
            category, param = parts
            
            if category == 'mass':
                setattr(config.mass, param, value)
            elif category == 'tires':
                setattr(config.tires, param, value)
            elif category == 'powertrain':
                setattr(config.powertrain, param, value)
            elif category == 'aerodynamics':
                setattr(config.aerodynamics, param, value)
            elif category == 'suspension':
                setattr(config.suspension, param, value)
            elif category == 'control':
                setattr(config.control, param, value)
            elif category == 'environment':
                setattr(config.environment, param, value)
            else:
                raise ValueError(f"Unknown category: {category}")
        
        return config

