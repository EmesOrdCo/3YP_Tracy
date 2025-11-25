"""Validation tools for comparing simulation vs test data."""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from pathlib import Path
import pandas as pd
from dataclasses import dataclass

import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..dynamics.state import SimulationState
    from ..simulation.acceleration_sim import SimulationResult
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from dynamics.state import SimulationState
    from simulation.acceleration_sim import SimulationResult


@dataclass
class ValidationData:
    """Test data for validation."""
    time: List[float]
    position: List[float]
    velocity: Optional[List[float]] = None
    acceleration: Optional[List[float]] = None
    power: Optional[List[float]] = None
    
    @classmethod
    def from_csv(cls, file_path: Path, 
                 time_col: str = 'time',
                 position_col: str = 'position',
                 velocity_col: Optional[str] = None,
                 acceleration_col: Optional[str] = None,
                 power_col: Optional[str] = None) -> 'ValidationData':
        """
        Load validation data from CSV file.
        
        Args:
            file_path: Path to CSV file
            time_col: Name of time column
            position_col: Name of position column
            velocity_col: Optional name of velocity column
            acceleration_col: Optional name of acceleration column
            power_col: Optional name of power column
            
        Returns:
            ValidationData object
        """
        df = pd.read_csv(file_path)
        
        return cls(
            time=df[time_col].tolist(),
            position=df[position_col].tolist(),
            velocity=df[velocity_col].tolist() if velocity_col and velocity_col in df.columns else None,
            acceleration=df[acceleration_col].tolist() if acceleration_col and acceleration_col in df.columns else None,
            power=df[power_col].tolist() if power_col and power_col in df.columns else None
        )


@dataclass
class ValidationResult:
    """Result of validation comparison."""
    metric_name: str
    simulated_values: List[float]
    test_values: List[float]
    time_points: List[float]
    mse: float  # Mean Squared Error
    rmse: float  # Root Mean Squared Error
    mae: float  # Mean Absolute Error
    max_error: float
    correlation: float
    

def interpolate_to_common_time(
    time1: List[float],
    values1: List[float],
    time2: List[float]
) -> List[float]:
    """
    Interpolate values from time1 to time2 grid.
    
    Args:
        time1: Original time points
        values1: Original values
        time2: Target time points
        
    Returns:
        Interpolated values at time2 points
    """
    return np.interp(time2, time1, values1).tolist()


def compare_time_series(
    sim_state_history: List[SimulationState],
    test_data: ValidationData,
    metric: str = 'position',
    interpolate: bool = True
) -> ValidationResult:
    """
    Compare simulated time series with test data.
    
    Args:
        sim_state_history: Simulated state history
        test_data: Test data for comparison
        metric: Metric to compare ('position', 'velocity', 'acceleration', 'power')
        interpolate: Whether to interpolate to common time grid
        
    Returns:
        ValidationResult object
    """
    # Extract simulated data
    sim_times = [s.time for s in sim_state_history]
    
    if metric == 'position':
        sim_values = [s.position for s in sim_state_history]
        test_values = test_data.position
        test_times = test_data.time
    elif metric == 'velocity':
        sim_values = [s.velocity for s in sim_state_history]
        test_values = test_data.velocity if test_data.velocity else []
        test_times = test_data.time
    elif metric == 'acceleration':
        sim_values = [s.acceleration for s in sim_state_history]
        test_values = test_data.acceleration if test_data.acceleration else []
        test_times = test_data.time
    elif metric == 'power':
        sim_values = [s.power_consumed for s in sim_state_history]
        test_values = test_data.power if test_data.power else []
        test_times = test_data.time
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    if not test_values or len(test_values) == 0:
        raise ValueError(f"Test data does not contain {metric} values")
    
    # Find common time range
    min_time = max(min(sim_times), min(test_times))
    max_time = min(max(sim_times), max(test_times))
    
    # Filter to common range
    sim_mask = [(t >= min_time and t <= max_time) for t in sim_times]
    test_mask = [(t >= min_time and t <= max_time) for t in test_times]
    
    sim_times_filtered = [t for t, m in zip(sim_times, sim_mask) if m]
    sim_values_filtered = [v for v, m in zip(sim_values, sim_mask) if m]
    test_times_filtered = [t for t, m in zip(test_times, test_mask) if m]
    test_values_filtered = [v for v, m in zip(test_values, test_mask) if m]
    
    if interpolate:
        # Interpolate both to common time grid
        common_times = np.linspace(min_time, max_time, 
                                   min(len(sim_times_filtered), len(test_times_filtered))).tolist()
        sim_values_interp = interpolate_to_common_time(sim_times_filtered, sim_values_filtered, common_times)
        test_values_interp = interpolate_to_common_time(test_times_filtered, test_values_filtered, common_times)
        time_points = common_times
    else:
        # Use intersection of time points (simpler but may have fewer points)
        time_points = sorted(set(sim_times_filtered) & set(test_times_filtered))
        if not time_points:
            raise ValueError("No overlapping time points between simulation and test data")
        
        sim_values_interp = interpolate_to_common_time(sim_times_filtered, sim_values_filtered, time_points)
        test_values_interp = interpolate_to_common_time(test_times_filtered, test_values_filtered, time_points)
    
    # Calculate error metrics
    errors = np.array(sim_values_interp) - np.array(test_values_interp)
    
    mse = np.mean(errors ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(errors))
    max_error = np.max(np.abs(errors))
    
    # Calculate correlation
    if len(sim_values_interp) > 1:
        correlation = np.corrcoef(sim_values_interp, test_values_interp)[0, 1]
    else:
        correlation = 1.0 if sim_values_interp[0] == test_values_interp[0] else 0.0
    
    return ValidationResult(
        metric_name=metric,
        simulated_values=sim_values_interp,
        test_values=test_values_interp,
        time_points=time_points,
        mse=mse,
        rmse=rmse,
        mae=mae,
        max_error=max_error,
        correlation=correlation
    )


