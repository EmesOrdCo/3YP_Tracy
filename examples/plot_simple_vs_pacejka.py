#!/usr/bin/env python3
"""
Generate comparison plot: Simple vs Pacejka tire model.

Creates a 4-panel plot showing:
1. Simple vs Pacejka force curves at nominal load
2. Pacejka force vs slip at different loads
3. Load sensitivity: Peak μ vs vertical load
4. Optimal slip ratio vs vertical load
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.vehicle_config import TireProperties
from vehicle.tire_model import TireModel, SimpleTireModel, AVON_FSAE_COEFFICIENTS


def main():
    # Create tire configurations
    config = TireProperties(
        radius_loaded=0.2286,
        mass=3.0,
        mu_max=1.5,
        mu_slip_optimal=0.12,
        rolling_resistance_coeff=0.015,
        tire_model_type="pacejka"
    )
    
    # Create both models
    simple_model = TireModel(config, use_pacejka=False)
    pacejka_model = TireModel(config, use_pacejka=True)
    
    # Slip ratio range (0 to 40%)
    slip_ratios = np.linspace(0, 0.40, 200)
    
    # Load range for analysis
    loads_panel2 = [1000, 1500, 2000, 2500, 3000]
    colors_panel2 = plt.cm.viridis(np.linspace(0.2, 0.9, len(loads_panel2)))
    
    # Extended load range for panels 3 and 4
    load_range = np.linspace(500, 4000, 50)
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # =========================================================================
    # Panel 1: Simple vs Pacejka at nominal load (Fz = 1500 N)
    # =========================================================================
    ax1 = axes[0, 0]
    Fz_nominal = 1500.0
    
    # Simple model forces
    simple_forces = []
    for slip in slip_ratios:
        fx, _ = simple_model.calculate_longitudinal_force(Fz_nominal, slip, 10.0)
        simple_forces.append(fx)
    simple_forces = np.array(simple_forces)
    
    # Pacejka model forces
    pacejka_forces = []
    for slip in slip_ratios:
        fx, _ = pacejka_model.calculate_longitudinal_force(Fz_nominal, slip, 10.0)
        pacejka_forces.append(fx)
    pacejka_forces = np.array(pacejka_forces)
    
    # Plot curves
    ax1.plot(slip_ratios * 100, simple_forces / 1000, 'b--', linewidth=2.5, 
             label='Simple Model')
    ax1.plot(slip_ratios * 100, pacejka_forces / 1000, 'r-', linewidth=2.5, 
             label='Pacejka Model')
    
    # Find and mark optimal slip for each model
    simple_opt_idx = np.argmax(simple_forces)
    simple_opt_slip = slip_ratios[simple_opt_idx]
    
    pacejka_opt_idx = np.argmax(pacejka_forces)
    pacejka_opt_slip = slip_ratios[pacejka_opt_idx]
    
    # Vertical lines at optimal slip
    ax1.axvline(x=simple_opt_slip * 100, color='blue', linestyle=':', alpha=0.7,
                label=f'Simple optimal ({simple_opt_slip*100:.0f}%)')
    ax1.axvline(x=pacejka_opt_slip * 100, color='red', linestyle=':', alpha=0.7,
                label=f'Pacejka optimal (~{pacejka_opt_slip*100:.0f}%)')
    
    ax1.set_xlabel('Slip Ratio (%)', fontsize=11)
    ax1.set_ylabel('Longitudinal Force (kN)', fontsize=11)
    ax1.set_title(f'Simple vs Pacejka Model\n(Fz = {Fz_nominal:.0f} N)', fontsize=12)
    ax1.legend(loc='lower right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 40)
    ax1.set_ylim(0, 2.5)
    
    # =========================================================================
    # Panel 2: Pacejka Force vs Slip at Different Loads
    # =========================================================================
    ax2 = axes[0, 1]
    
    for i, Fz in enumerate(loads_panel2):
        forces = []
        for slip in slip_ratios:
            fx, _ = pacejka_model.calculate_longitudinal_force(Fz, slip, 10.0)
            forces.append(fx)
        forces = np.array(forces)
        
        ax2.plot(slip_ratios * 100, forces / 1000, color=colors_panel2[i], 
                 linewidth=2, label=f'Fz = {Fz} N')
    
    ax2.set_xlabel('Slip Ratio (%)', fontsize=11)
    ax2.set_ylabel('Longitudinal Force (kN)', fontsize=11)
    ax2.set_title('Pacejka Model: Force vs Slip at Different Loads', fontsize=12)
    ax2.legend(loc='lower right', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 40)
    ax2.set_ylim(0, 4.5)
    
    # =========================================================================
    # Panel 3: Load Sensitivity - Peak μ vs Vertical Load
    # =========================================================================
    ax3 = axes[1, 0]
    
    # Simple model: constant μ
    simple_mu = np.ones_like(load_range) * config.mu_max
    
    # Pacejka model: load-sensitive μ
    pacejka_mu = []
    for Fz in load_range:
        forces = [pacejka_model.calculate_longitudinal_force(Fz, slip, 10.0)[0] 
                  for slip in slip_ratios]
        peak_force = max(forces)
        pacejka_mu.append(peak_force / Fz)
    pacejka_mu = np.array(pacejka_mu)
    
    # Plot
    ax3.plot(load_range, simple_mu, 'b--', linewidth=2.5, 
             label='Simple Model (constant)')
    ax3.plot(load_range, pacejka_mu, 'r-', linewidth=2.5, 
             label='Pacejka Model (load sensitive)')
    
    # Fill the difference region
    ax3.fill_between(load_range, simple_mu, pacejka_mu, 
                     where=(pacejka_mu < simple_mu), alpha=0.3, color='red',
                     label='Difference')
    
    # Add typical rear tire load region
    ax3.axvspan(1500, 2500, alpha=0.2, color='green', label='Typical rear tire\nload during accel')
    
    ax3.set_xlabel('Vertical Load Fz (N)', fontsize=11)
    ax3.set_ylabel('Peak Friction Coefficient μ', fontsize=11)
    ax3.set_title('Load Sensitivity: Peak μ vs Vertical Load', fontsize=12)
    ax3.legend(loc='lower left', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(500, 4000)
    ax3.set_ylim(1.0, 1.7)
    
    # =========================================================================
    # Panel 4: Optimal Slip Ratio vs Vertical Load
    # =========================================================================
    ax4 = axes[1, 1]
    
    # Simple model: fixed optimal slip
    simple_opt = np.ones_like(load_range) * config.mu_slip_optimal * 100  # Convert to %
    
    # Pacejka model: compute optimal slip at each load
    pacejka_opt = []
    for Fz in load_range:
        opt_slip = pacejka_model.get_optimal_slip_ratio(Fz)
        pacejka_opt.append(opt_slip * 100)  # Convert to %
    pacejka_opt = np.array(pacejka_opt)
    
    # Plot
    ax4.plot(load_range, simple_opt, 'b--', linewidth=2.5, 
             label='Simple Model (fixed 12%)')
    ax4.plot(load_range, pacejka_opt, 'r-', linewidth=2.5, 
             label='Pacejka Model')
    
    ax4.set_xlabel('Vertical Load Fz (N)', fontsize=11)
    ax4.set_ylabel('Optimal Slip Ratio (%)', fontsize=11)
    ax4.set_title('Optimal Slip Ratio vs Vertical Load', fontsize=12)
    ax4.legend(loc='upper right', fontsize=9)
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(500, 4000)
    ax4.set_ylim(0, 25)
    
    # =========================================================================
    # Final layout
    # =========================================================================
    plt.tight_layout()
    
    # Save figure
    out_path = package_root / 'figures' / 'simple_vs_pacejka.png'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Figure saved to: {out_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Model Comparison Summary")
    print("=" * 60)
    print(f"\nAt nominal load (Fz = {Fz_nominal:.0f} N):")
    print(f"  Simple model optimal slip: {simple_opt_slip*100:.1f}%")
    print(f"  Pacejka model optimal slip: {pacejka_opt_slip*100:.1f}%")
    print(f"\nPacejka optimal slip across loads:")
    for Fz in [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]:
        opt = pacejka_model.get_optimal_slip_ratio(Fz)
        mu = pacejka_model.get_peak_friction_coefficient(Fz)
        print(f"  Fz = {Fz:4d} N: κ_opt = {opt*100:5.1f}%, μ_peak = {mu:.3f}")


if __name__ == "__main__":
    main()
