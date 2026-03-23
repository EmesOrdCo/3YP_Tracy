#!/usr/bin/env python3
"""
Optimize gear ratio for minimum 75m acceleration time.

This script sweeps through gear ratios to find the optimal balance between:
- Torque multiplication (lower ratio = more wheel torque)
- Top speed (higher ratio = higher top speed before motor max RPM)

The optimal gear ratio depends on:
- Motor characteristics (max torque, max speed)
- Vehicle mass
- Tire grip limits
- 80kW power limit
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from copy import deepcopy

# Add package root to path
package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver


def run_with_gear_ratio(base_config, gear_ratio: float) -> dict:
    """
    Run simulation with a specific gear ratio.
    
    Args:
        base_config: Base vehicle configuration
        gear_ratio: Gear ratio to test
        
    Returns:
        Dictionary with results
    """
    # Create modified config
    config = deepcopy(base_config)
    config.powertrain.gear_ratio = gear_ratio
    
    try:
        solver = DynamicsSolver(config)
        final_state = solver.solve()
        
        # Calculate peak power
        peak_power = max(s.power_consumed for s in solver.state_history) / 1000  # kW
        
        # Calculate max vehicle speed (theoretical)
        motor_max_speed = config.powertrain.motor_max_speed
        wheel_radius = config.tires.radius_loaded
        max_vehicle_speed = motor_max_speed / gear_ratio * wheel_radius
        
        return {
            'gear_ratio': gear_ratio,
            'time_75m': final_state.time,
            'final_velocity': final_state.velocity,
            'final_velocity_kmh': final_state.velocity * 3.6,
            'peak_power_kw': peak_power,
            'max_vehicle_speed_kmh': max_vehicle_speed * 3.6,
            'success': True
        }
    except Exception as e:
        return {
            'gear_ratio': gear_ratio,
            'time_75m': float('inf'),
            'final_velocity': 0,
            'final_velocity_kmh': 0,
            'peak_power_kw': 0,
            'max_vehicle_speed_kmh': 0,
            'success': False,
            'error': str(e)
        }


def optimize_gear_ratio(config_name: str, gear_ratios: list) -> list:
    """
    Run optimization sweep for a configuration.
    
    Args:
        config_name: Name of config file
        gear_ratios: List of gear ratios to test
        
    Returns:
        List of results for each gear ratio
    """
    # Load base config
    config_path = package_root / "config" / "vehicle_configs" / f"{config_name}.json"
    base_config = load_config(config_path)
    
    results = []
    print(f"\nOptimizing {config_name}...")
    print(f"Testing {len(gear_ratios)} gear ratios from {min(gear_ratios):.1f} to {max(gear_ratios):.1f}")
    print("-" * 70)
    
    for i, gr in enumerate(gear_ratios):
        result = run_with_gear_ratio(base_config, gr)
        results.append(result)
        
        if result['success']:
            print(f"  GR={gr:5.2f}: t={result['time_75m']:.3f}s, "
                  f"v_final={result['final_velocity_kmh']:.1f}km/h, "
                  f"P_peak={result['peak_power_kw']:.1f}kW, "
                  f"v_max={result['max_vehicle_speed_kmh']:.0f}km/h")
        else:
            print(f"  GR={gr:5.2f}: FAILED - {result.get('error', 'Unknown error')}")
    
    return results


def find_optimal(results: list) -> dict:
    """Find the optimal gear ratio from results."""
    valid_results = [r for r in results if r['success']]
    if not valid_results:
        return None
    return min(valid_results, key=lambda r: r['time_75m'])


def plot_optimization(battery_results: list, supercap_results: list, save_path: str = None):
    """Create optimization plots."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Gear Ratio Optimization: 75m Acceleration', fontsize=14, fontweight='bold')
    
    # Extract data
    batt_gr = [r['gear_ratio'] for r in battery_results if r['success']]
    batt_time = [r['time_75m'] for r in battery_results if r['success']]
    batt_power = [r['peak_power_kw'] for r in battery_results if r['success']]
    batt_vmax = [r['max_vehicle_speed_kmh'] for r in battery_results if r['success']]
    batt_vfinal = [r['final_velocity_kmh'] for r in battery_results if r['success']]
    
    cap_gr = [r['gear_ratio'] for r in supercap_results if r['success']]
    cap_time = [r['time_75m'] for r in supercap_results if r['success']]
    cap_power = [r['peak_power_kw'] for r in supercap_results if r['success']]
    cap_vmax = [r['max_vehicle_speed_kmh'] for r in supercap_results if r['success']]
    cap_vfinal = [r['final_velocity_kmh'] for r in supercap_results if r['success']]
    
    # Find optima
    batt_opt = find_optimal(battery_results)
    cap_opt = find_optimal(supercap_results)
    
    # Plot 1: 75m Time vs Gear Ratio
    ax1 = axes[0, 0]
    ax1.plot(batt_gr, batt_time, 'b-o', label='Battery', linewidth=2, markersize=4)
    ax1.plot(cap_gr, cap_time, 'r-s', label='Supercapacitor', linewidth=2, markersize=4)
    if batt_opt:
        ax1.axvline(x=batt_opt['gear_ratio'], color='b', linestyle='--', alpha=0.5)
        ax1.plot(batt_opt['gear_ratio'], batt_opt['time_75m'], 'b*', markersize=15)
    if cap_opt:
        ax1.axvline(x=cap_opt['gear_ratio'], color='r', linestyle='--', alpha=0.5)
        ax1.plot(cap_opt['gear_ratio'], cap_opt['time_75m'], 'r*', markersize=15)
    ax1.set_xlabel('Gear Ratio')
    ax1.set_ylabel('75m Time (s)')
    ax1.set_title('75m Time vs Gear Ratio')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Peak Power vs Gear Ratio
    ax2 = axes[0, 1]
    ax2.plot(batt_gr, batt_power, 'b-o', label='Battery', linewidth=2, markersize=4)
    ax2.plot(cap_gr, cap_power, 'r-s', label='Supercapacitor', linewidth=2, markersize=4)
    ax2.axhline(y=80, color='g', linestyle=':', label='80kW FS limit', linewidth=2)
    ax2.set_xlabel('Gear Ratio')
    ax2.set_ylabel('Peak Power (kW)')
    ax2.set_title('Peak Power vs Gear Ratio')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Final Velocity vs Gear Ratio
    ax3 = axes[1, 0]
    ax3.plot(batt_gr, batt_vfinal, 'b-o', label='Battery (actual)', linewidth=2, markersize=4)
    ax3.plot(cap_gr, cap_vfinal, 'r-s', label='Supercap (actual)', linewidth=2, markersize=4)
    ax3.plot(batt_gr, batt_vmax, 'b--', label='Battery (max possible)', linewidth=1, alpha=0.5)
    ax3.plot(cap_gr, cap_vmax, 'r--', label='Supercap (max possible)', linewidth=1, alpha=0.5)
    ax3.set_xlabel('Gear Ratio')
    ax3.set_ylabel('Velocity (km/h)')
    ax3.set_title('Final Velocity vs Gear Ratio')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Summary text
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = "OPTIMIZATION RESULTS\n" + "="*40 + "\n\n"
    
    if batt_opt:
        summary_text += "BATTERY OPTIMAL:\n"
        summary_text += f"  Gear Ratio: {batt_opt['gear_ratio']:.2f}\n"
        summary_text += f"  75m Time: {batt_opt['time_75m']:.3f} s\n"
        summary_text += f"  Final Velocity: {batt_opt['final_velocity_kmh']:.1f} km/h\n"
        summary_text += f"  Peak Power: {batt_opt['peak_power_kw']:.1f} kW\n\n"
    
    if cap_opt:
        summary_text += "SUPERCAPACITOR OPTIMAL:\n"
        summary_text += f"  Gear Ratio: {cap_opt['gear_ratio']:.2f}\n"
        summary_text += f"  75m Time: {cap_opt['time_75m']:.3f} s\n"
        summary_text += f"  Final Velocity: {cap_opt['final_velocity_kmh']:.1f} km/h\n"
        summary_text += f"  Peak Power: {cap_opt['peak_power_kw']:.1f} kW\n\n"
    
    if batt_opt and cap_opt:
        time_diff = batt_opt['time_75m'] - cap_opt['time_75m']
        if time_diff > 0:
            summary_text += f"WINNER: SUPERCAPACITOR\n"
            summary_text += f"  Faster by {time_diff*1000:.1f} ms"
        else:
            summary_text += f"WINNER: BATTERY\n"
            summary_text += f"  Faster by {-time_diff*1000:.1f} ms"
    
    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to: {save_path}")
    
    plt.close()


