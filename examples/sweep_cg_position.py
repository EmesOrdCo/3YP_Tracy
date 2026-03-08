#!/usr/bin/env python3
"""
Sweep CG position to understand its effect on acceleration performance.

This script explores how longitudinal (cg_x) and vertical (cg_z) CG positions
affect 75m acceleration time, load transfer, and wheelie risk.

Key trade-offs:
- CG further back (higher cg_x): More rear grip under acceleration, but wheelie risk
- CG lower (lower cg_z): Less load transfer, more stable, but packaging constraints
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy

# Add package root to path
package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver


def calculate_wheelie_limit_accel(cg_x: float, cg_z: float, wheelbase: float) -> float:
    """
    Calculate the acceleration at which front wheels lift off.
    
    Wheelie occurs when: a_wheelie = g * (wheelbase - cg_x) / cg_z
    
    Args:
        cg_x: CG distance from front axle (m)
        cg_z: CG height above ground (m)
        wheelbase: Wheelbase (m)
        
    Returns:
        Wheelie limit acceleration (m/s²)
    """
    g = 9.81
    b = wheelbase - cg_x  # Distance from CG to front axle
    if cg_z <= 0:
        return float('inf')
    return g * b / cg_z


def run_with_cg(base_config, cg_x: float, cg_z: float) -> dict:
    """
    Run simulation with specific CG position.
    
    Args:
        base_config: Base vehicle configuration
        cg_x: CG distance from front axle (m)
        cg_z: CG height above ground (m)
        
    Returns:
        Dictionary with results
    """
    config = deepcopy(base_config)
    config.mass.cg_x = cg_x
    config.mass.cg_z = cg_z
    
    try:
        solver = DynamicsSolver(config)
        final_state = solver.solve()
        
        # Extract key metrics
        normal_forces_front = [s.normal_force_front for s in solver.state_history]
        normal_forces_rear = [s.normal_force_rear for s in solver.state_history]
        accelerations = [s.acceleration for s in solver.state_history]
        
        # Calculate wheelie limit and check if exceeded
        wheelie_limit = calculate_wheelie_limit_accel(cg_x, cg_z, config.mass.wheelbase)
        peak_accel = max(accelerations)
        
        # Wheelie detected if peak acceleration exceeds theoretical limit
        # (or if front normal force hit zero, which is clamped in the sim)
        wheelie_detected = peak_accel >= wheelie_limit * 0.95  # 5% margin
        
        # Calculate margin to wheelie (positive = safe, negative = wheelie)
        wheelie_margin = wheelie_limit - peak_accel
        
        # Calculate load transfer metrics
        min_front = min(normal_forces_front)
        max_rear = max(normal_forces_rear)
        
        # Static weight distribution (use config values for accuracy)
        g = 9.81
        wheelbase = config.mass.wheelbase
        static_rear_pct = (cg_x / wheelbase) * 100
        
        return {
            'cg_x': cg_x,
            'cg_z': cg_z,
            'time_75m': final_state.time,
            'final_velocity': final_state.velocity,
            'final_velocity_kmh': final_state.velocity * 3.6,
            'min_front_normal': min_front,
            'max_rear_normal': max_rear,
            'static_rear_pct': static_rear_pct,
            'peak_acceleration': peak_accel,
            'wheelie_limit': wheelie_limit,
            'wheelie_margin': wheelie_margin,
            'wheelie_detected': wheelie_detected,
            'success': True
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'cg_x': cg_x,
            'cg_z': cg_z,
            'time_75m': float('inf'),
            'final_velocity': 0,
            'final_velocity_kmh': 0,
            'min_front_normal': 0,
            'max_rear_normal': 0,
            'static_rear_pct': 0,
            'peak_acceleration': 0,
            'wheelie_limit': 0,
            'wheelie_margin': 0,
            'wheelie_detected': True,
            'success': False,
            'error': str(e)
        }


def sweep_cg_x(config_name: str, cg_x_values: list, cg_z_fixed: float) -> list:
    """Sweep CG longitudinal position."""
    config_path = package_root / "config" / "vehicle_configs" / f"{config_name}.json"
    base_config = load_config(config_path)
    
    results = []
    print(f"\nSweeping CG_x for {config_name} (CG_z fixed at {cg_z_fixed}m)...")
    print("-" * 70)
    
    for cg_x in cg_x_values:
        result = run_with_cg(base_config, cg_x, cg_z_fixed)
        results.append(result)
        
        if result['success']:
            wheelie_str = " [WHEELIE!]" if result['wheelie_detected'] else ""
            print(f"  cg_x={cg_x:.2f}m: t={result['time_75m']:.3f}s, "
                  f"rear%={result['static_rear_pct']:.1f}%, "
                  f"F_front_min={result['min_front_normal']:.0f}N{wheelie_str}")
        else:
            print(f"  cg_x={cg_x:.2f}m: FAILED - {result.get('error', 'Unknown')}")
    
    return results


def sweep_cg_z(config_name: str, cg_z_values: list, cg_x_fixed: float) -> list:
    """Sweep CG vertical position."""
    config_path = package_root / "config" / "vehicle_configs" / f"{config_name}.json"
    base_config = load_config(config_path)
    
    results = []
    print(f"\nSweeping CG_z for {config_name} (CG_x fixed at {cg_x_fixed}m)...")
    print("-" * 70)
    
    for cg_z in cg_z_values:
        result = run_with_cg(base_config, cg_x_fixed, cg_z)
        results.append(result)
        
        if result['success']:
            wheelie_str = " [WHEELIE!]" if result['wheelie_detected'] else ""
            print(f"  cg_z={cg_z:.2f}m: t={result['time_75m']:.3f}s, "
                  f"F_front_min={result['min_front_normal']:.0f}N{wheelie_str}")
        else:
            print(f"  cg_z={cg_z:.2f}m: FAILED - {result.get('error', 'Unknown')}")
    
    return results


def plot_cg_sweep(cg_x_results: list, cg_z_results: list, save_path: str = None):
    """Create CG position sweep plots."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('CG Position Effect on 75m Acceleration', fontsize=14, fontweight='bold')
    
    # Filter successful results
    x_valid = [r for r in cg_x_results if r['success']]
    z_valid = [r for r in cg_z_results if r['success']]
    
    # Extract data for CG_x sweep
    cg_x_vals = [r['cg_x'] for r in x_valid]
    x_times = [r['time_75m'] for r in x_valid]
    x_rear_pct = [r['static_rear_pct'] for r in x_valid]
    x_wheelie_margin = [r['wheelie_margin'] for r in x_valid]
    x_wheelie = [r['wheelie_detected'] for r in x_valid]
    x_peak_accel = [r['peak_acceleration'] for r in x_valid]
    x_wheelie_limit = [r['wheelie_limit'] for r in x_valid]
    
    # Extract data for CG_z sweep
    cg_z_vals = [r['cg_z'] for r in z_valid]
    z_times = [r['time_75m'] for r in z_valid]
    z_wheelie_margin = [r['wheelie_margin'] for r in z_valid]
    z_wheelie = [r['wheelie_detected'] for r in z_valid]
    z_peak_accel = [r['peak_acceleration'] for r in z_valid]
    z_wheelie_limit = [r['wheelie_limit'] for r in z_valid]
    
    # Plot 1: 75m Time vs CG_x
    ax1 = axes[0, 0]
    colors_x = ['red' if w else 'blue' for w in x_wheelie]
    ax1.scatter(cg_x_vals, x_times, c=colors_x, s=50, zorder=5)
    ax1.plot(cg_x_vals, x_times, 'b-', linewidth=1, alpha=0.5)
    ax1.set_xlabel('CG Distance from Front Axle (m)')
    ax1.set_ylabel('75m Time (s)')
    ax1.set_title('75m Time vs CG Longitudinal Position')
    ax1.grid(True, alpha=0.3)
    
    # Mark optimal (excluding wheelie)
    valid_x = [(r['cg_x'], r['time_75m']) for r in x_valid if not r['wheelie_detected']]
    if valid_x:
        opt_x = min(valid_x, key=lambda x: x[1])
        ax1.axvline(x=opt_x[0], color='g', linestyle='--', alpha=0.5, label=f'Optimal: {opt_x[0]:.2f}m')
        ax1.plot(opt_x[0], opt_x[1], 'g*', markersize=15)
        ax1.legend()
    
    # Plot 2: Acceleration vs Wheelie Limit (CG_x sweep)
    ax2 = axes[0, 1]
    ax2.plot(cg_x_vals, x_peak_accel, 'b-o', linewidth=2, markersize=4, label='Peak Acceleration')
    ax2.plot(cg_x_vals, x_wheelie_limit, 'r--', linewidth=2, label='Wheelie Limit')
    ax2.fill_between(cg_x_vals, x_peak_accel, x_wheelie_limit, 
                     where=[p < l for p, l in zip(x_peak_accel, x_wheelie_limit)],
                     alpha=0.3, color='green', label='Safe margin')
    ax2.fill_between(cg_x_vals, x_peak_accel, x_wheelie_limit,
                     where=[p >= l for p, l in zip(x_peak_accel, x_wheelie_limit)],
                     alpha=0.3, color='red', label='Wheelie zone')
    ax2.set_xlabel('CG Distance from Front Axle (m)')
    ax2.set_ylabel('Acceleration (m/s²)')
    ax2.set_title('Peak Acceleration vs Wheelie Limit')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: 75m Time vs CG_z
    ax3 = axes[1, 0]
    colors_z = ['red' if w else 'blue' for w in z_wheelie]
    ax3.scatter(cg_z_vals, z_times, c=colors_z, s=50, zorder=5)
    ax3.plot(cg_z_vals, z_times, 'b-', linewidth=1, alpha=0.5)
    ax3.set_xlabel('CG Height (m)')
    ax3.set_ylabel('75m Time (s)')
    ax3.set_title('75m Time vs CG Height')
    ax3.grid(True, alpha=0.3)
    
    # Mark optimal (excluding wheelie)
    valid_z = [(r['cg_z'], r['time_75m']) for r in z_valid if not r['wheelie_detected']]
    if valid_z:
        opt_z = min(valid_z, key=lambda x: x[1])
        ax3.axvline(x=opt_z[0], color='g', linestyle='--', alpha=0.5, label=f'Optimal: {opt_z[0]:.2f}m')
        ax3.plot(opt_z[0], opt_z[1], 'g*', markersize=15)
        ax3.legend()
    
    # Plot 4: Acceleration vs Wheelie Limit (CG_z sweep)
    ax4 = axes[1, 1]
    ax4.plot(cg_z_vals, z_peak_accel, 'b-o', linewidth=2, markersize=4, label='Peak Acceleration')
    ax4.plot(cg_z_vals, z_wheelie_limit, 'r--', linewidth=2, label='Wheelie Limit')
    ax4.fill_between(cg_z_vals, z_peak_accel, z_wheelie_limit,
                     where=[p < l for p, l in zip(z_peak_accel, z_wheelie_limit)],
                     alpha=0.3, color='green', label='Safe margin')
    ax4.fill_between(cg_z_vals, z_peak_accel, z_wheelie_limit,
                     where=[p >= l for p, l in zip(z_peak_accel, z_wheelie_limit)],
                     alpha=0.3, color='red', label='Wheelie zone')
    ax4.set_xlabel('CG Height (m)')
    ax4.set_ylabel('Acceleration (m/s²)')
    ax4.set_title('Peak Acceleration vs Wheelie Limit (CG Height)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add legend for colors
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='blue', label='No wheelie'),
                       Patch(facecolor='red', label='Wheelie risk')]
    fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to: {save_path}")
    
    plt.show()


