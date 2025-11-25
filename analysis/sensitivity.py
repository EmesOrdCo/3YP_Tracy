"""Parameter sensitivity analysis tools."""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass
import pandas as pd

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


@dataclass
class SensitivityResult:
    """Result of sensitivity analysis for a single parameter."""
    parameter_name: str
    base_value: float
    varied_values: List[float]
    results: List[SimulationResult]
    output_metric: str  # e.g., 'final_time', 'score', 'final_velocity'
    metric_values: List[float]
    sensitivity_coefficient: float  # % change in output per % change in input
    

def parameter_sweep(
    base_config: VehicleConfig,
    parameter_path: str,
    values: List[float],
    fastest_time: Optional[float] = None
) -> SensitivityResult:
    """
    Perform a parameter sweep for a single parameter.
    
    Args:
        base_config: Base vehicle configuration
        parameter_path: Path to parameter to vary (e.g., 'mass.total_mass')
        values: List of values to test
        fastest_time: Optional fastest time for scoring
        
    Returns:
        SensitivityResult object
    """
    results = []
    
    for value in values:
        # Create modified config
        config = _set_parameter(base_config, parameter_path, value)
        
        # Run simulation
        sim = AccelerationSimulation(config)
        result = sim.run(fastest_time=fastest_time)
        results.append(result)
    
    # Extract output metric (default to final_time)
    metric_values = [r.final_time for r in results]
    
    # Calculate sensitivity coefficient
    base_idx = len(values) // 2  # Use middle value as base
    base_metric = metric_values[base_idx]
    base_param_value = values[base_idx]
    
    if base_metric > 0 and base_param_value > 0:
        # Calculate average sensitivity
        sensitivities = []
        for i in range(len(values)):
            if i != base_idx and values[i] > 0 and metric_values[i] > 0:
                param_change = (values[i] - base_param_value) / base_param_value
                metric_change = (metric_values[i] - base_metric) / base_metric
                if param_change != 0:
                    sensitivities.append(metric_change / param_change)
        
        sensitivity_coefficient = np.mean(sensitivities) if sensitivities else 0.0
    else:
        sensitivity_coefficient = 0.0
    
    return SensitivityResult(
        parameter_name=parameter_path,
        base_value=base_param_value,
        varied_values=values,
        results=results,
        output_metric='final_time',
        metric_values=metric_values,
        sensitivity_coefficient=sensitivity_coefficient
    )


def multi_parameter_sensitivity(
    base_config: VehicleConfig,
    parameters: Dict[str, List[float]],
    fastest_time: Optional[float] = None,
    output_metric: str = 'final_time'
) -> Dict[str, SensitivityResult]:
    """
    Perform sensitivity analysis for multiple parameters.
    
    Args:
        base_config: Base vehicle configuration
        parameters: Dictionary mapping parameter paths to value lists
        fastest_time: Optional fastest time for scoring
        output_metric: Metric to analyze ('final_time', 'score', 'final_velocity', etc.)
        
    Returns:
        Dictionary mapping parameter names to SensitivityResult objects
    """
    results = {}
    
    for param_path, values in parameters.items():
        results[param_path] = parameter_sweep(
            base_config, param_path, values, fastest_time
        )
        # Update output metric
        if output_metric == 'final_time':
            results[param_path].metric_values = [r.final_time for r in results[param_path].results]
        elif output_metric == 'score':
            results[param_path].metric_values = [
                r.score if r.score is not None else 0.0 
                for r in results[param_path].results
            ]
        elif output_metric == 'final_velocity':
            results[param_path].metric_values = [r.final_velocity for r in results[param_path].results]
        else:
            raise ValueError(f"Unknown output_metric: {output_metric}")
        
        results[param_path].output_metric = output_metric
    
    return results


