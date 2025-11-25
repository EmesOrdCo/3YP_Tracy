"""Visualization tools for simulation results."""

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Optional, Dict, Tuple
from pathlib import Path

import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..dynamics.state import SimulationState
    from ..simulation.acceleration_sim import SimulationResult
    from .results import extract_time_series_data, extract_statistics
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from dynamics.state import SimulationState
    from simulation.acceleration_sim import SimulationResult
    from analysis.results import extract_time_series_data, extract_statistics


def plot_velocity_vs_time(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    label: Optional[str] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot velocity vs time.
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes (creates new if None)
        label: Optional label for the plot
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    ax.plot(data['time'], data['velocity'], label=label, **kwargs)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Velocity (m/s)')
    ax.set_title('Velocity vs Time')
    ax.grid(True, alpha=0.3)
    
    if label:
        ax.legend()
    
    return ax


def plot_position_vs_time(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    label: Optional[str] = None,
    target_distance: float = 75.0,
    **kwargs
) -> plt.Axes:
    """
    Plot position vs time.
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes
        label: Optional label for the plot
        target_distance: Target distance to mark
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    ax.plot(data['time'], data['position'], label=label, **kwargs)
    
    # Mark target distance
    if target_distance > 0:
        ax.axhline(y=target_distance, color='r', linestyle='--', 
                   alpha=0.5, label=f'Target: {target_distance}m')
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Position (m)')
    ax.set_title('Position vs Time')
    ax.grid(True, alpha=0.3)
    
    if label:
        ax.legend()
    
    return ax


def plot_acceleration_vs_time(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    label: Optional[str] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot acceleration vs time.
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes
        label: Optional label for the plot
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    ax.plot(data['time'], data['acceleration'], label=label, **kwargs)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Acceleration (m/s²)')
    ax.set_title('Acceleration vs Time')
    ax.grid(True, alpha=0.3)
    
    if label:
        ax.legend()
    
    return ax


def plot_forces_vs_time(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot all forces vs time on one plot.
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    
    ax.plot(data['time'], data['drive_force'], label='Drive Force', **kwargs)
    ax.plot(data['time'], np.abs(data['drag_force']), label='Drag Force', **kwargs)
    ax.plot(data['time'], np.abs(data['rolling_resistance']), 
            label='Rolling Resistance', **kwargs)
    ax.plot(data['time'], data['tire_force_rear'], label='Tire Force (Rear)', 
            linestyle='--', **kwargs)
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Force (N)')
    ax.set_title('Forces vs Time')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    return ax


def plot_power_vs_time(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    power_limit: Optional[float] = None,
    label: Optional[str] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot power consumption vs time.
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes
        power_limit: Optional power limit to mark (W)
        label: Optional label for the plot
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    power_kw = abs(np.array(data['power_consumed'])) / 1000  # Convert to kW
    
    ax.plot(data['time'], power_kw, label=label, **kwargs)
    
    # Mark power limit if provided
    if power_limit is not None:
        limit_kw = power_limit / 1000
        ax.axhline(y=limit_kw, color='r', linestyle='--', 
                   alpha=0.5, label=f'Power Limit: {limit_kw:.1f} kW')
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Power Consumption vs Time')
    ax.grid(True, alpha=0.3)
    
    if label:
        ax.legend()
    
    return ax


def plot_tire_forces_vs_time(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot tire forces vs time.
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    
    ax.plot(data['time'], data['tire_force_front'], label='Front Tire Force', **kwargs)
    ax.plot(data['time'], data['tire_force_rear'], label='Rear Tire Force', **kwargs)
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Tire Force (N)')
    ax.set_title('Tire Forces vs Time')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    return ax


def plot_normal_forces_vs_time(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot normal forces vs time (load transfer visualization).
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    
    ax.plot(data['time'], data['normal_force_front'], label='Front Normal Force', **kwargs)
    ax.plot(data['time'], data['normal_force_rear'], label='Rear Normal Force', **kwargs)
    
    # Calculate total for reference
    total = np.array(data['normal_force_front']) + np.array(data['normal_force_rear'])
    ax.plot(data['time'], total, label='Total Normal Force', 
            linestyle='--', alpha=0.5, **kwargs)
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Normal Force (N)')
    ax.set_title('Normal Forces vs Time (Load Transfer)')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    return ax


def plot_velocity_vs_position(
    state_history: List[SimulationState],
    ax: Optional[plt.Axes] = None,
    label: Optional[str] = None,
    **kwargs
) -> plt.Axes:
    """
    Plot velocity vs position.
    
    Args:
        state_history: List of simulation states
        ax: Optional matplotlib axes
        label: Optional label for the plot
        **kwargs: Additional arguments passed to plt.plot
        
    Returns:
        Matplotlib axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    data = extract_time_series_data(state_history)
    ax.plot(data['position'], data['velocity'], label=label, **kwargs)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Velocity (m/s)')
    ax.set_title('Velocity vs Position')
    ax.grid(True, alpha=0.3)
    
    if label:
        ax.legend()
    
    return ax


def create_comprehensive_plot(
    state_history: List[SimulationState],
    result: Optional[SimulationResult] = None,
    power_limit: Optional[float] = None,
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Create a comprehensive multi-panel plot of simulation results.
    
    Args:
        state_history: List of simulation states
        result: Optional simulation result for title
        power_limit: Optional power limit to mark (W)
        save_path: Optional path to save figure
        
    Returns:
        Matplotlib figure object
    """
    fig = plt.figure(figsize=(16, 10))
    
    # Create subplots
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Position vs Time
    ax1 = fig.add_subplot(gs[0, 0])
    plot_position_vs_time(state_history, ax=ax1)
    
    # Velocity vs Time
    ax2 = fig.add_subplot(gs[0, 1])
    plot_velocity_vs_time(state_history, ax=ax2)
    
    # Acceleration vs Time
    ax3 = fig.add_subplot(gs[0, 2])
    plot_acceleration_vs_time(state_history, ax=ax3)
    
    # Forces vs Time
    ax4 = fig.add_subplot(gs[1, 0])
    plot_forces_vs_time(state_history, ax=ax4)
    
    # Power vs Time
    ax5 = fig.add_subplot(gs[1, 1])
    plot_power_vs_time(state_history, ax=ax5, power_limit=power_limit)
    
    # Tire Forces vs Time
    ax6 = fig.add_subplot(gs[1, 2])
    plot_tire_forces_vs_time(state_history, ax=ax6)
    
    # Normal Forces vs Time
    ax7 = fig.add_subplot(gs[2, 0])
    plot_normal_forces_vs_time(state_history, ax=ax7)
    
    # Velocity vs Position
    ax8 = fig.add_subplot(gs[2, 1])
    plot_velocity_vs_position(state_history, ax=ax8)
    
    # Wheel Speeds vs Time
    ax9 = fig.add_subplot(gs[2, 2])
    data = extract_time_series_data(state_history)
    ax9.plot(data['time'], data['wheel_speed_front'], label='Front Wheel Speed')
    ax9.plot(data['time'], data['wheel_speed_rear'], label='Rear Wheel Speed')
    ax9.set_xlabel('Time (s)')
    ax9.set_ylabel('Wheel Speed (rad/s)')
    ax9.set_title('Wheel Speeds vs Time')
    ax9.grid(True, alpha=0.3)
    ax9.legend()
    
    # Add title with result info if available
    if result:
        title = f"Simulation Results - Time: {result.final_time:.3f}s"
        if result.score is not None:
            title += f", Score: {result.score:.2f} points"
        title += f" - Compliant: {'✓' if result.compliant else '✗'}"
        fig.suptitle(title, fontsize=14, fontweight='bold')
    else:
        fig.suptitle('Simulation Results', fontsize=14, fontweight='bold')
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_comparison(
    state_histories: List[List[SimulationState]],
    labels: List[str],
    plot_type: str = 'velocity',
    save_path: Optional[Path] = None
) -> plt.Figure:
    """
    Plot multiple simulation results for comparison.
    
    Args:
        state_histories: List of state history lists
        labels: Labels for each simulation
        plot_type: Type of plot ('velocity', 'position', 'acceleration', 'power')
        save_path: Optional path to save figure
        
    Returns:
        Matplotlib figure object
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(state_histories)))
    
    for i, (state_history, label) in enumerate(zip(state_histories, labels)):
        if plot_type == 'velocity':
            plot_velocity_vs_time(state_history, ax=ax, label=label, color=colors[i])
        elif plot_type == 'position':
            plot_position_vs_time(state_history, ax=ax, label=label, color=colors[i])
        elif plot_type == 'acceleration':
            plot_acceleration_vs_time(state_history, ax=ax, label=label, color=colors[i])
        elif plot_type == 'power':
            plot_power_vs_time(state_history, ax=ax, label=label, color=colors[i])
        else:
            raise ValueError(f"Unknown plot_type: {plot_type}")
    
    ax.set_title(f'{plot_type.capitalize()} Comparison')
    ax.legend()
    
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig

