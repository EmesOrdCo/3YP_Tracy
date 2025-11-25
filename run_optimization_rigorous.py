#!/usr/bin/env python3
"""
Rigorous optimization runner - ensures proper package setup.

This script:
1. Verifies package is properly set up
2. Sets up Python path correctly
3. Runs optimization with proper error handling
"""

import sys
from pathlib import Path

# Get package root
PACKAGE_ROOT = Path(__file__).parent.resolve()

# Ensure package root is in Python path
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Verify package structure
required_modules = ['config', 'vehicle', 'dynamics', 'simulation', 'rules']
missing = [m for m in required_modules if not (PACKAGE_ROOT / m / '__init__.py').exists()]

if missing:
    print("ERROR: Package structure incomplete!")
    print(f"Missing modules: {missing}")
    print(f"Package root: {PACKAGE_ROOT}")
    print("\nPlease ensure you're running from the correct directory.")
    sys.exit(1)

# Try to import - this will work if package is installed or path is correct
try:
    from config.config_loader import load_config
    from simulation.multi_objective_optimizer import MultiObjectiveOptimizer
    print("✓ Package imports successful")
except ImportError as e:
    print("ERROR: Failed to import package modules")
    print(f"Error: {e}")
    print("\nTrying to install package...")
    import subprocess
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-e', str(PACKAGE_ROOT)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("✓ Package installed successfully")
        print("Please run this script again.")
        sys.exit(0)
    else:
        print("✗ Failed to install package automatically")
        print("Please run manually: pip install -e .")
        sys.exit(1)

# Now run the optimization
if __name__ == "__main__":
    from pathlib import Path
    
    print("=" * 70)
    print("FORMULA STUDENT ACCELERATION - OPTIMIZATION")
    print("=" * 70)
    
    # Load base config
    config_path = PACKAGE_ROOT / "config" / "vehicle_configs" / "base_vehicle.json"
    base_config = load_config(str(config_path))
    
    print(f"\nBase configuration:")
    print(f"  Mass: {base_config.mass.total_mass:.1f} kg")
    print(f"  CG X: {base_config.mass.cg_x:.3f} m")
    print(f"  CG Z: {base_config.mass.cg_z:.3f} m")
    print(f"  Gear ratio: {base_config.powertrain.gear_ratio:.2f}")
    
    # Define parameter bounds
    parameter_bounds = {
        'mass.cg_x': (0.8, 1.4),
        'mass.cg_z': (0.2, 0.4),
        'powertrain.gear_ratio': (8.0, 12.0),
        'control.target_slip_ratio': (0.10, 0.20),
    }
    
    print(f"\nOptimizing {len(parameter_bounds)} parameters...")
    print("Starting optimization (this may take several minutes)...\n")
    
    # Create optimizer
    optimizer = MultiObjectiveOptimizer(
        base_config=base_config,
        parameter_bounds=parameter_bounds,
        objective='minimize_time_with_rules',
        enforce_rules=True
    )
    
    # Run optimization
    try:
        result = optimizer.optimize(
            method='differential_evolution',
            max_iterations=30,
            population_size=20,
            verbose=True
        )
        
        # Display results
        print("\n" + "=" * 70)
        print("OPTIMIZATION RESULTS")
        print("=" * 70)
        
        print(f"\n✓ Best Time: {result.best_simulation_result.final_time:.3f} s")
        print(f"✓ Power Compliant: {result.best_simulation_result.power_compliant}")
        print(f"✓ Time Compliant: {result.best_simulation_result.time_compliant}")
        print(f"✓ Total Evaluations: {len(result.all_evaluations)}")
        
        print(f"\nOptimized Parameters:")
        print(f"  CG X: {result.best_config.mass.cg_x:.3f} m (was {base_config.mass.cg_x:.3f} m)")
        print(f"  CG Z: {result.best_config.mass.cg_z:.3f} m (was {base_config.mass.cg_z:.3f} m)")
        print(f"  Gear Ratio: {result.best_config.powertrain.gear_ratio:.2f} (was {base_config.powertrain.gear_ratio:.2f})")
        print(f"  Target Slip: {result.best_config.control.target_slip_ratio:.3f} (was {base_config.control.target_slip_ratio:.3f})")
        
        print("\n" + "=" * 70)
        print("Optimization complete!")
        
    except KeyboardInterrupt:
        print("\n\nOptimization interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR during optimization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

