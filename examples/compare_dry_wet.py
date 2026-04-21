#!/usr/bin/env python3
"""
Compare dry vs wet track performance for Formula Student 75m acceleration.

Uses surface_mu_scaling: 1.0 = dry, 0.6 = wet (literature-based for racing slicks).
"""

import sys
from pathlib import Path
from copy import deepcopy
import numpy as np
import matplotlib.pyplot as plt

package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver


def run_simulation(config, surface_mu_scaling: float = 1.0) -> dict:
    """Run simulation with given surface_mu_scaling."""
    config = deepcopy(config)
    config.environment.surface_mu_scaling = surface_mu_scaling
    solver = DynamicsSolver(config)
    final_state = solver.solve()
    
    return {
        'final_time': final_state.time,
        'final_velocity': final_state.velocity,
        'times': [s.time for s in solver.state_history],
        'positions': [s.position for s in solver.state_history],
        'velocities': [s.velocity for s in solver.state_history],
        'accelerations': [s.acceleration for s in solver.state_history],
        'power_consumed': [s.power_consumed for s in solver.state_history],
        'dc_bus_voltages': [s.dc_bus_voltage for s in solver.state_history],
        'soc': [s.energy_storage_soc for s in solver.state_history],
        'surface_mu_scaling': surface_mu_scaling,
    }


def downsample(data: list, factor: int = 10) -> list:
    """Downsample by taking every Nth point."""
    return data[::factor]


def moving_average(data: list, window: int = 20) -> list:
    """Causal moving average."""
    result = []
    for i in range(len(data)):
        start = max(0, i - window + 1)
        end = i + 1
        result.append(sum(data[start:end]) / (end - start))
    return result


def main():
    print("Dry vs Wet Track Comparison (75m acceleration)")
    print("-" * 50)
    
    config = load_config(package_root / "config" / "vehicle_configs" / "base_vehicle.json")
    
    # Dry run
    print("\n1. Running DRY (surface_mu_scaling=1.0)...")
    dry = run_simulation(config, surface_mu_scaling=1.0)
    print(f"   ✓ Completed in {dry['final_time']:.4f}s")
    
    # Wet run
    print("\n2. Running WET (surface_mu_scaling=0.6)...")
    wet = run_simulation(config, surface_mu_scaling=0.6)
    print(f"   ✓ Completed in {wet['final_time']:.4f}s")
    
    # Summary
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"  Dry: {dry['final_time']:.4f} s  @  {dry['final_velocity']*3.6:.1f} km/h")
    print(f"  Wet: {wet['final_time']:.4f} s  @  {wet['final_velocity']*3.6:.1f} km/h")
    print(f"  Wet is {wet['final_time'] - dry['final_time']:.3f} s slower")
    print("=" * 50)
    
    # Plot (6-panel layout matching energy storage comparison)
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Dry vs Wet Track: 75m Acceleration', fontsize=14, fontweight='bold')
    
    ds = 10
    accel_window = 20
    smooth_window = 100
    
    # Plot 1: Position vs Time
    ax1 = axes[0, 0]
    ax1.plot(downsample(dry['times'], ds), downsample(dry['positions'], ds), 'b-', label='Dry (μ=1.0)', linewidth=2)
    ax1.plot(downsample(wet['times'], ds), downsample(wet['positions'], ds), 'c--', label='Wet (μ=0.6)', linewidth=2)
    ax1.axhline(y=75, color='g', linestyle=':', alpha=0.7)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Position (m)')
    ax1.set_title('Position vs Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Velocity vs Time
    ax2 = axes[0, 1]
    ax2.plot(downsample(dry['times'], ds), downsample([v*3.6 for v in dry['velocities']], ds), 'b-', label='Dry', linewidth=2)
    ax2.plot(downsample(wet['times'], ds), downsample([v*3.6 for v in wet['velocities']], ds), 'c--', label='Wet', linewidth=2)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Velocity (km/h)')
    ax2.set_title('Velocity vs Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Acceleration vs Time
    ax3 = axes[0, 2]
    dry_accel = moving_average(dry['accelerations'], accel_window)
    wet_accel = moving_average(wet['accelerations'], accel_window)
    ax3.plot(downsample(dry['times'], ds), downsample(dry_accel, ds), 'b-', label='Dry', linewidth=2)
    ax3.plot(downsample(wet['times'], ds), downsample(wet_accel, ds), 'c--', label='Wet', linewidth=2)
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Acceleration (m/s²)')
    ax3.set_title('Acceleration vs Time')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: DC Bus Voltage vs Time
    ax4 = axes[1, 0]
    dry_volt = moving_average(dry['dc_bus_voltages'], smooth_window)
    wet_volt = moving_average(wet['dc_bus_voltages'], smooth_window)
    ax4.plot(downsample(dry['times'], ds), downsample(dry_volt, ds), 'b-', label='Dry', linewidth=2)
    ax4.plot(downsample(wet['times'], ds), downsample(wet_volt, ds), 'c--', label='Wet', linewidth=2)
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('DC Bus Voltage (V)')
    ax4.set_title('DC Bus Voltage vs Time')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Power vs Time
    ax5 = axes[1, 1]
    dry_power = moving_average([p/1000 for p in dry['power_consumed']], smooth_window)
    wet_power = moving_average([p/1000 for p in wet['power_consumed']], smooth_window)
    ax5.plot(downsample(dry['times'], ds), downsample(dry_power, ds), 'b-', label='Dry', linewidth=2)
    ax5.plot(downsample(wet['times'], ds), downsample(wet_power, ds), 'c--', label='Wet', linewidth=2)
    ax5.axhline(y=80, color='g', linestyle=':', alpha=0.7, label='80 kW limit')
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Power (kW)')
    ax5.set_title('Power vs Time')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # Plot 6: State of Charge vs Time
    ax6 = axes[1, 2]
    dry_soc = moving_average([s*100 for s in dry['soc']], smooth_window)
    wet_soc = moving_average([s*100 for s in wet['soc']], smooth_window)
    ax6.plot(downsample(dry['times'], ds), downsample(dry_soc, ds), 'b-', label='Dry', linewidth=2)
    ax6.plot(downsample(wet['times'], ds), downsample(wet_soc, ds), 'c--', label='Wet', linewidth=2)
    ax6.set_xlabel('Time (s)')
    ax6.set_ylabel('State of Charge (%)')
    ax6.set_title('Energy Storage SoC vs Time')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    out_path = package_root / 'figures' / 'dry_wet_comparison.png'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\nPlot saved to: {out_path}")


if __name__ == '__main__':
    main()
