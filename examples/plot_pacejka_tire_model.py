#!/usr/bin/env python3
"""
Generate comprehensive Pacejka tire model visualization.

Creates a 4-panel plot showing:
1. Force vs Slip at different loads (with true optimal slip markers)
2. Peak Force vs Load
3. Peak Friction Coefficient vs Load
4. Optimal Slip vs Load
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from config.vehicle_config import TireProperties
from vehicle.tire_model import TireModel, PacejkaTireModel, AVON_FSAE_COEFFICIENTS


def main():
    # Create tire model
    config = TireProperties(
        radius_loaded=0.2286,
        mass=3.0,
        mu_max=1.5,
        mu_slip_optimal=0.12,
        rolling_resistance_coeff=0.015,
        tire_model_type="pacejka"
    )
    tire_model = TireModel(config, use_pacejka=True)
    
    # Slip ratio range (0 to 40%)
    slip_ratios = np.linspace(0, 0.40, 200)
    
    # Load range for analysis
    loads = [500, 1000, 1500, 2000, 2500, 3000]
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(loads)))
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # =========================================================================
    # Panel 1: Force vs Slip at different loads
    # =========================================================================
    ax1 = axes[0, 0]
    
    for i, Fz in enumerate(loads):
        forces = []
        for slip in slip_ratios:
            fx, _ = tire_model.calculate_longitudinal_force(Fz, slip, 10.0)
            forces.append(fx)
        forces = np.array(forces)
        
        # Plot force curve
        ax1.plot(slip_ratios * 100, forces / 1000, color=colors[i], 
                 linewidth=2, label=f'Fz = {Fz} N')
        
        # Find and mark the TRUE peak using numerical search
        peak_idx = np.argmax(forces)
        peak_slip = slip_ratios[peak_idx]
        peak_force = forces[peak_idx]
        
        # Mark the peak with a dot
        ax1.plot(peak_slip * 100, peak_force / 1000, 'o', color=colors[i], 
                 markersize=8, markeredgecolor='black', markeredgewidth=1)
        
        # Add vertical line at optimal slip (only for first and last load)
        if i == 0 or i == len(loads) - 1:
            ax1.axvline(x=peak_slip * 100, color=colors[i], linestyle=':', 
                       alpha=0.5, linewidth=1)
    
    ax1.set_xlabel('Slip Ratio (%)', fontsize=11)
    ax1.set_ylabel('Longitudinal Force (kN)', fontsize=11)
    ax1.set_title('Force vs Slip Ratio at Different Loads', fontsize=12)
    ax1.legend(loc='lower right', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 40)
    ax1.set_ylim(0, None)
    
    # =========================================================================
    # Panel 2: Peak Force vs Load
    # =========================================================================
    ax2 = axes[0, 1]
    
    load_range = np.linspace(300, 3500, 50)
    peak_forces = []
    
    for Fz in load_range:
        # Compute force curve and find peak
        forces = [tire_model.calculate_longitudinal_force(Fz, slip, 10.0)[0] 
                  for slip in slip_ratios]
        peak_forces.append(max(forces))
    
    ax2.plot(load_range, np.array(peak_forces) / 1000, 'b-', linewidth=2)
    ax2.set_xlabel('Normal Force (N)', fontsize=11)
    ax2.set_ylabel('Peak Longitudinal Force (kN)', fontsize=11)
    ax2.set_title('Peak Force vs Load', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Add reference line for constant μ = 1.45 (nominal)
    ax2.plot(load_range, load_range * 1.45 / 1000, 'r--', alpha=0.5, 
             label='μ = 1.45 (nominal)')
    ax2.legend(fontsize=9)
    
    # =========================================================================
    # Panel 3: Peak Friction Coefficient vs Load
    # =========================================================================
    ax3 = axes[1, 0]
    
    mu_peaks = []
    for Fz in load_range:
        # Compute actual peak μ from force curve
        forces = [tire_model.calculate_longitudinal_force(Fz, slip, 10.0)[0] 
                  for slip in slip_ratios]
        peak_force = max(forces)
        mu_peaks.append(peak_force / Fz)
    
    ax3.plot(load_range, mu_peaks, 'b-', linewidth=2)
    ax3.set_xlabel('Normal Force (N)', fontsize=11)
    ax3.set_ylabel('Peak Friction Coefficient μ', fontsize=11)
    ax3.set_title('Load Sensitivity: μ Decreases with Load', fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    # Add reference lines
    ax3.axhline(y=AVON_FSAE_COEFFICIENTS.pDx1, color='r', linestyle='--', 
                alpha=0.5, label=f'pDx1 = {AVON_FSAE_COEFFICIENTS.pDx1}')
    ax3.axvline(x=AVON_FSAE_COEFFICIENTS.Fz0, color='g', linestyle=':', 
                alpha=0.5, label=f'Fz0 = {AVON_FSAE_COEFFICIENTS.Fz0} N')
    ax3.legend(fontsize=9)
    
    # =========================================================================
    # Panel 4: Optimal Slip vs Load
    # =========================================================================
    ax4 = axes[1, 1]
    
    optimal_slips = []
    for Fz in load_range:
        # Use the updated numerical method
        opt_slip = tire_model.get_optimal_slip_ratio(Fz)
        optimal_slips.append(opt_slip * 100)  # Convert to percentage
    
    ax4.plot(load_range, optimal_slips, 'b-', linewidth=2)
    ax4.set_xlabel('Normal Force (N)', fontsize=11)
    ax4.set_ylabel('Optimal Slip Ratio (%)', fontsize=11)
    ax4.set_title('Optimal Slip vs Load', fontsize=12)
    ax4.grid(True, alpha=0.3)
    
    # Add typical range annotation
    ax4.axhspan(8, 15, alpha=0.2, color='green', label='Typical range (8-15%)')
    ax4.legend(fontsize=9)
    ax4.set_ylim(0, 25)
    
    # =========================================================================
    # Final layout
    # =========================================================================
    fig.suptitle('Pacejka Magic Formula Tire Model (AVON FSAE Coefficients)', 
                 fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save figure
    out_path = package_root / 'figures' / 'pacejka_comprehensive.png'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Figure saved to: {out_path}")
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("Pacejka Model Summary")
    print("=" * 60)
    print(f"Coefficients: C={AVON_FSAE_COEFFICIENTS.C}, "
          f"pDx1={AVON_FSAE_COEFFICIENTS.pDx1}, "
          f"pDx2={AVON_FSAE_COEFFICIENTS.pDx2}")
    print(f"Nominal load Fz0: {AVON_FSAE_COEFFICIENTS.Fz0} N")
    print()
    
    # Show optimal slip at different loads
    print("Optimal slip ratio at different loads:")
    for Fz in [500, 1000, 1500, 2000, 2500, 3000]:
        opt_slip = tire_model.get_optimal_slip_ratio(Fz)
        mu_peak = tire_model.get_peak_friction_coefficient(Fz)
        print(f"  Fz = {Fz:4d} N: κ_opt = {opt_slip*100:5.1f}%, μ_peak = {mu_peak:.3f}")


if __name__ == "__main__":
    main()
