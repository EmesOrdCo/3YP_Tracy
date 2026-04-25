#!/usr/bin/env python3
"""
Weight Sensitivity Analysis for Formula Student Acceleration.

This script varies the vehicle weight from 150kg to 250kg in 10kg increments
and plots the effect on 75m acceleration finishing time using supercapacitors.
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Add package root to path
package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver


def run_simulation_with_mass(mass_kg: float) -> dict:
    """
    Run acceleration simulation with specified vehicle mass using supercapacitors.
    
    Args:
        mass_kg: Total vehicle mass in kg
        
    Returns:
        Dictionary with simulation results
    """
    # Load supercapacitor configuration
    config_path = package_root / "config" / "vehicle_configs" / "supercapacitor_vehicle.json"
    config = load_config(config_path)
    
    # Override the total mass
    config.mass.total_mass = mass_kg
    
    # Create solver and run
    solver = DynamicsSolver(config)
    final_state = solver.solve()
    
    return {
        'mass': mass_kg,
        'final_time': final_state.time,
        'final_velocity': final_state.velocity,
        'final_position': final_state.position
    }


def main():
    """Run weight sensitivity analysis."""
    print("="*60)
    print("WEIGHT SENSITIVITY ANALYSIS - Supercapacitor Configuration")
    print("="*60)
    print("\nVarying vehicle mass from 150kg to 250kg in 10kg increments...")
    print("-"*60)
    
    # Define mass range
    masses = np.arange(150, 260, 10)  # 150, 160, ..., 250 kg
    
    # Run simulations
    results = []
    for mass in masses:
        print(f"Running simulation with mass = {mass:.0f} kg...", end=" ")
        result = run_simulation_with_mass(mass)
        results.append(result)
        print(f"Time: {result['final_time']:.4f}s, Final velocity: {result['final_velocity']*3.6:.1f} km/h")
    
    # Extract data for plotting
    masses_arr = np.array([r['mass'] for r in results])
    times_arr = np.array([r['final_time'] for r in results])
    velocities_arr = np.array([r['final_velocity'] * 3.6 for r in results])  # Convert to km/h
    
    # Print summary table
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"{'Mass (kg)':<15} {'Time (s)':<15} {'Final Velocity (km/h)':<20}")
    print("-"*60)
    for r in results:
        print(f"{r['mass']:<15.0f} {r['final_time']:<15.4f} {r['final_velocity']*3.6:<20.1f}")
    
    # Calculate sensitivity
    time_range = times_arr.max() - times_arr.min()
    mass_range = masses_arr.max() - masses_arr.min()
    avg_sensitivity = time_range / mass_range * 10  # seconds per 10kg
    
    print("\n" + "-"*60)
    print(f"Lightest (150kg): {times_arr[0]:.4f}s")
    print(f"Heaviest (250kg): {times_arr[-1]:.4f}s")
    print(f"Time difference: {time_range*1000:.1f} ms")
    print(f"Average sensitivity: {avg_sensitivity*1000:.1f} ms per 10kg")
    print("="*60)
    
    # Create plot
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Primary axis: Finishing time
    color1 = 'tab:blue'
    ax1.set_xlabel('Vehicle Mass (kg)', fontsize=12)
    ax1.set_ylabel('75m Finishing Time (s)', color=color1, fontsize=12)
    line1 = ax1.plot(masses_arr, times_arr, 'o-', color=color1, linewidth=2, 
                     markersize=8, label='Finishing Time')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3)
    
    # Secondary axis: Final velocity
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Final Velocity (km/h)', color=color2, fontsize=12)
    line2 = ax2.plot(masses_arr, velocities_arr, 's--', color=color2, linewidth=2,
                     markersize=6, label='Final Velocity')
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Combined legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='center right', fontsize=10)
    
    # Title and annotations
    plt.title('Effect of Vehicle Mass on 75m Acceleration Performance\n(Supercapacitor Energy Storage)', 
              fontsize=14, fontweight='bold')
    
    # Add annotation for sensitivity
    ax1.annotate(f'Sensitivity: {avg_sensitivity*1000:.1f} ms per 10kg',
                xy=(0.02, 0.98), xycoords='axes fraction',
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Save figure
    save_path = package_root / 'figures' / 'weight_sensitivity_supercap.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {save_path}")
    
    plt.close()


if __name__ == '__main__':
    main()