def main():
    """Run CG position sweep analysis."""
    print("="*70)
    print("CG POSITION SWEEP FOR 75m ACCELERATION")
    print("="*70)
    
    # Get wheelbase from config for reference
    config_path = package_root / "config" / "vehicle_configs" / "supercapacitor_vehicle.json"
    base_config = load_config(config_path)
    wheelbase = base_config.mass.wheelbase
    default_cg_x = base_config.mass.cg_x
    default_cg_z = base_config.mass.cg_z
    
    print(f"\nVehicle wheelbase: {wheelbase}m")
    print(f"Default CG position: x={default_cg_x}m, z={default_cg_z}m")
    
    # Define sweep ranges
    # CG_x: from 40% to 90% of wheelbase (0.64m to 1.44m for 1.6m wheelbase)
    cg_x_values = np.arange(0.6, 1.5, 0.05).tolist()
    
    # CG_z: from 0.15m to 0.5m (low to high)
    cg_z_values = np.arange(0.15, 0.55, 0.025).tolist()
    
    # Run sweeps using supercapacitor config (faster, more interesting dynamics)
    cg_x_results = sweep_cg_x('supercapacitor_vehicle', cg_x_values, default_cg_z)
    cg_z_results = sweep_cg_z('supercapacitor_vehicle', cg_z_values, default_cg_x)
    
    # Find optima
    valid_x = [r for r in cg_x_results if r['success'] and not r['wheelie_detected']]
    valid_z = [r for r in cg_z_results if r['success'] and not r['wheelie_detected']]
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if valid_x:
        best_x = min(valid_x, key=lambda r: r['time_75m'])
        print(f"\nOptimal CG_x (no wheelie): {best_x['cg_x']:.2f}m")
        print(f"  75m Time: {best_x['time_75m']:.3f}s")
        print(f"  Rear weight: {best_x['static_rear_pct']:.1f}%")
        print(f"  Min front normal force: {best_x['min_front_normal']:.0f}N")
    
    if valid_z:
        best_z = min(valid_z, key=lambda r: r['time_75m'])
        print(f"\nOptimal CG_z (no wheelie): {best_z['cg_z']:.2f}m")
        print(f"  75m Time: {best_z['time_75m']:.3f}s")
        print(f"  Min front normal force: {best_z['min_front_normal']:.0f}N")
    
    # Plot results
    save_path = package_root / 'figures' / 'cg_position_sweep.png'
    plot_cg_sweep(cg_x_results, cg_z_results, str(save_path))


if __name__ == '__main__':
    main()
