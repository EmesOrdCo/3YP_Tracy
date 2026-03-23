#!/usr/bin/env python3
"""
Create annotated version of energy storage comparison plot.
Labels all salient features for presentation.
Uses optimal gear ratios for each configuration.
"""

import sys
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Add package root to path
package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver


def run_simulation(config_name: str, gear_ratio: float = None) -> dict:
    """Run acceleration simulation with specified config and optional gear ratio override."""
    config_path = package_root / "config" / "vehicle_configs" / f"{config_name}.json"
    
    if gear_ratio is not None:
        # Load, modify, and save temp config
        with open(config_path) as f:
            config_dict = json.load(f)
        config_dict['powertrain']['gear_ratio'] = gear_ratio
        temp_path = package_root / "config" / "vehicle_configs" / "temp_config.json"
        with open(temp_path, 'w') as f:
            json.dump(config_dict, f)
        config = load_config(temp_path)
        import os
        os.remove(temp_path)
    else:
        config = load_config(config_path)
    
    solver = DynamicsSolver(config)
    final_state = solver.solve()
    
    times = [s.time for s in solver.state_history]
    positions = [s.position for s in solver.state_history]
    velocities = [s.velocity for s in solver.state_history]
    accelerations = [s.acceleration for s in solver.state_history]
    dc_bus_voltages = [s.dc_bus_voltage for s in solver.state_history]
    power_consumed = [s.power_consumed for s in solver.state_history]
    soc = [s.energy_storage_soc for s in solver.state_history]
    
    return {
        'config_name': config_name,
        'final_time': final_state.time,
        'final_velocity': final_state.velocity,
        'times': times,
        'positions': positions,
        'velocities': velocities,
        'accelerations': accelerations,
        'dc_bus_voltages': dc_bus_voltages,
        'power_consumed': power_consumed,
        'soc': soc,
        'total_mass': config.mass.total_mass,
        'gear_ratio': gear_ratio if gear_ratio else config.powertrain.gear_ratio,
    }


def downsample(data: list, factor: int = 10) -> list:
    return data[::factor]


