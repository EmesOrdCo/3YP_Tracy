"""Generate figures for the logbook."""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import numpy as np
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config_loader import load_config
from simulation.acceleration_sim import AccelerationSimulation
from analysis.results import extract_time_series_data

# Create figures directory
figures_dir = project_root / "figures"
figures_dir.mkdir(exist_ok=True)

# Set matplotlib style for clean, professional plots
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['figure.dpi'] = 150

def generate_simulation_plots():
    """Run simulation and generate plots."""
    print("Loading configuration...")
    config = load_config(str(project_root / "config/vehicle_configs/base_vehicle.json"))
    
    print("Running simulation...")
    sim = AccelerationSimulation(config)
    result = sim.run(fastest_time=3.5)
    state_history = sim.get_state_history()
    
    print(f"Simulation complete: {result.final_time:.3f} s, {result.final_velocity:.2f} m/s")
    
    # Extract time series data
    data = extract_time_series_data(state_history)
    time = np.array(data['time'])
    velocity = np.array(data['velocity'])
    position = np.array(data['position'])
    acceleration = np.array(data['acceleration'])
    power = np.abs(np.array(data['power_consumed'])) / 1000  # kW
    drive_force = np.array(data['drive_force'])
    drag_force = np.abs(np.array(data['drag_force']))
    rolling_resistance = np.abs(np.array(data['rolling_resistance']))
    normal_front = np.array(data['normal_force_front'])
    normal_rear = np.array(data['normal_force_rear'])
    
    # Plot 1: Velocity vs Time
    print("Generating velocity plot...")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(time, velocity, 'b-', linewidth=1.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Velocity (m/s)')
    ax.set_title('Velocity vs Time — 75m Acceleration Run')
    ax.set_xlim(0, max(time))
    ax.set_ylim(0, max(velocity) * 1.05)
    ax.axhline(y=velocity[-1], color='r', linestyle='--', alpha=0.5, label=f'Final: {velocity[-1]:.1f} m/s')
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "velocity_vs_time.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Plot 2: Power vs Time
    print("Generating power plot...")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(time, power, 'b-', linewidth=1.5, label='Power Consumed')
    ax.axhline(y=80, color='r', linestyle='--', linewidth=1.5, label='80 kW Limit (EV 2.2)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Power Consumption vs Time')
    ax.set_xlim(0, max(time))
    ax.set_ylim(0, 90)
    ax.fill_between(time, power, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "power_vs_time.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Plot 3: Acceleration vs Time
    print("Generating acceleration plot...")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(time, acceleration, 'b-', linewidth=1.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Acceleration (m/s²)')
    ax.set_title('Acceleration vs Time')
    ax.set_xlim(0, max(time))
    ax.axhline(y=9.81, color='gray', linestyle=':', alpha=0.5, label='1g reference')
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "acceleration_vs_time.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Plot 4: Forces Breakdown
    print("Generating forces plot...")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(time, drive_force, 'g-', linewidth=1.5, label='Drive Force')
    ax.plot(time, drag_force, 'r-', linewidth=1.5, label='Drag Force')
    ax.plot(time, rolling_resistance, 'orange', linewidth=1.5, label='Rolling Resistance')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Force (N)')
    ax.set_title('Force Breakdown vs Time')
    ax.set_xlim(0, max(time))
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "forces_vs_time.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Plot 5: Normal Forces (Load Transfer)
    print("Generating load transfer plot...")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(time, normal_front, 'b-', linewidth=1.5, label='Front Axle')
    ax.plot(time, normal_rear, 'r-', linewidth=1.5, label='Rear Axle')
    ax.axhline(y=(normal_front[0] + normal_rear[0])/2, color='gray', linestyle=':', 
               alpha=0.5, label='Static (50/50)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Normal Force (N)')
    ax.set_title('Normal Forces vs Time — Load Transfer During Acceleration')
    ax.set_xlim(0, max(time))
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "normal_forces_vs_time.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Plot 6: Velocity vs Position
    print("Generating velocity vs position plot...")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(position, velocity, 'b-', linewidth=1.5)
    ax.axvline(x=75, color='r', linestyle='--', alpha=0.5, label='75m finish')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Velocity (m/s)')
    ax.set_title('Velocity vs Position')
    ax.set_xlim(0, 80)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "velocity_vs_position.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Plot 7: Tyre Friction Curve
    print("Generating tyre friction curve...")
    slip_ratios = np.linspace(0, 0.5, 100)
    mu_max = 1.4
    slip_optimal = 0.12
    
    mu_values = []
    for slip in slip_ratios:
        if slip <= slip_optimal:
            mu = (mu_max / slip_optimal) * slip
        else:
            mu = mu_max * (1.0 - (slip - slip_optimal) / (1.0 - slip_optimal))
            mu = max(0.0, mu)
        mu_values.append(mu)
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(slip_ratios * 100, mu_values, 'b-', linewidth=1.5)
    ax.axvline(x=slip_optimal * 100, color='r', linestyle='--', alpha=0.5, 
               label=f'Optimal slip: {slip_optimal*100:.0f}%')
    ax.axhline(y=mu_max, color='g', linestyle='--', alpha=0.5, 
               label=f'Peak μ: {mu_max}')
    ax.set_xlabel('Slip Ratio (%)')
    ax.set_ylabel('Friction Coefficient μ')
    ax.set_title('Simplified Tyre Friction Model')
    ax.set_xlim(0, 50)
    ax.set_ylim(0, 1.6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "tyre_friction_curve.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    # Plot 8: Comprehensive multi-panel plot
    print("Generating comprehensive plot...")
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    
    # Velocity vs Time
    axes[0, 0].plot(time, velocity, 'b-', linewidth=1.2)
    axes[0, 0].set_xlabel('Time (s)')
    axes[0, 0].set_ylabel('Velocity (m/s)')
    axes[0, 0].set_title('Velocity')
    
    # Position vs Time
    axes[0, 1].plot(time, position, 'g-', linewidth=1.2)
    axes[0, 1].axhline(y=75, color='r', linestyle='--', alpha=0.5)
    axes[0, 1].set_xlabel('Time (s)')
    axes[0, 1].set_ylabel('Position (m)')
    axes[0, 1].set_title('Position')
    
    # Acceleration vs Time
    axes[0, 2].plot(time, acceleration, 'r-', linewidth=1.2)
    axes[0, 2].set_xlabel('Time (s)')
    axes[0, 2].set_ylabel('Acceleration (m/s²)')
    axes[0, 2].set_title('Acceleration')
    
    # Power vs Time
    axes[1, 0].plot(time, power, 'purple', linewidth=1.2)
    axes[1, 0].axhline(y=80, color='r', linestyle='--', alpha=0.5)
    axes[1, 0].set_xlabel('Time (s)')
    axes[1, 0].set_ylabel('Power (kW)')
    axes[1, 0].set_title('Power')
    
    # Forces vs Time
    axes[1, 1].plot(time, drive_force, 'g-', linewidth=1.2, label='Drive')
    axes[1, 1].plot(time, drag_force, 'r-', linewidth=1.2, label='Drag')
    axes[1, 1].set_xlabel('Time (s)')
    axes[1, 1].set_ylabel('Force (N)')
    axes[1, 1].set_title('Forces')
    axes[1, 1].legend(fontsize=8)
    
    # Normal Forces vs Time
    axes[1, 2].plot(time, normal_front, 'b-', linewidth=1.2, label='Front')
    axes[1, 2].plot(time, normal_rear, 'r-', linewidth=1.2, label='Rear')
    axes[1, 2].set_xlabel('Time (s)')
    axes[1, 2].set_ylabel('Normal Force (N)')
    axes[1, 2].set_title('Load Transfer')
    axes[1, 2].legend(fontsize=8)
    
    fig.suptitle(f'Simulation Results — Time: {result.final_time:.3f}s, Final Velocity: {result.final_velocity:.1f} m/s', 
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(figures_dir / "comprehensive_results.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    print(f"\nSimulation plots saved to {figures_dir}/")
    return result


def save_mermaid_diagrams():
    """Save Mermaid diagram source files for conversion."""
    
    mermaid_dir = figures_dir / "mermaid_src"
    mermaid_dir.mkdir(exist_ok=True)
    
    diagrams = {
        "system_architecture": """flowchart TD
    subgraph STATE[Current State]
        POS[Position x]
        VEL[Velocity v]
        OMEGA[Wheel Angular Velocity ω]
    end

    subgraph MODELS[Physical Models]
        AERO[Aerodynamics<br/>Drag and Downforce]
        MASS[Mass Properties<br/>Load Transfer]
        TYRE[Tyre Model<br/>Slip and Traction]
        PWR[Powertrain<br/>Torque and Power]
    end

    subgraph OUTPUTS[Calculated Values]
        FDRAG[Drag Force]
        FZ[Normal Forces]
        FX[Traction Force]
        TORQUE[Wheel Torque]
    end

    VEL --> AERO
    AERO --> FDRAG
    AERO --> |downforce| MASS
    
    MASS --> FZ
    FZ --> TYRE
    
    VEL --> TYRE
    OMEGA --> TYRE
    TYRE --> FX
    
    OMEGA --> PWR
    PWR --> TORQUE
    
    FDRAG --> SUM[Force Summation]
    FX --> SUM
    TORQUE --> SUM
    
    SUM --> ACCEL[Acceleration Calculation]
    ACCEL --> RK4[RK4 Integration]
    RK4 --> NEWSTATE[Updated State]""",
    
        "tyre_model": """flowchart TD
    subgraph INPUTS[Inputs]
        FZ[Normal Force Fz<br/>from load transfer calculation]
        OMEGA[Wheel Angular Velocity ω<br/>from previous state]
        V[Vehicle Velocity v<br/>from previous state]
        R[Loaded Radius r<br/>from configuration]
    end

    subgraph SLIP_CALC[Slip Calculation]
        VWHEEL[Wheel Peripheral Velocity<br/>Vw = ω × r]
        SLIP[Slip Ratio<br/>κ = Vw - V / V]
    end

    subgraph FRICTION[Friction Model]
        MU_CALC[Friction Coefficient<br/>μ = f of κ]
        MU_MAX[Peak Friction μmax]
        K_OPT[Optimal Slip κopt]
    end

    subgraph FORCES[Force Outputs]
        FX[Longitudinal Force<br/>Fx = μ × Fz]
        FRR[Rolling Resistance<br/>Frr = Crr × Fz]
    end

    OMEGA --> VWHEEL
    R --> VWHEEL
    VWHEEL --> SLIP
    V --> SLIP
    
    SLIP --> MU_CALC
    MU_MAX --> MU_CALC
    K_OPT --> MU_CALC
    
    MU_CALC --> FX
    FZ --> FX
    FZ --> FRR""",
    
        "aerodynamic_forces": """flowchart LR
    subgraph LOW[Low Speed: 5 m/s]
        DRAG1[Drag: 12 N]
        DOWN1[Downforce: 15 N]
    end
    
    subgraph MED[Medium Speed: 15 m/s]
        DRAG2[Drag: 110 N]
        DOWN2[Downforce: 138 N]
    end
    
    subgraph HIGH[High Speed: 25 m/s]
        DRAG3[Drag: 306 N]
        DOWN3[Downforce: 383 N]
    end
    
    LOW --> MED --> HIGH""",
    
        "powertrain_flow": """flowchart TD
    REQ[Requested Wheel Torque<br/>from control strategy] --> CONV1[Convert to Motor Torque<br/>Tm = Tw / Ng / η]
    CONV1 --> CURR[Calculate Motor Current<br/>I = Tm / Kt]
    CURR --> PWR[Calculate Electrical Power<br/>P = V × I]
    PWR --> CHECK{P > 80 kW?}
    CHECK --> |Yes| LIMIT[Limit Current<br/>Imax = 80000 / V]
    CHECK --> |No| PASS[Use Calculated Current]
    LIMIT --> RECALC[Recalculate Torque<br/>Tm = Imax × Kt]
    PASS --> OUT[Output Wheel Torque<br/>Tw = Tm × Ng × η]
    RECALC --> OUT""",
    
        "simulation_results": """flowchart LR
    subgraph RESULTS[Simulation Results]
        TIME[Time: 4.31 s]
        VMAX[Final Velocity: 28.4 m/s]
        PMAX[Peak Power: 80.0 kW]
        AMAX[Peak Acceleration: 12.1 m/s²]
    end
    
    subgraph COMPLIANCE[Rule Compliance]
        PWR_OK[Power Limit: PASS<br/>80 kW ≤ 80 kW]
        TIME_OK[Time Limit: PASS<br/>4.31 s < 25 s]
    end
    
    RESULTS --> COMPLIANCE"""
    }
    
    print("\nSaving Mermaid diagram source files...")
    for name, content in diagrams.items():
        filepath = mermaid_dir / f"{name}.mmd"
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Saved {filepath}")
    
    # Create HTML file for viewing/exporting Mermaid diagrams
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Logbook Diagrams</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 40px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
        .mermaid { background: #fff; padding: 20px; border: 1px solid #ddd; margin: 20px 0; }
        .instructions { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 30px; }
    </style>
</head>
<body>
    <h1>Formula Student Acceleration Simulation — Logbook Diagrams</h1>
    
    <div class="instructions">
        <strong>To export as PNG:</strong> Right-click on each diagram and select "Save image as..." 
        or use your browser's screenshot tool.
    </div>
    
    <h2>1. System Architecture</h2>
    <div class="mermaid">
flowchart TD
    subgraph STATE[Current State]
        POS[Position x]
        VEL[Velocity v]
        OMEGA[Wheel Angular Velocity ω]
    end

    subgraph MODELS[Physical Models]
        AERO[Aerodynamics<br/>Drag and Downforce]
        MASS[Mass Properties<br/>Load Transfer]
        TYRE[Tyre Model<br/>Slip and Traction]
        PWR[Powertrain<br/>Torque and Power]
    end

    subgraph OUTPUTS[Calculated Values]
        FDRAG[Drag Force]
        FZ[Normal Forces]
        FX[Traction Force]
        TORQUE[Wheel Torque]
    end

    VEL --> AERO
    AERO --> FDRAG
    AERO --> |downforce| MASS
    
    MASS --> FZ
    FZ --> TYRE
    
    VEL --> TYRE
    OMEGA --> TYRE
    TYRE --> FX
    
    OMEGA --> PWR
    PWR --> TORQUE
    
    FDRAG --> SUM[Force Summation]
    FX --> SUM
    TORQUE --> SUM
    
    SUM --> ACCEL[Acceleration Calculation]
    ACCEL --> RK4[RK4 Integration]
    RK4 --> NEWSTATE[Updated State]
    </div>
    
    <h2>2. Tyre Model</h2>
    <div class="mermaid">
flowchart TD
    subgraph INPUTS[Inputs]
        FZ[Normal Force Fz<br/>from load transfer calculation]
        OMEGA[Wheel Angular Velocity ω<br/>from previous state]
        V[Vehicle Velocity v<br/>from previous state]
        R[Loaded Radius r<br/>from configuration]
    end

    subgraph SLIP_CALC[Slip Calculation]
        VWHEEL[Wheel Peripheral Velocity<br/>Vw = ω × r]
        SLIP[Slip Ratio<br/>κ = Vw - V / V]
    end

    subgraph FRICTION[Friction Model]
        MU_CALC[Friction Coefficient<br/>μ = f of κ]
        MU_MAX[Peak Friction μmax]
        K_OPT[Optimal Slip κopt]
    end

    subgraph FORCES[Force Outputs]
        FX[Longitudinal Force<br/>Fx = μ × Fz]
        FRR[Rolling Resistance<br/>Frr = Crr × Fz]
    end

    OMEGA --> VWHEEL
    R --> VWHEEL
    VWHEEL --> SLIP
    V --> SLIP
    
    SLIP --> MU_CALC
    MU_MAX --> MU_CALC
    K_OPT --> MU_CALC
    
    MU_CALC --> FX
    FZ --> FX
    FZ --> FRR
    </div>
    
    <h2>3. Aerodynamic Forces at Different Speeds</h2>
    <div class="mermaid">
flowchart LR
    subgraph LOW[Low Speed: 5 m/s]
        DRAG1[Drag: 12 N]
        DOWN1[Downforce: 15 N]
    end
    
    subgraph MED[Medium Speed: 15 m/s]
        DRAG2[Drag: 110 N]
        DOWN2[Downforce: 138 N]
    end
    
    subgraph HIGH[High Speed: 25 m/s]
        DRAG3[Drag: 306 N]
        DOWN3[Downforce: 383 N]
    end
    
    LOW --> MED --> HIGH
    </div>
    
    <h2>4. Powertrain Power Limiting Flow</h2>
    <div class="mermaid">
flowchart TD
    REQ[Requested Wheel Torque<br/>from control strategy] --> CONV1[Convert to Motor Torque<br/>Tm = Tw / Ng / η]
    CONV1 --> CURR[Calculate Motor Current<br/>I = Tm / Kt]
    CURR --> PWR[Calculate Electrical Power<br/>P = V × I]
    PWR --> CHECK{P > 80 kW?}
    CHECK --> |Yes| LIMIT[Limit Current<br/>Imax = 80000 / V]
    CHECK --> |No| PASS[Use Calculated Current]
    LIMIT --> RECALC[Recalculate Torque<br/>Tm = Imax × Kt]
    PASS --> OUT[Output Wheel Torque<br/>Tw = Tm × Ng × η]
    RECALC --> OUT
    </div>
    
    <h2>5. Simulation Results Summary</h2>
    <div class="mermaid">
flowchart LR
    subgraph RESULTS[Simulation Results]
        TIME[Time: 4.31 s]
        VMAX[Final Velocity: 28.4 m/s]
        PMAX[Peak Power: 80.0 kW]
        AMAX[Peak Acceleration: 12.1 m/s²]
    end
    
    subgraph COMPLIANCE[Rule Compliance]
        PWR_OK[Power Limit: PASS<br/>80 kW ≤ 80 kW]
        TIME_OK[Time Limit: PASS<br/>4.31 s < 25 s]
    end
    
    RESULTS --> COMPLIANCE
    </div>
    
    <script>
        mermaid.initialize({ startOnLoad: true, theme: 'default' });
    </script>
</body>
</html>
"""
    
    html_path = figures_dir / "view_diagrams.html"
    with open(html_path, 'w') as f:
        f.write(html_content)
    print(f"\nHTML viewer saved to {html_path}")
    print("Open this file in a browser to view and export diagrams as images.")


if __name__ == "__main__":
    print("=" * 60)
    print("Generating Logbook Figures")
    print("=" * 60)
    
    result = generate_simulation_plots()
    save_mermaid_diagrams()
    
    print("\n" + "=" * 60)
    print("Complete!")
    print("=" * 60)
    print(f"\nSimulation time: {result.final_time:.3f} s")
    print(f"Final velocity: {result.final_velocity:.2f} m/s")
    print(f"Power compliant: {result.power_compliant}")
    print(f"\nFigures saved to: figures/")
    print("  - velocity_vs_time.png")
    print("  - power_vs_time.png")
    print("  - acceleration_vs_time.png")
    print("  - forces_vs_time.png")
    print("  - normal_forces_vs_time.png")
    print("  - velocity_vs_position.png")
    print("  - tyre_friction_curve.png")
    print("  - comprehensive_results.png")
    print("\nMermaid diagrams:")
    print("  - figures/view_diagrams.html (open in browser to view/export)")
    print("  - figures/mermaid_src/*.mmd (source files)")
