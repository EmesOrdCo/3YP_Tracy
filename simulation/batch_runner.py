"""Batch simulation runner for parameter sweeps."""

from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import copy
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing

import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import VehicleConfig
    from ..simulation.acceleration_sim import AccelerationSimulation, SimulationResult
    from ..analysis.results import compare_results, save_results_to_csv
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import VehicleConfig
    from simulation.acceleration_sim import AccelerationSimulation, SimulationResult
    from analysis.results import compare_results, save_results_to_csv


class BatchRunner:
    """Run multiple simulations with different configurations."""
    
    def __init__(self, base_config: VehicleConfig, parallel: bool = True, n_workers: Optional[int] = None):
        """
        Initialize batch runner.
        
        Args:
            base_config: Base vehicle configuration
            parallel: Whether to run simulations in parallel
            n_workers: Number of parallel workers (None = auto)
        """
        self.base_config = base_config
        self.parallel = parallel
        self.n_workers = n_workers or multiprocessing.cpu_count()
    
    def run_single_simulation(self, config: VehicleConfig, fastest_time: Optional[float] = None) -> SimulationResult:
        """
        Run a single simulation.
        
        Args:
            config: Vehicle configuration
            fastest_time: Optional fastest time for scoring
            
        Returns:
            Simulation result
        """
        sim = AccelerationSimulation(config)
        return sim.run(fastest_time=fastest_time)
    
    def parameter_sweep(
        self,
        parameter_path: str,
        values: List[float],
        fastest_time: Optional[float] = None
    ) -> List[SimulationResult]:
        """
        Run parameter sweep for a single parameter.
        
        Args:
            parameter_path: Path to parameter (e.g., 'mass.total_mass')
            values: List of values to test
            fastest_time: Optional fastest time for scoring
            
        Returns:
            List of simulation results
        """
        configs = []
        for value in values:
            config = self._set_parameter(self.base_config, parameter_path, value)
            configs.append(config)
        
        return self.run_batch(configs, fastest_time=fastest_time)
    
    def multi_parameter_sweep(
        self,
        parameters: Dict[str, List[float]],
        fastest_time: Optional[float] = None
    ) -> List[SimulationResult]:
        """
        Run multi-parameter sweep (full factorial).
        
        Args:
            parameters: Dictionary mapping parameter paths to value lists
            fastest_time: Optional fastest time for scoring
            
        Returns:
            List of simulation results
        """
        import itertools
        
        # Generate all combinations
        param_names = list(parameters.keys())
        param_values = list(parameters.values())
        combinations = list(itertools.product(*param_values))
        
        configs = []
        for combo in combinations:
            config = copy.deepcopy(self.base_config)
            for param_name, value in zip(param_names, combo):
                config = self._set_parameter(config, param_name, value)
            configs.append(config)
        
        return self.run_batch(configs, fastest_time=fastest_time)
    
    def run_batch(
        self,
        configs: List[VehicleConfig],
        fastest_time: Optional[float] = None,
        labels: Optional[List[str]] = None
    ) -> List[SimulationResult]:
        """
        Run batch of simulations.
        
        Args:
            configs: List of vehicle configurations
            fastest_time: Optional fastest time for scoring
            labels: Optional labels for each simulation
            
        Returns:
            List of simulation results
        """
        if labels is None:
            labels = [f"Sim_{i+1}" for i in range(len(configs))]
        
        if self.parallel and len(configs) > 1:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
                futures = [
                    executor.submit(self.run_single_simulation, config, fastest_time)
                    for config in configs
                ]
                results = [f.result() for f in futures]
        else:
            # Sequential execution
            results = [
                self.run_single_simulation(config, fastest_time)
                for config in configs
            ]
        
        return results
    
    def save_batch_results(
        self,
        results: List[SimulationResult],
        labels: List[str],
        output_dir: Path
    ):
        """
        Save batch results to CSV.
        
        Args:
            results: List of simulation results
            labels: Labels for each result
            output_dir: Output directory
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create comparison DataFrame
        comparison_df = compare_results(results, labels)
        comparison_df.to_csv(output_dir / "batch_comparison.csv", index=False)
        
        print(f"Batch results saved to {output_dir}")
        print(f"\nSummary:")
        print(comparison_df.to_string(index=False))
    
    def _set_parameter(self, config: VehicleConfig, parameter_path: str, value: float) -> VehicleConfig:
        """
        Create a new config with modified parameter.
        
        Args:
            config: Base configuration
            parameter_path: Dot-separated path to parameter
            value: New value for parameter
            
        Returns:
            New VehicleConfig with modified parameter
        """
        new_config = copy.deepcopy(config)
        parts = parameter_path.split('.')
        
        if len(parts) == 2:
            category, param = parts
            
            if category == 'mass':
                setattr(new_config.mass, param, value)
            elif category == 'tires':
                setattr(new_config.tires, param, value)
            elif category == 'powertrain':
                setattr(new_config.powertrain, param, value)
            elif category == 'aerodynamics':
                setattr(new_config.aerodynamics, param, value)
            elif category == 'suspension':
                setattr(new_config.suspension, param, value)
            elif category == 'control':
                setattr(new_config.control, param, value)
            elif category == 'environment':
                setattr(new_config.environment, param, value)
            else:
                raise ValueError(f"Unknown category: {category}")
        else:
            raise ValueError(f"Parameter path must have format 'category.parameter', got: {parameter_path}")
        
        return new_config