def moving_average(data: list, window: int = 50) -> list:
    result = []
    for i in range(len(data)):
        start = max(0, i - window // 2)
        end = min(len(data), i + window // 2 + 1)
        result.append(sum(data[start:end]) / (end - start))
    return result


def plot_annotated(battery_results: dict, supercap_results: dict, save_path: str = None):
    """Create annotated comparison plots."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 11))
    
    batt_gr = battery_results['gear_ratio']
    cap_gr = supercap_results['gear_ratio']
    batt_time = battery_results['final_time']
    cap_time = supercap_results['final_time']
    time_diff_ms = (batt_time - cap_time) * 1000
    
    fig.suptitle(f'Battery (GR={batt_gr:.1f}) vs Supercapacitor (GR={cap_gr:.1f}): 75m Acceleration\n'
                 f'Battery: {batt_time:.3f}s | Supercap: {cap_time:.3f}s | Δ = {time_diff_ms:.0f}ms', 
                 fontsize=14, fontweight='bold')
    
    ds = 10
    smooth_window = 100
    
    # Common annotation style
    bbox_props = dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8, edgecolor='gray')
    arrow_props = dict(arrowstyle='->', connectionstyle='arc3,rad=0.2', color='black')
    
    # ===== Plot 1: Position vs Time =====
    ax1 = axes[0, 0]
    ax1.plot(downsample(battery_results['times'], ds), 
             downsample(battery_results['positions'], ds), 
             'b-', label=f'Battery (200kg)', linewidth=2)
    ax1.plot(downsample(supercap_results['times'], ds), 
             downsample(supercap_results['positions'], ds), 
             'r--', label=f'Supercapacitor (180kg)', linewidth=2)
    ax1.axhline(y=75, color='g', linestyle=':', label='75m finish', linewidth=2)
    
    # No annotations - curves are self-explanatory, times shown in title
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Position (m)')
    ax1.set_title('Position vs Time')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)
    
    # ===== Plot 2: Velocity vs Time =====
    ax2 = axes[0, 1]
    batt_vel_kmh = [v*3.6 for v in battery_results['velocities']]
    cap_vel_kmh = [v*3.6 for v in supercap_results['velocities']]
    
    ax2.plot(downsample(battery_results['times'], ds), 
             downsample(batt_vel_kmh, ds), 
             'b-', label='Battery', linewidth=2)
    ax2.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_vel_kmh, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    
    # No annotations - continuous acceleration, no plateau at optimal GR
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Velocity (km/h)')
    ax2.set_title('Velocity vs Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # ===== Plot 3: Acceleration vs Time =====
    ax3 = axes[0, 2]
    # No smoothing - show true physics
    ax3.plot(downsample(battery_results['times'], ds), 
             downsample(battery_results['accelerations'], ds), 
             'b-', label='Battery', linewidth=2)
    ax3.plot(downsample(supercap_results['times'], ds), 
             downsample(supercap_results['accelerations'], ds), 
             'r--', label='Supercapacitor', linewidth=2)
    
    # Annotation - point to the battery curve in the declining section
    ax3.annotate('Power-limited:\na = P/(m×v)', 
                 xy=(2.5, 8.5), 
                 xytext=(2.8, 12),
                 fontsize=9, bbox=bbox_props, arrowprops=arrow_props)
    
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Acceleration (m/s²)')
    ax3.set_title('Acceleration vs Time')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 16)
    
    # ===== Plot 4: DC Bus Voltage vs Time =====
    ax4 = axes[1, 0]
    batt_volt_smooth = moving_average(battery_results['dc_bus_voltages'], smooth_window)
    cap_volt_smooth = moving_average(supercap_results['dc_bus_voltages'], smooth_window)
    
    ax4.plot(downsample(battery_results['times'], ds), 
             downsample(batt_volt_smooth, ds), 
             'b-', label='Battery', linewidth=2)
    ax4.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_volt_smooth, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    
    # Annotation - point directly to the supercap voltage curve
    ax4.annotate('Supercap: V drops\nas E = ½CV² depletes', 
                 xy=(2.5, 480), 
                 xytext=(0.3, 520),
                 fontsize=9, bbox=bbox_props, arrowprops=arrow_props)
    
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('DC Bus Voltage (V)')
    ax4.set_title('DC Bus Voltage vs Time')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # ===== Plot 5: Power vs Time =====
    ax5 = axes[1, 1]
    # No smoothing - show true physics
    batt_power_kw = [p/1000 for p in battery_results['power_consumed']]
    cap_power_kw = [p/1000 for p in supercap_results['power_consumed']]
    
    ax5.plot(downsample(battery_results['times'], ds), 
             downsample(batt_power_kw, ds), 
             'b-', label='Battery', linewidth=2)
    ax5.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_power_kw, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    ax5.axhline(y=80, color='g', linestyle=':', label='80kW FS limit', linewidth=2)
    
    # Annotation - point to the 80kW limit line
    ax5.annotate('80kW FS limit\n(EV 2.2)', 
                 xy=(2.5, 80), 
                 xytext=(2.5, 60),
                 fontsize=9, bbox=bbox_props, arrowprops=arrow_props)
    
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Power (kW)')
    ax5.set_title('Power Consumed vs Time')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # ===== Plot 6: State of Charge vs Time =====
    ax6 = axes[1, 2]
    batt_soc_smooth = moving_average([s*100 for s in battery_results['soc']], smooth_window)
    cap_soc_smooth = moving_average([s*100 for s in supercap_results['soc']], smooth_window)
    
    ax6.plot(downsample(battery_results['times'], ds), 
             downsample(batt_soc_smooth, ds), 
             'b-', label='Battery', linewidth=2)
    ax6.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_soc_smooth, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    
    # Annotation - point to the supercap SoC curve
    ax6.annotate('Supercap: smaller\ncapacity, larger\nSoC swing', 
                 xy=(3.0, 55), 
                 xytext=(1.2, 65),
                 fontsize=9, bbox=bbox_props, arrowprops=arrow_props)
    
    ax6.set_xlabel('Time (s)')
    ax6.set_ylabel('State of Charge (%)')
    ax6.set_title('Energy Storage SoC vs Time')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Annotated plot saved to: {save_path}")
    
    plt.close()


def main():
    print("Generating energy storage comparison at OPTIMAL gear ratios...")
    print()
    
    # Optimal gear ratios determined by sweep analysis:
    # - Both configs optimal at GR ~5.0 (just before motor speed limit kicks in)
    # - This gives fastest 75m time without hitting motor speed limit
    BATTERY_OPTIMAL_GR = 5.0
    SUPERCAP_OPTIMAL_GR = 5.0
    
    print(f"Battery: using optimal GR = {BATTERY_OPTIMAL_GR}")
    battery_results = run_simulation('base_vehicle', gear_ratio=BATTERY_OPTIMAL_GR)
    print(f"  -> Time: {battery_results['final_time']:.3f}s, Final velocity: {battery_results['final_velocity']*3.6:.1f} km/h")
    
    print(f"Supercapacitor: using optimal GR = {SUPERCAP_OPTIMAL_GR}")
    supercap_results = run_simulation('supercapacitor_vehicle', gear_ratio=SUPERCAP_OPTIMAL_GR)
    print(f"  -> Time: {supercap_results['final_time']:.3f}s, Final velocity: {supercap_results['final_velocity']*3.6:.1f} km/h")
    
    time_diff = (battery_results['final_time'] - supercap_results['final_time']) * 1000
    print(f"\nSupercapacitor advantage: {time_diff:.0f}ms faster")
    
    # Save to main figures folder (overwrites old non-optimal version)
    save_path = package_root / 'figures' / 'energy_storage_comparison.png'
    plot_annotated(battery_results, supercap_results, str(save_path))


if __name__ == '__main__':
    main()
