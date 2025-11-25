"""Result processing and storage utilities."""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..simulation.acceleration_sim import SimulationResult
    from ..dynamics.state import SimulationState
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from simulation.acceleration_sim import SimulationResult
    from dynamics.state import SimulationState


def extract_time_series_data(
    state_history: List[SimulationState]
) -> Dict[str, List[float]]:
    """
    Extract time series data from state history.
    
    Args:
        state_history: List of simulation states
        
    Returns:
        Dictionary with time series arrays for each state variable
    """
    data = {
        'time': [],
        'position': [],
        'velocity': [],
        'acceleration': [],
        'wheel_speed_front': [],
        'wheel_speed_rear': [],
        'motor_speed': [],
        'motor_current': [],
        'motor_torque': [],
        'drive_force': [],
        'drag_force': [],
        'rolling_resistance': [],
        'normal_force_front': [],
        'normal_force_rear': [],
        'tire_force_front': [],
        'tire_force_rear': [],
        'power_consumed': []
    }
    
    for state in state_history:
        state_dict = state.to_dict()
        for key in data.keys():
            data[key].append(state_dict[key])
    
    return data


def extract_statistics(
    state_history: List[SimulationState]
) -> Dict[str, Dict[str, float]]:
    """
    Extract statistics from state history.
    
    Args:
        state_history: List of simulation states
        
    Returns:
        Dictionary with min, max, mean, and final values for each variable
    """
    data = extract_time_series_data(state_history)
    stats = {}
    
    for key, values in data.items():
        if len(values) == 0:
            continue
        stats[key] = {
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            'final': values[-1] if values else None
        }
    
    return stats


def save_results_to_json(
    result: SimulationResult,
    output_path: Path,
    include_state_history: bool = False,
    state_history: Optional[List[SimulationState]] = None
) -> None:
    """
    Save simulation result to JSON file.
    
    Args:
        result: Simulation result to save
        output_path: Path to output JSON file
        include_state_history: Whether to include full state history
        state_history: Optional state history (required if include_state_history=True)
    """
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'result': result.to_dict(),
        'final_state': result.final_state.to_dict()
    }
    
    if include_state_history:
        if state_history is None:
            raise ValueError("state_history required when include_state_history=True")
        output_data['state_history'] = [s.to_dict() for s in state_history]
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)


def save_results_to_csv(
    result: SimulationResult,
    output_path: Path,
    state_history: Optional[List[SimulationState]] = None
) -> None:
    """
    Save simulation results to CSV files.
    
    Creates two files:
    - {output_path}_summary.csv: Summary of result
    - {output_path}_history.csv: Full state history (if provided)
    
    Args:
        result: Simulation result to save
        output_path: Base path for output files
        state_history: Optional state history to save
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save summary
    summary_path = output_path.parent / f"{output_path.stem}_summary.csv"
    summary_data = {
        'parameter': [],
        'value': []
    }
    
    result_dict = result.to_dict()
    for key, value in result_dict.items():
        summary_data['parameter'].append(key)
        if isinstance(value, bool):
            summary_data['value'].append(str(value))
        elif value is None:
            summary_data['value'].append('')
        else:
            summary_data['value'].append(str(value))
    
    pd.DataFrame(summary_data).to_csv(summary_path, index=False)
    
    # Save state history if provided
    if state_history:
        history_path = output_path.parent / f"{output_path.stem}_history.csv"
        data = extract_time_series_data(state_history)
        pd.DataFrame(data).to_csv(history_path, index=False)


def load_results_from_json(file_path: Path) -> Dict[str, Any]:
    """
    Load simulation results from JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary containing loaded results
    """
    with open(file_path, 'r') as f:
        return json.load(f)


def compare_results(
    results: List[SimulationResult],
    labels: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Compare multiple simulation results side by side.
    
    Args:
        results: List of simulation results to compare
        labels: Optional list of labels for each result
        
    Returns:
        DataFrame with comparison of key metrics
    """
    if labels is None:
        labels = [f"Run {i+1}" for i in range(len(results))]
    
    comparison_data = {
        'Label': labels,
        'Final Time (s)': [r.final_time for r in results],
        'Final Distance (m)': [r.final_distance for r in results],
        'Final Velocity (m/s)': [r.final_velocity for r in results],
        'Max Power (kW)': [r.max_power_used / 1000 for r in results],
        'Power Compliant': [r.power_compliant for r in results],
        'Time Compliant': [r.time_compliant for r in results],
        'Overall Compliant': [r.compliant for r in results],
        'Score': [r.score if r.score is not None else 0.0 for r in results]
    }
    
    return pd.DataFrame(comparison_data)


def calculate_performance_metrics(
    state_history: List[SimulationState],
    target_distance: float = 75.0
) -> Dict[str, float]:
    """
    Calculate additional performance metrics from state history.
    
    Args:
        state_history: List of simulation states
        target_distance: Target distance (m)
        
    Returns:
        Dictionary of performance metrics
    """
    if not state_history:
        return {}
    
    # Find states at key distances
    distances_25m = None
    distances_50m = None
    
    for state in state_history:
        if distances_25m is None and state.position >= 25.0:
            distances_25m = state
        if distances_50m is None and state.position >= 50.0:
            distances_50m = state
    
    final_state = state_history[-1]
    
    metrics = {
        'time_to_25m': distances_25m.time if distances_25m else None,
        'time_to_50m': distances_50m.time if distances_50m else None,
        'time_to_finish': final_state.time,
        'velocity_at_25m': distances_25m.velocity if distances_25m else None,
        'velocity_at_50m': distances_50m.velocity if distances_50m else None,
        'final_velocity': final_state.velocity,
        'max_acceleration': max(s.acceleration for s in state_history),
        'max_velocity': max(s.velocity for s in state_history),
        'max_power': max(abs(s.power_consumed) for s in state_history),
        'distance_traveled': final_state.position
    }
    
    # Calculate average acceleration
    velocities = [s.velocity for s in state_history]
    times = [s.time for s in state_history]
    if len(velocities) > 1 and times[-1] > 0:
        metrics['average_acceleration'] = velocities[-1] / times[-1]
    else:
        metrics['average_acceleration'] = 0.0
    
    return metrics