def sensitivity_to_dataframe(
    sensitivity_results: Dict[str, SensitivityResult]
) -> pd.DataFrame:
    """
    Convert sensitivity results to pandas DataFrame.
    
    Args:
        sensitivity_results: Dictionary of sensitivity results
        
    Returns:
        DataFrame with parameter sensitivities
    """
    data = {
        'Parameter': [],
        'Base Value': [],
        'Sensitivity Coefficient': [],
        'Output Metric': [],
        'Min Metric': [],
        'Max Metric': [],
        'Metric Range': []
    }
    
    for param_name, result in sensitivity_results.items():
        data['Parameter'].append(param_name)
        data['Base Value'].append(result.base_value)
        data['Sensitivity Coefficient'].append(result.sensitivity_coefficient)
        data['Output Metric'].append(result.output_metric)
        data['Min Metric'].append(min(result.metric_values))
        data['Max Metric'].append(max(result.metric_values))
        data['Metric Range'].append(max(result.metric_values) - min(result.metric_values))
    
    return pd.DataFrame(data)


def rank_sensitivities(
    sensitivity_results: Dict[str, SensitivityResult],
    output_metric: str = 'final_time'
) -> pd.DataFrame:
    """
    Rank parameters by their sensitivity.
    
    Args:
        sensitivity_results: Dictionary of sensitivity results
        output_metric: Metric to rank by
        
    Returns:
        DataFrame sorted by absolute sensitivity coefficient
    """
    df = sensitivity_to_dataframe(sensitivity_results)
    
    # Filter by output metric
    df = df[df['Output Metric'] == output_metric].copy()
    
    # Rank by absolute sensitivity
    df['Abs Sensitivity'] = df['Sensitivity Coefficient'].abs()
    df = df.sort_values('Abs Sensitivity', ascending=False)
    df['Rank'] = range(1, len(df) + 1)
    
    return df[['Rank', 'Parameter', 'Sensitivity Coefficient', 'Metric Range']]


def _set_parameter(config: VehicleConfig, parameter_path: str, value: float) -> VehicleConfig:
    """
    Create a new config with modified parameter.
    
    Args:
        config: Base configuration
        parameter_path: Dot-separated path to parameter (e.g., 'mass.total_mass')
        value: New value for parameter
        
    Returns:
        New VehicleConfig with modified parameter
    """
    import copy
    from ..config.vehicle_config import (
        MassProperties, TireProperties, PowertrainProperties,
        AerodynamicsProperties, SuspensionProperties, ControlProperties,
        EnvironmentProperties, VehicleConfig
    )
    
    # Deep copy config
    new_config = copy.deepcopy(config)
    
    # Parse parameter path
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


def one_at_a_time_sensitivity(
    base_config: VehicleConfig,
    parameter_ranges: Dict[str, Tuple[float, float]],
    n_points: int = 5,
    fastest_time: Optional[float] = None,
    output_metric: str = 'final_time'
) -> Dict[str, SensitivityResult]:
    """
    Perform one-at-a-time sensitivity analysis.
    
    Varies each parameter individually over a range.
    
    Args:
        base_config: Base vehicle configuration
        parameter_ranges: Dictionary mapping parameter paths to (min, max) tuples
        n_points: Number of points to test per parameter
        fastest_time: Optional fastest time for scoring
        output_metric: Metric to analyze
        
    Returns:
        Dictionary mapping parameter names to SensitivityResult objects
    """
    parameters = {}
    
    for param_path, (min_val, max_val) in parameter_ranges.items():
        values = np.linspace(min_val, max_val, n_points).tolist()
        parameters[param_path] = values
    
    return multi_parameter_sensitivity(
        base_config, parameters, fastest_time, output_metric
    )


def plot_sensitivity(
    sensitivity_result: SensitivityResult,
    ax=None
):
    """
    Plot sensitivity result.
    
    Args:
        sensitivity_result: Sensitivity result to plot
        ax: Optional matplotlib axes
        
    Returns:
        Matplotlib axes object
    """
    import matplotlib.pyplot as plt
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    
    ax.plot(sensitivity_result.varied_values, sensitivity_result.metric_values, 
            marker='o', linewidth=2)
    ax.axvline(sensitivity_result.base_value, color='r', linestyle='--', 
               alpha=0.5, label='Base Value')
    ax.set_xlabel(sensitivity_result.parameter_name)
    ax.set_ylabel(sensitivity_result.output_metric)
    ax.set_title(f'Sensitivity: {sensitivity_result.parameter_name}')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    return ax

