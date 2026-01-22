"""Check wheelie limit and calculate safe CG positions."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from rules.wheelie_check import calculate_wheelie_limit_acceleration


def main():
    """Check wheelie limits for current configuration."""
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "vehicle_configs" / "base_vehicle.json"
    config = load_config(config_path)
    
    mass = config.mass.total_mass
    cg_x = config.mass.cg_x
    cg_z = config.mass.cg_z
    wheelbase = config.mass.wheelbase
    
    print("=" * 60)
    print("Wheelie Limit Analysis")
    print("=" * 60)
    print(f"\nCurrent Configuration:")
    print(f"  Mass: {mass:.1f} kg")
    print(f"  CG X (distance from front axle): {cg_x:.3f} m")
    print(f"  CG Z (height above ground): {cg_z:.3f} m")
    print(f"  Wheelbase: {wheelbase:.2f} m")
    
    # Calculate current wheelie limit acceleration
    max_accel = calculate_wheelie_limit_acceleration(
        mass, cg_x, cg_z, wheelbase, front_downforce=0.0
    )
    
    print(f"\n{'='*60}")
    print(f"Wheelie Limit Acceleration: {max_accel:.2f} m/s² ({max_accel/9.81:.2f} g)")
    
    if max_accel < 10.0:
        print("  ⚠️  WARNING: Very low wheelie limit - vehicle will wheelie easily!")
    elif max_accel < 20.0:
        print("  ⚠️  CAUTION: Low wheelie limit - may wheelie during hard acceleration")
    else:
        print("  ✓ Wheelie limit is reasonably high")
    
    # Calculate how much CG needs to move
    print(f"\n{'='*60}")
    print("To Fix Wheelie Issues:")
    print(f"{'='*60}")
    
    # Calculate required changes
    # Target: at least 25 m/s² (2.5g) before wheelie
    target_accel = 25.0  # m/s²
    
    # Option 1: Move CG forward (increase cg_x)
    # Formula: a = (front_static + front_downforce) * wheelbase / (m * cg_z)
    # Rearranging: front_static = a * m * cg_z / wheelbase
    # front_static = total_weight * (b / wheelbase) where b = wheelbase - cg_x
    # Solving for cg_x:
    g = 9.81
    total_weight = mass * g
    required_front_static = target_accel * mass * cg_z / wheelbase
    required_rear_distance = required_front_static / total_weight * wheelbase
    required_cg_x_forward = wheelbase - required_rear_distance
    
    print(f"\n1. Move CG Forward (increase cg_x):")
    print(f"   Current cg_x: {cg_x:.3f} m")
    print(f"   Required cg_x: {required_cg_x_forward:.3f} m")
    change_x = required_cg_x_forward - cg_x
    if change_x > 0:
        print(f"   Move CG forward by: +{change_x:.3f} m ({change_x*100:.1f} cm)")
    else:
        print(f"   Current CG position is already sufficient!")
    
    # Option 2: Lower CG (decrease cg_z)
    # Formula: a = (front_static + front_downforce) * wheelbase / (m * cg_z)
    # Rearranging: cg_z = (front_static + front_downforce) * wheelbase / (m * a)
    b = wheelbase - cg_x
    front_static = total_weight * (b / wheelbase)
    required_cg_z_lower = front_static * wheelbase / (mass * target_accel)
    
    print(f"\n2. Lower CG (decrease cg_z):")
    print(f"   Current cg_z: {cg_z:.3f} m")
    print(f"   Required cg_z: {required_cg_z_lower:.3f} m")
    change_z = cg_z - required_cg_z_lower
    if change_z > 0:
        print(f"   Lower CG by: -{change_z:.3f} m ({change_z*100:.1f} cm)")
    else:
        print(f"   Current CG height is already sufficient!")
    
    # Option 3: Combination
    print(f"\n3. Recommended: Combine both adjustments")
    print(f"   - Move CG forward by ~{abs(change_x)/2:.3f} m ({abs(change_x)/2*100:.1f} cm)")
    print(f"   - Lower CG by ~{abs(change_z)/2:.3f} m ({abs(change_z)/2*100:.1f} cm)")
    
    print(f"\n{'='*60}")
    print("How Wheelie Occurs:")
    print(f"{'='*60}")
    print("During acceleration, load transfers from front to rear wheels.")
    print("Front normal force = Static load - Load transfer + Downforce")
    print("Load transfer = (mass × acceleration × CG_height) / wheelbase")
    print("\nTo prevent wheelie:")
    print("  • Move CG forward → more weight on front wheels initially")
    print("  • Lower CG → less load transfer during acceleration")
    print("  • Both combined = most effective solution")
    
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()


