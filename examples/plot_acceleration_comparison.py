#!/usr/bin/env python3
"""
Plot acceleration vs time: our simulation vs real-world reference data.

Focus on initial acceleration spike for verification.
Reference: Tesla Model S Plaid (AccelerationTimes.com), MotorTrend data.
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver

# Tesla Model S Plaid - published 0-60 mph segment times (AccelerationTimes.com)
# Convert to m/s: 10 mph = 4.47 m/s, 20 mph = 8.94 m/s, etc.
TESLA_PLAID_SPEED_TIMES = [
    (0, 0),           # t=0, v=0
    (0.4, 4.47),     # 0-10 mph
    (0.7, 8.94),     # 0-20 mph
    (1.0, 13.41),    # 0-30 mph
    (1.4, 17.88),    # 0-40 mph
    (1.8, 22.35),    # 0-50 mph
    (2.3, 26.82),    # 0-60 mph
]


def tesla_plaid_acceleration_profile():
    """Derive acceleration from Tesla Plaid velocity-time segments."""
    times = np.array([t for t, _ in TESLA_PLAID_SPEED_TIMES])
    velocities = np.array([v for _, v in TESLA_PLAID_SPEED_TIMES])
    
    # Segment accelerations: a = (v2-v1)/(t2-t1)
    accels = []
    for i in range(1, len(times)):
        dt = times[i] - times[i-1]
        dv = velocities[i] - velocities[i-1]
        accels.append(dv / dt if dt > 0 else 0)
    
    # Create fine time series for plotting (use midpoint of each segment)
    t_plot = []
    a_plot = []
    for i in range(1, len(times)):
        t_mid = (times[i-1] + times[i]) / 2
        t_plot.append(t_mid)
        a_plot.append(accels[i-1])
    
    return np.array(t_plot), np.array(a_plot)


def main():
    # Run our simulation
    config = load_config(package_root / "config" / "vehicle_configs" / "base_vehicle.json")
    solver = DynamicsSolver(config)
    solver.solve()
    
    times = np.array([s.time for s in solver.state_history])
    accels = np.array([s.acceleration for s in solver.state_history])
    
    # Causal smoothing (no future-looking) - short window preserves 50ms torque ramp
    def causal_avg(data, window):
        return [sum(data[max(0,i-window+1):i+1]) / (i+1 - max(0,i-window+1)) 
                for i in range(len(data))]
    accels_smooth = np.array(causal_avg(accels.tolist(), 20))
    
    # Tesla data
    t_tesla, a_tesla = tesla_plaid_acceleration_profile()
    
    # Create figure
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # --- Top: Full run (0-3.5s) ---
    ax1 = axes[0]
    ax1.plot(times, accels_smooth, 'b-', linewidth=2, label='Our FS Simulation (Battery)')
    ax1.plot(t_tesla, a_tesla, 'r-o', linewidth=1.5, markersize=8, label='Tesla Model S Plaid (reference)', markevery=1)
    
    # Add vertical line at 1s to highlight initial phase
    ax1.axvline(x=1.0, color='gray', linestyle='--', alpha=0.5)
    ax1.set_ylabel('Acceleration (m/s²)', fontsize=11)
    ax1.set_title('Acceleration vs Time: Simulation vs Real-World Reference', fontsize=12)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 3.6)
    ax1.set_ylim(0, 16)
    
    # --- Bottom: Initial spike zoom (0-1.2s) ---
    ax2 = axes[1]
    mask = times <= 1.2
    ax2.plot(times[mask], accels_smooth[mask], 'b-', linewidth=2.5, label='Our FS Simulation')
    # Only show Tesla points in 0-1.2s range
    t_mask = t_tesla <= 1.2
    ax2.plot(t_tesla[t_mask], a_tesla[t_mask], 'r-o', linewidth=1.5, markersize=10, label='Tesla Model S Plaid')
    
    ax2.axhline(y=13.2, color='green', linestyle=':', alpha=0.6, label='~13 m/s² (peak)')
    ax2.set_xlabel('Time (s)', fontsize=11)
    ax2.set_ylabel('Acceleration (m/s²)', fontsize=11)
    ax2.set_title('Initial Acceleration Spike (Zoom)', fontsize=12)
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 1.2)
    ax2.set_ylim(0, 16)
    
    # Add note
    fig.text(0.5, 0.02, 'Reference: Tesla Plaid 0-60 mph data (AccelerationTimes.com). Both show initial rise → peak → decline. '
             'Tesla: 750 kW AWD; Our sim: 80 kW RWD FS car.', ha='center', fontsize=9, style='italic')
    
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    
    out_path = package_root / "figures" / "acceleration_comparison.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Plot saved to: {out_path}")


if __name__ == "__main__":
    main()