def main():
    """Run gear ratio optimization."""
    print("="*70)
    print("GEAR RATIO OPTIMIZATION FOR 75m ACCELERATION")
    print("="*70)
    
    # Define gear ratios to test
    # Lower ratio = higher top speed (motor spins slower per wheel rev)
    # Higher ratio = lower top speed (motor hits max RPM sooner)
    # Include lower ratios to find true optimum
    gear_ratios = np.arange(3.0, 12.1, 0.5).tolist()
    
    # Optimize battery configuration
    battery_results = optimize_gear_ratio('base_vehicle', gear_ratios)
    batt_opt = find_optimal(battery_results)
    
    # Optimize supercapacitor configuration
    supercap_results = optimize_gear_ratio('supercapacitor_vehicle', gear_ratios)
    cap_opt = find_optimal(supercap_results)
    
    # Print summary
    print("\n" + "="*70)
    print("OPTIMIZATION SUMMARY")
    print("="*70)
    
    if batt_opt:
        print(f"\nBATTERY OPTIMAL:")
        print(f"  Gear Ratio: {batt_opt['gear_ratio']:.2f}")
        print(f"  75m Time: {batt_opt['time_75m']:.3f} s")
        print(f"  Final Velocity: {batt_opt['final_velocity_kmh']:.1f} km/h")
        print(f"  Peak Power: {batt_opt['peak_power_kw']:.1f} kW")
        print(f"  Max Possible Speed: {batt_opt['max_vehicle_speed_kmh']:.0f} km/h")
    
    if cap_opt:
        print(f"\nSUPERCAPACITOR OPTIMAL:")
        print(f"  Gear Ratio: {cap_opt['gear_ratio']:.2f}")
        print(f"  75m Time: {cap_opt['time_75m']:.3f} s")
        print(f"  Final Velocity: {cap_opt['final_velocity_kmh']:.1f} km/h")
        print(f"  Peak Power: {cap_opt['peak_power_kw']:.1f} kW")
        print(f"  Max Possible Speed: {cap_opt['max_vehicle_speed_kmh']:.0f} km/h")
    
    if batt_opt and cap_opt:
        print("\n" + "-"*70)
        time_diff = batt_opt['time_75m'] - cap_opt['time_75m']
        if time_diff > 0:
            print(f"OVERALL WINNER: SUPERCAPACITOR (faster by {time_diff*1000:.1f} ms)")
        else:
            print(f"OVERALL WINNER: BATTERY (faster by {-time_diff*1000:.1f} ms)")
    
    # Create plots
    save_path = package_root / 'figures' / 'gear_ratio_optimization.png'
    plot_optimization(battery_results, supercap_results, str(save_path))


if __name__ == '__main__':
    main()
