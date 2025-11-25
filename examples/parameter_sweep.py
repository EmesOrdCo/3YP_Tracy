"""Parameter sweep example."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from simulation.batch_runner import BatchRunner
from analysis.visualization import plot_comparison
import numpy as np


def main():
    """Run parameter sweep example."""
    # Load base configuration
    config_path = Path(__file__).parent.parent / "config" / "vehicle_configs" / "base_vehicle.json"
    base_config = load_config(config_path)
    
    print("=" * 60)
    print("Parameter Sweep Example")
    print("=" * 60)
    
    # Create batch runner
    runner = BatchRunner(base_config, parallel=True)
    
    # Define parameter sweep: vary gear ratio
    gear_ratios = np.linspace(8.0, 12.0, 5).tolist()
    print(f"\nSweeping gear ratio: {gear_ratios}")
    
    # Run sweep
    results = runner.parameter_sweep(
        'powertrain.gear_ratio',
        gear_ratios,
        fastest_time=4.5
    )
    
    # Print results
    print("\nResults:")
    labels = [f"Gear={gr:.1f}" for gr in gear_ratios]
    for label, result in zip(labels, results):
        print(f"{label:15s}: Time={result.final_time:.3f}s, "
              f"Score={result.score:.2f if result.score else 0.0:.2f} pts, "
              f"Compliant={'✓' if result.compliant else '✗'}")
    
    # Plot comparison
    state_histories = []
    for result in results:
        # Get state history from solver (would need to access from result)
        # For now, just demonstrate the plotting structure
        pass
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

