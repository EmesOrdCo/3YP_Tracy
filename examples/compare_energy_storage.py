#!/usr/bin/env python3
"""
Compare Battery vs Supercapacitor performance for Formula Student acceleration.

This script runs the 75m acceleration simulation with both energy storage types
and compares the results to determine which configuration is faster.

Based on:
- Battery: 300V nominal, constant voltage
- Supercapacitor: C46W-3R0-0600 (200 cells in series, 600V initial, voltage decays)
- Motor: YASA P400R with field weakening
- Inverter: BAMOCAR-PG-D3-700/400
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


def run_simulation(config_name: str, surface_mu_scaling: float = 1.0) -> dict:
    """
    Run acceleration simulation with specified config.
    
    Args:
        config_name: Name of config file (without .json extension)
        surface_mu_scaling: Grip multiplier (1.0=dry, 0.6=wet)
        
    Returns:
        Dictionary with simulation results
    """
    # Load configuration from vehicle_configs directory
    config_path = package_root / "config" / "vehicle_configs" / f"{config_name}.json"
    config = load_config(config_path)
    config.environment.surface_mu_scaling = surface_mu_scaling
    
    # Create solver and run
    solver = DynamicsSolver(config)
    final_state = solver.solve()
    
    # Extract time history
    times = [s.time for s in solver.state_history]
    positions = [s.position for s in solver.state_history]
    velocities = [s.velocity for s in solver.state_history]
    accelerations = [s.acceleration for s in solver.state_history]
    dc_bus_voltages = [s.dc_bus_voltage for s in solver.state_history]
    power_consumed = [s.power_consumed for s in solver.state_history]
    soc = [s.energy_storage_soc for s in solver.state_history]
    in_field_weakening = [s.in_field_weakening for s in solver.state_history]
    
    return {
        'config_name': config_name,
        'final_time': final_state.time,
        'final_velocity': final_state.velocity,
        'final_position': final_state.position,
        'times': times,
        'positions': positions,
        'velocities': velocities,
        'accelerations': accelerations,
        'dc_bus_voltages': dc_bus_voltages,
        'power_consumed': power_consumed,
        'soc': soc,
        'in_field_weakening': in_field_weakening,
        'total_mass': config.mass.total_mass,
        'energy_storage_type': getattr(config.powertrain, 'energy_storage_type', 'battery')
    }


def compare_results(battery_results: dict, supercap_results: dict):
    """Print comparison of results."""
    print("\n" + "="*70)
    print("FORMULA STUDENT ACCELERATION COMPARISON: Battery vs Supercapacitor")
    print("="*70)
    
    print(f"\n{'Parameter':<30} {'Battery':<20} {'Supercapacitor':<20}")
    print("-"*70)
    
    print(f"{'Total Mass (kg)':<30} {battery_results['total_mass']:<20.1f} {supercap_results['total_mass']:<20.1f}")
    print(f"{'75m Time (s)':<30} {battery_results['final_time']:<20.4f} {supercap_results['final_time']:<20.4f}")
    print(f"{'Final Velocity (m/s)':<30} {battery_results['final_velocity']:<20.2f} {supercap_results['final_velocity']:<20.2f}")
    print(f"{'Final Velocity (km/h)':<30} {battery_results['final_velocity']*3.6:<20.2f} {supercap_results['final_velocity']*3.6:<20.2f}")
    
    # Voltage analysis for supercap
    supercap_v_start = supercap_results['dc_bus_voltages'][0]
    supercap_v_end = supercap_results['dc_bus_voltages'][-1]
    voltage_drop_pct = (supercap_v_start - supercap_v_end) / supercap_v_start * 100
    
    print(f"\n{'--- Supercapacitor Voltage ---':<30}")
    print(f"{'Initial Voltage (V)':<30} {'-':<20} {supercap_v_start:<20.1f}")
    print(f"{'Final Voltage (V)':<30} {'-':<20} {supercap_v_end:<20.1f}")
    print(f"{'Voltage Drop (%)':<30} {'-':<20} {voltage_drop_pct:<20.1f}")
    
    # Field weakening analysis
    fw_battery = sum(battery_results['in_field_weakening'])
    fw_supercap = sum(supercap_results['in_field_weakening'])
    total_steps = len(battery_results['in_field_weakening'])
    
    print(f"\n{'--- Field Weakening ---':<30}")
    print(f"{'Steps in FW Region':<30} {fw_battery:<20} {fw_supercap:<20}")
    print(f"{'% Time in FW':<30} {fw_battery/total_steps*100:<20.1f} {fw_supercap/total_steps*100:<20.1f}")
    
    # Winner
    print("\n" + "="*70)
    time_diff = battery_results['final_time'] - supercap_results['final_time']
    if time_diff > 0:
        winner = "SUPERCAPACITOR"
        advantage = time_diff
    else:
        winner = "BATTERY"
        advantage = -time_diff
    
    print(f"WINNER: {winner} (faster by {advantage*1000:.1f} ms)")
    print("="*70)


def downsample(data: list, factor: int = 10) -> list:
    """Downsample data by taking every Nth point."""
    return data[::factor]


def moving_average(data: list, window: int = 50) -> list:
    """Apply causal moving average (no future-looking) to avoid boundary artifacts.
    
    Uses only past and current samples - prevents fake 'spike' at t=0 from
    centered filter pulling in future high values.
    """
    result = []
    for i in range(len(data)):
        start = max(0, i - window + 1)
        end = i + 1
        result.append(sum(data[start:end]) / (end - start))
    return result


def plot_comparison(battery_results: dict, supercap_results: dict, save_path: str = None, title_suffix: str = ''):
    """Create comparison plots with downsampled/smoothed data for clarity."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    title = 'Battery vs Supercapacitor: 75m Acceleration Comparison'
    if title_suffix:
        title += f' ({title_suffix})'
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    # Downsample factor (reduces 4600 points to ~460)
    ds = 10
    
    # Smooth window for noisy signals (power, voltage, SOC)
    smooth_window = 100
    # Shorter window for acceleration: preserves 50ms torque ramp (avoids 100ms visual lag)
    accel_smooth_window = 20
    
    # Plot 1: Position vs Time (smooth, use all points - not noisy)
    ax1 = axes[0, 0]
    ax1.plot(downsample(battery_results['times'], ds), 
             downsample(battery_results['positions'], ds), 
             'b-', label='Battery', linewidth=2)
    ax1.plot(downsample(supercap_results['times'], ds), 
             downsample(supercap_results['positions'], ds), 
             'r--', label='Supercapacitor', linewidth=2)
    ax1.axhline(y=75, color='g', linestyle=':', label='75m target')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Position (m)')
    ax1.set_title('Position vs Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Velocity vs Time (smooth, downsample)
    ax2 = axes[0, 1]
    ax2.plot(downsample(battery_results['times'], ds), 
             downsample([v*3.6 for v in battery_results['velocities']], ds), 
             'b-', label='Battery', linewidth=2)
    ax2.plot(downsample(supercap_results['times'], ds), 
             downsample([v*3.6 for v in supercap_results['velocities']], ds), 
             'r--', label='Supercapacitor', linewidth=2)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Velocity (km/h)')
    ax2.set_title('Velocity vs Time')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Acceleration vs Time (light smoothing to preserve 50ms ramp)
    ax3 = axes[0, 2]
    batt_accel_smooth = moving_average(battery_results['accelerations'], accel_smooth_window)
    cap_accel_smooth = moving_average(supercap_results['accelerations'], accel_smooth_window)
    ax3.plot(downsample(battery_results['times'], ds), 
             downsample(batt_accel_smooth, ds), 
             'b-', label='Battery', linewidth=2)
    ax3.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_accel_smooth, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Acceleration (m/s²)')
    ax3.set_title('Acceleration vs Time')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: DC Bus Voltage vs Time (SMOOTHED - oscillates slightly)
    ax4 = axes[1, 0]
    batt_volt_smooth = moving_average(battery_results['dc_bus_voltages'], smooth_window)
    cap_volt_smooth = moving_average(supercap_results['dc_bus_voltages'], smooth_window)
    ax4.plot(downsample(battery_results['times'], ds), 
             downsample(batt_volt_smooth, ds), 
             'b-', label='Battery', linewidth=2)
    ax4.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_volt_smooth, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('DC Bus Voltage (V)')
    ax4.set_title('DC Bus Voltage vs Time')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Power vs Time (SMOOTHED - oscillates heavily at max speed)
    ax5 = axes[1, 1]
    batt_power_smooth = moving_average([p/1000 for p in battery_results['power_consumed']], smooth_window)
    cap_power_smooth = moving_average([p/1000 for p in supercap_results['power_consumed']], smooth_window)
    ax5.plot(downsample(battery_results['times'], ds), 
             downsample(batt_power_smooth, ds), 
             'b-', label='Battery', linewidth=2)
    ax5.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_power_smooth, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    ax5.axhline(y=80, color='g', linestyle=':', label='80kW limit')
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Power (kW)')
    ax5.set_title('Power Consumed vs Time (smoothed)')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # Plot 6: State of Charge vs Time (SMOOTHED)
    ax6 = axes[1, 2]
    batt_soc_smooth = moving_average([s*100 for s in battery_results['soc']], smooth_window)
    cap_soc_smooth = moving_average([s*100 for s in supercap_results['soc']], smooth_window)
    ax6.plot(downsample(battery_results['times'], ds), 
             downsample(batt_soc_smooth, ds), 
             'b-', label='Battery', linewidth=2)
    ax6.plot(downsample(supercap_results['times'], ds), 
             downsample(cap_soc_smooth, ds), 
             'r--', label='Supercapacitor', linewidth=2)
    ax6.set_xlabel('Time (s)')
    ax6.set_ylabel('State of Charge (%)')
    ax6.set_title('Energy Storage SoC vs Time')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\nPlot saved to: {save_path}")
    
    plt.close()


def main():
    """Run comparison between battery and supercapacitor configurations."""
    print("Running Battery vs Supercapacitor Comparison...")
    print("-" * 50)
    
    # Run battery simulation
    print("\n1. Running BATTERY simulation...")
    try:
        battery_results = run_simulation('base_vehicle')
        print(f"   ✓ Completed in {battery_results['final_time']:.4f}s")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # Run supercapacitor simulation
    print("\n2. Running SUPERCAPACITOR simulation...")
    try:
        supercap_results = run_simulation('supercapacitor_vehicle')
        print(f"   ✓ Completed in {supercap_results['final_time']:.4f}s")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # Compare results
    compare_results(battery_results, supercap_results)
    
    # Plot comparison (dry)
    save_path = package_root / 'figures' / 'energy_storage_comparison.png'
    plot_comparison(battery_results, supercap_results, str(save_path))
    
    # Run wet (battery vs supercap, same 6-panel layout)
    print("\n3. Running WET (surface_mu_scaling=0.6)...")
    battery_wet = run_simulation('base_vehicle', surface_mu_scaling=0.6)
    supercap_wet = run_simulation('supercapacitor_vehicle', surface_mu_scaling=0.6)
    print(f"   Battery: {battery_wet['final_time']:.4f}s, Supercap: {supercap_wet['final_time']:.4f}s")
    save_path_wet = package_root / 'figures' / 'energy_storage_comparison_wet.png'
    plot_comparison(battery_wet, supercap_wet, str(save_path_wet), title_suffix='Wet Track')


if __name__ == '__main__':
    main()
