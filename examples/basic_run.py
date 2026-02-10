"""Basic acceleration simulation example."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import load_config
from simulation.acceleration_sim import AccelerationSimulation


def main():
    """Run basic acceleration simulation."""
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "vehicle_configs" / "base_vehicle.json"
    config = load_config(config_path)
    
    print("=" * 60)
    print("Formula Student Acceleration Simulation")
    print("=" * 60)
    print(f"\nVehicle Configuration:")
    print(f"  Mass: {config.mass.total_mass:.1f} kg")
    print(f"  CG Position: ({config.mass.cg_x:.2f}, {config.mass.cg_z:.2f}) m")
    print(f"  Wheelbase: {config.mass.wheelbase:.2f} m")
    print(f"  Max Power: {config.powertrain.max_power_accumulator_outlet/1000:.1f} kW")
    print(f"  Gear Ratio: {config.powertrain.gear_ratio:.1f}")
    print(f"  Tire Radius: {config.tires.radius_loaded*1000:.1f} mm")
    print(f"  Tire μ: {config.tires.mu_max:.2f}")
    
    # Create simulation
    sim = AccelerationSimulation(config)
    
    # Run simulation
    print("\nRunning simulation...")
    result = sim.run(fastest_time=4.5)  # Assume 4.5s is fastest time
    
    # Print results
    print("\n" + "=" * 60)
    print("Simulation Results")
    print("=" * 60)
    print(f"  Final Time: {result.final_time:.3f} s")
    print(f"  Final Distance: {result.final_distance:.2f} m")
    print(f"  Final Velocity: {result.final_velocity:.1f} m/s ({result.final_velocity*3.6:.1f} km/h)")
    print(f"  Max Power Used: {result.max_power_used/1000:.2f} kW")
    print(f"  Power Compliant: {'✓' if result.power_compliant else '✗'}")
    print(f"  Time Compliant: {'✓' if result.time_compliant else '✗'}")
    print(f"  Overall Compliant: {'✓' if result.compliant else '✗'}")
    print(f"  Wheelie Detected: {'⚠️ YES' if result.wheelie_detected else '✓ NO'}")
    if result.wheelie_detected:
        print(f"  Min Front Normal Force: {result.min_front_normal_force:.2f} N (threshold: 0.10 N)")
    
    if result.score is not None:
        print(f"  Score: {result.score:.2f} points")
    
    # Print warnings if not compliant or if wheelie detected
    if not result.compliant or result.wheelie_detected:
        print("\n⚠️  WARNINGS:")
        if not result.power_compliant:
            print(f"   - Power limit exceeded: {result.max_power_used/1000:.2f} kW > 80 kW")
        if not result.time_compliant:
            print(f"   - Time limit exceeded: {result.final_time:.2f} s > 25.0 s")
        if result.wheelie_detected:
            print(f"   - WHEELIE DETECTED: Front wheels lifted off at {result.wheelie_time:.3f} s")
            print(f"     Minimum front normal force: {result.min_front_normal_force:.2f} N (threshold: 0.10 N)")
            print(f"     ⚠️  Loss of front wheel traction and steering control!")
            print(f"     Fix: Increase cg_x (move CG forward) or decrease cg_z (lower CG)")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()