def validate_simulation(
    sim_state_history: List[SimulationState],
    test_data: ValidationData,
    metrics: Optional[List[str]] = None
) -> Dict[str, ValidationResult]:
    """
    Validate simulation against test data for multiple metrics.
    
    Args:
        sim_state_history: Simulated state history
        test_data: Test data for comparison
        metrics: List of metrics to compare (default: ['position', 'velocity'])
        
    Returns:
        Dictionary mapping metric names to ValidationResult objects
    """
    if metrics is None:
        metrics = ['position', 'velocity']
    
    results = {}
    
    for metric in metrics:
        try:
            results[metric] = compare_time_series(sim_state_history, test_data, metric)
        except (ValueError, KeyError) as e:
            print(f"Warning: Could not validate {metric}: {e}")
    
    return results


def validation_summary(
    validation_results: Dict[str, ValidationResult]
) -> pd.DataFrame:
    """
    Create summary table of validation results.
    
    Args:
        validation_results: Dictionary of validation results
        
    Returns:
        DataFrame with validation metrics
    """
    data = {
        'Metric': [],
        'RMSE': [],
        'MAE': [],
        'Max Error': [],
        'Correlation': []
    }
    
    for metric_name, result in validation_results.items():
        data['Metric'].append(metric_name)
        data['RMSE'].append(result.rmse)
        data['MAE'].append(result.mae)
        data['Max Error'].append(result.max_error)
        data['Correlation'].append(result.correlation)
    
    return pd.DataFrame(data)


def plot_validation(
    validation_result: ValidationResult,
    ax=None,
    show_errors: bool = True
):
    """
    Plot validation comparison.
    
    Args:
        validation_result: Validation result to plot
        ax: Optional matplotlib axes
        show_errors: Whether to show error bars/region
        
    Returns:
        Matplotlib axes object
    """
    import matplotlib.pyplot as plt
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(validation_result.time_points, validation_result.simulated_values,
            label='Simulation', linewidth=2, marker='o', markersize=3)
    ax.plot(validation_result.time_points, validation_result.test_values,
            label='Test Data', linewidth=2, marker='s', markersize=3)
    
    if show_errors:
        errors = np.array(validation_result.simulated_values) - np.array(validation_result.test_values)
        ax.fill_between(validation_result.time_points, 
                        np.array(validation_result.test_values) - np.abs(errors),
                        np.array(validation_result.test_values) + np.abs(errors),
                        alpha=0.2, label='Error')
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel(validation_result.metric_name.capitalize())
    ax.set_title(f'Validation: {validation_result.metric_name.capitalize()} '
                 f'(RMSE={validation_result.rmse:.3f}, R={validation_result.correlation:.3f})')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    return ax


def compare_final_results(
    sim_result: SimulationResult,
    test_final_time: Optional[float] = None,
    test_final_distance: Optional[float] = None,
    test_final_velocity: Optional[float] = None,
    tolerance: float = 0.05  # 5% tolerance
) -> Dict[str, Tuple[bool, float, float]]:
    """
    Compare final simulation results with test data.
    
    Args:
        sim_result: Simulation result
        test_final_time: Test final time (s)
        test_final_distance: Test final distance (m)
        test_final_velocity: Test final velocity (m/s)
        tolerance: Relative tolerance for comparison
        
    Returns:
        Dictionary mapping metric names to (match, simulated_value, test_value) tuples
    """
    comparisons = {}
    
    if test_final_time is not None:
        error = abs(sim_result.final_time - test_final_time) / test_final_time
        comparisons['final_time'] = (error <= tolerance, sim_result.final_time, test_final_time)
    
    if test_final_distance is not None:
        error = abs(sim_result.final_distance - test_final_distance) / test_final_distance
        comparisons['final_distance'] = (error <= tolerance, sim_result.final_distance, test_final_distance)
    
    if test_final_velocity is not None:
        error = abs(sim_result.final_velocity - test_final_velocity) / test_final_velocity
        comparisons['final_velocity'] = (error <= tolerance, sim_result.final_velocity, test_final_velocity)
    
    return comparisons

