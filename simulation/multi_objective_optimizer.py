"""Multi-objective optimization for vehicle configuration.

This module provides advanced optimization capabilities for finding optimal vehicle
configurations while respecting Formula Student regulations and handling multiple
objectives simultaneously.
"""

from typing import Dict, List, Tuple, Optional, Callable, Any
import numpy as np
from dataclasses import dataclass, field
import copy
import json
from pathlib import Path
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp

from scipy.optimize import differential_evolution, minimize
from scipy.optimize import OptimizeResult
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    # Try relative imports first (when used as installed package)
    from ..config.vehicle_config import VehicleConfig
    from ..simulation.acceleration_sim import AccelerationSimulation, SimulationResult
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import VehicleConfig
    from simulation.acceleration_sim import AccelerationSimulation, SimulationResult


@dataclass
class ParameterBounds:
    """Defines bounds and constraints for a single parameter."""
    name: str  # e.g., "mass.cg_x"
    min_value: float
    max_value: float
    discrete: bool = False  # If True, parameter can only take discrete values
    step: Optional[float] = None  # Step size for discrete parameters
    
    def clip(self, value: float) -> float:
        """Clip value to bounds."""
        value = max(self.min_value, min(self.max_value, value))
        if self.discrete and self.step:
            # Round to nearest step
            value = round(value / self.step) * self.step
        return value


@dataclass
class OptimizationResult:
    """Results from multi-objective optimization."""
    best_config: VehicleConfig
    best_simulation_result: SimulationResult
    all_evaluations: List[Tuple[VehicleConfig, SimulationResult]] = field(default_factory=list)
    optimization_info: Dict[str, Any] = field(default_factory=dict)
    pareto_front: List[Tuple[VehicleConfig, SimulationResult]] = field(default_factory=list)


