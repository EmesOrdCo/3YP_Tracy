#!/usr/bin/env python3
"""
Analyze acceleration phases from simulation data.

Computes exact phase boundaries from state history:
1. Initial traction: torque ramp (0 to ramp_duration)
2. Traction limited: full grip, power below limit
3. Power limited: 80 kW limit active

Uses actual simulation data - no approximations.
"""

import sys
from pathlib import Path

package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.config_loader import load_config
from dynamics.solver import DynamicsSolver

# From solver.py - torque ramp duration
RAMP_DURATION = 0.05  # s
POWER_LIMIT_W = 80_000  # FS EV 2.2
POWER_THRESHOLD = 79_000  # W - consider power-limited when above this


def analyze_phases(config_name: str = 'base_vehicle') -> dict:
    """
    Run simulation and compute phase boundaries from state history.
    
    Returns:
        dict with phase boundaries, durations, and key metrics
    """
    config_path = package_root / "config" / "vehicle_configs" / f"{config_name}.json"
    config = load_config(config_path)
    solver = DynamicsSolver(config)
    final_state = solver.solve()
    
    times = [s.time for s in solver.state_history]
    power = [s.power_consumed for s in solver.state_history]
    accel = [s.acceleration for s in solver.state_history]
    vel = [s.velocity for s in solver.state_history]
    pos = [s.position for s in solver.state_history]
    
    # Phase 1 end: end of torque ramp (exact from solver)
    t_phase1_end = RAMP_DURATION
    idx_phase1_end = next(i for i, t in enumerate(times) if t >= t_phase1_end)
    
    # Phase 2→3 transition: first timestep where power >= threshold
    idx_power_limited = None
    for i, p in enumerate(power):
        if p >= POWER_THRESHOLD:
            idx_power_limited = i
            break
    
    if idx_power_limited is None:
        # Never hit power limit (unusual for 75m)
        idx_power_limited = len(times) - 1
    
    t_phase2_end = times[idx_power_limited]
    
    # Phase durations
    t_final = final_state.time
    
    phase1_duration = t_phase1_end - 0.0
    phase2_duration = t_phase2_end - t_phase1_end
    phase3_duration = t_final - t_phase2_end
    
    # Key metrics at phase boundaries
    def sample_at_idx(idx):
        return {
            'time': times[idx],
            'position': pos[idx],
            'velocity': vel[idx],
            'acceleration': accel[idx],
            'power_kw': power[idx] / 1000,
        }
    
    return {
        'config_name': config_name,
        'total_time': t_final,
        'phases': {
            '1_initial_traction': {
                'start_s': 0.0,
                'end_s': t_phase1_end,
                'duration_s': phase1_duration,
                'limiting_factor': 'Torque ramp (control)',
                'at_end': sample_at_idx(idx_phase1_end),
            },
            '2_traction_limited': {
                'start_s': t_phase1_end,
                'end_s': t_phase2_end,
                'duration_s': phase2_duration,
                'limiting_factor': 'Tire grip',
                'at_start': sample_at_idx(idx_phase1_end),
                'at_end': sample_at_idx(idx_power_limited),
            },
            '3_power_limited': {
                'start_s': t_phase2_end,
                'end_s': t_final,
                'duration_s': phase3_duration,
                'limiting_factor': '80 kW FS limit',
                'at_start': sample_at_idx(idx_power_limited),
                'at_end': sample_at_idx(-1),
            },
        },
        'state_history': solver.state_history,
    }


def format_report(results: dict) -> str:
    """Format phase analysis as markdown report."""
    p = results['phases']
    lines = [
        "# Acceleration Phase Analysis (from simulation data)",
        "",
        f"**Config:** {results['config_name']}",
        f"**Total 75m time:** {results['total_time']:.4f} s",
        "",
        "## Phase Boundaries (data-derived)",
        "",
        "| Phase | Start (s) | End (s) | Duration (s) | Limiting factor |",
        "|-------|-----------|---------|---------------|-----------------|",
    ]
    
    for name, data in p.items():
        phase_label = {
            '1_initial_traction': '1. Initial traction',
            '2_traction_limited': '2. Traction limited',
            '3_power_limited': '3. Power limited',
        }[name]
        lines.append(
            f"| {phase_label} | {data['start_s']:.3f} | {data['end_s']:.3f} | "
            f"{data['duration_s']:.3f} | {data['limiting_factor']} |"
        )
    
    lines.extend([
        "",
        "## Phase Details",
        "",
        "### 1. Initial traction (torque ramp)",
        f"- **Duration:** {p['1_initial_traction']['duration_s']:.3f} s (0 to {p['1_initial_traction']['end_s']:.3f} s)",
        f"- **At end:** a = {p['1_initial_traction']['at_end']['acceleration']:.2f} m/s², "
        f"v = {p['1_initial_traction']['at_end']['velocity']*3.6:.1f} km/h, "
        f"P = {p['1_initial_traction']['at_end']['power_kw']:.1f} kW",
        "",
        "### 2. Traction limited",
        f"- **Duration:** {p['2_traction_limited']['duration_s']:.3f} s "
        f"({p['2_traction_limited']['start_s']:.3f} to {p['2_traction_limited']['end_s']:.3f} s)",
        f"- **At start:** a = {p['2_traction_limited']['at_start']['acceleration']:.2f} m/s², "
        f"P = {p['2_traction_limited']['at_start']['power_kw']:.1f} kW",
        f"- **At end (power limit reached):** a = {p['2_traction_limited']['at_end']['acceleration']:.2f} m/s², "
        f"v = {p['2_traction_limited']['at_end']['velocity']*3.6:.1f} km/h, "
        f"P = {p['2_traction_limited']['at_end']['power_kw']:.1f} kW",
        "",
        "### 3. Power limited",
        f"- **Duration:** {p['3_power_limited']['duration_s']:.3f} s "
        f"({p['3_power_limited']['start_s']:.3f} to {p['3_power_limited']['end_s']:.3f} s)",
        f"- **At start:** a = {p['3_power_limited']['at_start']['acceleration']:.2f} m/s², "
        f"v = {p['3_power_limited']['at_start']['velocity']*3.6:.1f} km/h",
        f"- **At finish (75m):** a = {p['3_power_limited']['at_end']['acceleration']:.2f} m/s², "
        f"v = {p['3_power_limited']['at_end']['velocity']*3.6:.1f} km/h, "
        f"P = {p['3_power_limited']['at_end']['power_kw']:.1f} kW",
        "",
    ])
    
    return "\n".join(lines)


def main():
    print("Analyzing acceleration phases from simulation data...")
    results = analyze_phases('base_vehicle')
    
    report = format_report(results)
    print(report)
    
    out_path = package_root / 'docs' / 'ACCELERATION_PHASES.md'
    out_path.write_text(report, encoding='utf-8')
    print(f"\nReport saved to: {out_path}")


if __name__ == '__main__':
    main()
