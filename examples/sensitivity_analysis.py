"""Sensitivity analysis example."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from analysis.sensitivity import (
    one_at_a_time_sensitivity,
    rank_sensitivities,
    sensitivity_to_dataframe
)
import numpy as np


def main():
    """Run sensitivity analysis example."""
    # Load base configuration
    config_path = Path(__file__).parent.parent / "config" / "vehicle_configs" / "base_vehicle.json"
    base_config = load_config(config_path)
    
    print("=" * 60)
    print("Sensitivity Analysis Example")
    print("=" * 60)
    
    # Define parameter ranges to test
    parameter_ranges = {
        'mass.total_mass': (200.0, 300.0),  # ±20% around 250kg
        'powertrain.gear_ratio': (8.0, 12.0),  # ±20% around 10.0
        'tires.mu_max': (1.2, 1.8),  # ±20% around 1.5
        'powertrain.max_power_accumulator_outlet': (70000.0, 80000.0),  # Up to limit
    }
    
    print("\nAnalyzing parameter sensitivities...")
    print("Parameters:", list(parameter_ranges.keys()))
    
    # Run sensitivity analysis
    sensitivity_results = one_at_a_time_sensitivity(
        base_config,
        parameter_ranges,
        n_points=5,
        fastest_time=4.5,
        output_metric='final_time'
    )
    
    # Create summary table
    df = sensitivity_to_dataframe(sensitivity_results)
    print("\nSensitivity Summary:")
    print(df.to_string(index=False))
    
    # Rank by sensitivity
    ranked = rank_sensitivities(sensitivity_results, output_metric='final_time')
    print("\nRanked by Sensitivity:")
    print(ranked.to_string(index=False))
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