class MultiObjectiveOptimizer:
    """Advanced optimizer for vehicle configuration with constraint handling."""
    
    def __init__(
        self,
        base_config: VehicleConfig,
        parameter_bounds: Dict[str, Tuple[float, float]],
        objective: str = 'minimize_time',
        fastest_time: Optional[float] = None,
        enforce_rules: bool = True,
        n_workers: Optional[int] = None
    ):
        """
        Initialize multi-objective optimizer.
        
        Args:
            base_config: Base vehicle configuration to start from
            parameter_bounds: Dict mapping parameter paths to (min, max) bounds
                e.g., {"mass.cg_x": (0.8, 1.4), "mass.cg_z": (0.2, 0.4)}
            objective: Objective function
                - 'minimize_time': Minimize 75m time
                - 'maximize_score': Maximize Formula Student score
                - 'minimize_time_with_rules': Minimize time while staying within rules
            fastest_time: Optional fastest time for scoring calculations
            enforce_rules: If True, penalize configurations that violate rules
            n_workers: Number of parallel workers (None = auto-detect)
        """
        self.base_config = base_config
        self.parameter_bounds_dict = parameter_bounds
        self.objective = objective
        self.fastest_time = fastest_time
        self.enforce_rules = enforce_rules
        self.n_workers = n_workers or max(1, mp.cpu_count() - 1)
        
        # Convert bounds dict to ParameterBounds objects
        self.parameter_bounds = {
            name: ParameterBounds(name, bounds[0], bounds[1])
            for name, bounds in parameter_bounds.items()
        }
        
        self.param_names = list(self.parameter_bounds.keys())
        self.all_evaluations: List[Tuple[VehicleConfig, SimulationResult]] = []
        
    def optimize(
        self,
        method: str = 'differential_evolution',
        max_iterations: int = 100,
        population_size: Optional[int] = None,
        verbose: bool = True,
        save_progress: Optional[str] = None,
        **kwargs
    ) -> OptimizationResult:
        """
        Run optimization to find best configuration.
        
        Args:
            method: Optimization method
                - 'differential_evolution': Genetic algorithm (good for global search)
                - 'basin_hopping': Global optimization with local refinement
                - 'particle_swarm': Particle swarm optimization (requires pyswarm)
            max_iterations: Maximum number of iterations
            population_size: Population size for evolutionary algorithms
            verbose: Print progress
            save_progress: Optional path to save progress JSON
            **kwargs: Additional arguments for optimizer
            
        Returns:
            OptimizationResult with best configuration and all evaluations
        """
        bounds_list = [
            (self.parameter_bounds[name].min_value, self.parameter_bounds[name].max_value)
            for name in self.param_names
        ]
        
        if population_size is None:
            population_size = max(10, len(self.param_names) * 5)
        
        if verbose:
            print(f"Starting optimization with {len(self.param_names)} parameters")
            print(f"Method: {method}, Workers: {self.n_workers}")
            print(f"Parameters to optimize: {', '.join(self.param_names)}")
        
        start_time = time.time()
        
        # Track progress
        self._eval_count = 0
        self._best_so_far = float('inf')
        self._last_progress_time = time.time()
        
        # Create objective function with constraint handling
        def objective_func(x: np.ndarray) -> float:
            """Objective function that handles constraints."""
            try:
                config = self._vector_to_config(x)
                
                # Check basic validation
                errors = config.validate()
                if errors and self.enforce_rules:
                    # Return large penalty for invalid configs
                    return 1e6 + len(errors) * 1e5
                
                # Run simulation
                result = self._evaluate_config(config)
                
                # Progress tracking
                self._eval_count += 1
                current_obj = result.final_time
                
                # Print progress every 10 evaluations or every 5 seconds
                current_time = time.time()
                if verbose and (self._eval_count % 10 == 0 or 
                               current_time - self._last_progress_time > 5):
                    import sys
                    print(f"  Progress: {self._eval_count} evaluations, "
                          f"best so far: {self._best_so_far:.3f}s", end='\r', flush=True)
                    self._last_progress_time = current_time
                
                # Add penalty for rule violations
                penalty = 0.0
                if not result.power_compliant and self.enforce_rules:
                    penalty += 1e5  # Large penalty for power violations
                if not result.time_compliant and self.enforce_rules:
                    penalty += 1e4  # Penalty for time violations
                
                # Calculate objective
                if self.objective == 'minimize_time':
                    obj_value = result.final_time + penalty
                elif self.objective == 'maximize_score':
                    if result.score is None:
                        obj_value = 1e6 + penalty
                    else:
                        obj_value = -result.score + penalty  # Negate for minimization
                elif self.objective == 'minimize_time_with_rules':
                    if not result.power_compliant or not result.time_compliant:
                        obj_value = 1e6 + penalty
                    else:
                        obj_value = result.final_time + penalty
                else:
                    obj_value = result.final_time + penalty
                
                # Update best so far
                if obj_value < self._best_so_far:
                    self._best_so_far = obj_value
                
                return obj_value
                    
            except Exception as e:
                if verbose:
                    print(f"\nError evaluating config: {e}")
                return 1e6  # Return large penalty on error
        
        # Run optimization
        if method == 'differential_evolution':
            # Use workers=1 to avoid pickling issues with nested functions
            # The optimization still runs efficiently without multiprocessing
            result = differential_evolution(
                objective_func,
                bounds_list,
                maxiter=max_iterations,
                popsize=population_size,
                workers=1,  # Disable multiprocessing to avoid pickling issues
                updating='deferred',
                atol=1e-3,  # Tolerance for convergence
                **kwargs
            )
        elif method == 'minimize':
            # Use center of bounds as initial guess
            x0 = np.array([0.5 * (b[0] + b[1]) for b in bounds_list])
            result = minimize(
                objective_func,
                x0,
                bounds=bounds_list,
                options={'maxiter': max_iterations},
                **kwargs
            )
        else:
            raise ValueError(f"Unknown method: {method}")
        
        elapsed_time = time.time() - start_time
        
        # Create optimized config
        best_config = self._vector_to_config(result.x)
        
        # Evaluate final result
        best_result = self._evaluate_config(best_config)
        
        if verbose:
            print()  # New line after progress updates
            print(f"\nOptimization complete in {elapsed_time:.1f}s")
            print(f"Total evaluations: {len(self.all_evaluations)}")
            print(f"Best time: {best_result.final_time:.3f}s")
            print(f"Power compliant: {best_result.power_compliant}")
            print(f"Time compliant: {best_result.time_compliant}")
            if best_result.score:
                print(f"Score: {best_result.score:.1f}")
        
        optimization_info = {
            'method': method,
            'success': result.success if hasattr(result, 'success') else True,
            'message': getattr(result, 'message', ''),
            'fun': result.fun,
            'nit': getattr(result, 'nit', None),
            'nfev': getattr(result, 'nfev', len(self.all_evaluations)),
            'elapsed_time': elapsed_time,
            'n_evaluations': len(self.all_evaluations)
        }
        
        opt_result = OptimizationResult(
            best_config=best_config,
            best_simulation_result=best_result,
            all_evaluations=self.all_evaluations.copy(),
            optimization_info=optimization_info
        )
        
        # Save progress if requested
        if save_progress:
            self._save_progress(opt_result, save_progress)
        
        return opt_result
    
    def _evaluate_config(self, config: VehicleConfig) -> SimulationResult:
        """
        Evaluate a configuration by running simulation.
        
        Args:
            config: Vehicle configuration
            
        Returns:
            Simulation result
        """
        sim = AccelerationSimulation(config)
        result = sim.run(fastest_time=self.fastest_time)
        
        # Store evaluation
        self.all_evaluations.append((copy.deepcopy(config), result))
        
        return result
    
    def _vector_to_config(self, x: np.ndarray) -> VehicleConfig:
        """
        Convert parameter vector to configuration.
        
        Args:
            x: Parameter vector
            
        Returns:
            VehicleConfig object
        """
        config = copy.deepcopy(self.base_config)
        
        for param_name, value in zip(self.param_names, x):
            # Clip value to bounds
            bounds = self.parameter_bounds[param_name]
            value = bounds.clip(value)
            config = self._set_parameter(config, param_name, value)
        
        return config
    
    def _set_parameter(self, config: VehicleConfig, parameter_path: str, value: float) -> VehicleConfig:
        """Set a parameter value in config using dot notation."""
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
        else:
            raise ValueError(f"Invalid parameter path format: {parameter_path}")
        
        return config
    
    def _save_progress(self, result: OptimizationResult, filepath: str):
        """Save optimization progress to JSON file."""
        # Note: VehicleConfig objects can't be directly serialized to JSON
        # This saves a summary instead
        progress_data = {
            'optimization_info': result.optimization_info,
            'best_result': {
                'final_time': result.best_simulation_result.final_time,
                'final_distance': result.best_simulation_result.final_distance,
                'final_velocity': result.best_simulation_result.final_velocity,
                'power_compliant': result.best_simulation_result.power_compliant,
                'time_compliant': result.best_simulation_result.time_compliant,
                'score': result.best_simulation_result.score
            },
            'n_evaluations': len(result.all_evaluations),
            'all_times': [r.final_time for _, r in result.all_evaluations]
        }
        
        with open(filepath, 'w') as f:
            json.dump(progress_data, f, indent=2)
        
        print(f"Progress saved to {filepath}")

