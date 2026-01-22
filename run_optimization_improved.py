#!/usr/bin/env python3
"""
IMPROVED VEHICLE OPTIMIZATION SCRIPT
=====================================

This script implements a rigorous optimization approach that separates parameters into:

1. MINIMIZE: Parameters where lower is always better (set to practical limits)
2. MAXIMIZE: Parameters where higher is always better (set to practical limits)  
3. OPTIMIZE: Parameters with genuine trade-offs (found by optimizer)
4. FIXED: Parameters constrained by rules or component selection

Key improvement: CG position is optimized as a RATIO of wheelbase (0.6-0.95),
ensuring the optimizer explores wheelbase and weight distribution together properly.

Author: Formula Student Acceleration Simulation
"""

import sys
import json
import copy
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List, Any

import numpy as np
from scipy.optimize import differential_evolution

# Setup path for imports
PACKAGE_ROOT = Path(__file__).parent.resolve()
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from config.config_loader import load_config
from config.vehicle_config import VehicleConfig
from simulation.acceleration_sim import AccelerationSimulation, SimulationResult


# =============================================================================
# PARAMETER CLASSIFICATION
# =============================================================================

# MINIMIZE: Lower is always better for acceleration
# These are set to practical/achievable lower bounds
MINIMIZE_PARAMS = {
    'mass.total_mass': 175.0,              # kg - realistic minimum for FS EV
    'mass.cg_z': 0.22,                     # m - low but achievable with packaging
    'mass.unsprung_mass_front': 10.0,      # kg - lightweight uprights/hubs
    'mass.unsprung_mass_rear': 10.0,       # kg - lightweight uprights/hubs
    'mass.i_pitch': 120.0,                 # kg·m² - optimized mass distribution
    'tires.rolling_resistance_coeff': 0.010,  # - low rolling resistance slicks
    'powertrain.battery_internal_resistance': 0.008,  # Ω - quality cells
    'powertrain.wheel_inertia': 0.05,      # kg·m² - lightweight wheels
    'aerodynamics.cda': 0.55,              # m² - streamlined body, no wings
}

# MAXIMIZE: Higher is always better for acceleration  
# These are set to practical/achievable upper bounds
MAXIMIZE_PARAMS = {
    'tires.mu_max': 1.8,                   # - best slick compound (Hoosier R25B)
    'powertrain.motor_efficiency': 0.96,   # - high quality motor
    'powertrain.drivetrain_efficiency': 0.97,  # - single stage reduction, quality bearings
}

# FIXED: Constrained by rules, component selection, or no aero package
FIXED_PARAMS = {
    # Rules (FS 2025)
    'powertrain.max_power_accumulator_outlet': 80000.0,  # W - EV 2.2 rule
    'simulation.target_distance': 75.0,    # m - acceleration event distance
    
    # No aero package
    'aerodynamics.cl_front': 0.0,
    'aerodynamics.cl_rear': 0.0,
    
    # Motor/battery (placeholders - update when specs available)
    'powertrain.motor_torque_constant': 0.5,   # N·m/A
    'powertrain.motor_max_current': 200.0,     # A
    'powertrain.motor_max_speed': 1000.0,      # rad/s
    'powertrain.battery_voltage_nominal': 300.0,  # V
    'powertrain.battery_max_current': 300.0,   # A
    'powertrain.differential_ratio': 1.0,
    
    # Environment (standard conditions)
    'environment.air_density': 1.225,
    'environment.ambient_temperature': 20.0,
    'environment.track_grade': 0.0,
    'environment.wind_speed': 0.0,
    'environment.surface_mu_scaling': 1.0,
    
    # Chassis geometry (will be set by optimizer for wheelbase, track derived)
    'mass.front_track': 1.2,               # m
    'mass.rear_track': 1.2,                # m
    'mass.i_yaw': 100.0,                   # kg·m² - not critical for straight line
    
    # Tire mass (fixed once tire selected)
    'tires.mass': 3.0,                     # kg per tire
    
    # Suspension (low impact on straight line)
    'suspension.ride_height_front': 0.05,  # m
    'suspension.ride_height_rear': 0.05,   # m
    'suspension.wheel_rate_front': 35000.0,  # N/m
    'suspension.wheel_rate_rear': 35000.0,   # N/m
    
    # Control
    'control.torque_ramp_rate': 1000.0,    # N·m/s
    'control.traction_control_enabled': True,
    
    # Simulation settings
    'simulation.dt': 0.001,
    'simulation.max_time': 30.0,
}

# OPTIMIZE: Parameters with genuine trade-offs
# Format: (min_bound, max_bound, description)
OPTIMIZE_PARAMS = {
    'wheelbase': (1.525, 2.0, 'Wheelbase [m] - min 1.525m per FS rules'),
    'cg_x_ratio': (0.60, 0.95, 'CG position as ratio of wheelbase (0=front, 1=rear)'),
    'gear_ratio': (8.0, 14.0, 'Final drive gear ratio'),
    'radius_loaded': (0.200, 0.280, 'Tire loaded radius [m] (10" to 13" wheels)'),
    'target_slip_ratio': (0.08, 0.20, 'Traction control target slip ratio'),
    'mu_slip_optimal': (0.08, 0.20, 'Tire optimal slip ratio (should match target)'),
    'launch_torque_limit': (400.0, 1500.0, 'Launch torque limit [N·m at wheel]'),
    'anti_squat_ratio': (0.0, 0.6, 'Anti-squat geometry ratio'),
}


# =============================================================================
# OPTIMIZER CLASS
# =============================================================================

@dataclass
class OptimizationResult:
    """Results from the optimization."""
    best_config: VehicleConfig
    best_result: SimulationResult
    best_time: float
    optimized_params: Dict[str, float]
    n_evaluations: int
    elapsed_time: float
    convergence_history: List[float]


class ImprovedOptimizer:
    """
    Improved optimizer that properly handles parameter classification.
    
    Key features:
    - CG position optimized as ratio of wheelbase
    - Clear separation of monotonic vs trade-off parameters
    - Constraint handling for rules compliance
    """
    
    def __init__(self, base_config: VehicleConfig):
        self.base_config = base_config
        self.n_evaluations = 0
        self.best_time = float('inf')
        self.convergence_history = []
        
    def _apply_fixed_params(self, config: VehicleConfig) -> VehicleConfig:
        """Apply all fixed parameter values."""
        for param_path, value in FIXED_PARAMS.items():
            self._set_param(config, param_path, value)
        return config
    
    def _apply_minimize_params(self, config: VehicleConfig) -> VehicleConfig:
        """Apply minimize parameter values (practical lower bounds)."""
        for param_path, value in MINIMIZE_PARAMS.items():
            self._set_param(config, param_path, value)
        return config
    
    def _apply_maximize_params(self, config: VehicleConfig) -> VehicleConfig:
        """Apply maximize parameter values (practical upper bounds)."""
        for param_path, value in MAXIMIZE_PARAMS.items():
            self._set_param(config, param_path, value)
        return config
    
    def _set_param(self, config: VehicleConfig, param_path: str, value: Any):
        """Set a parameter value using dot notation."""
        parts = param_path.split('.')
        if len(parts) == 2:
            category, param = parts
            obj = getattr(config, category, None)
            if obj is not None:
                setattr(obj, param, value)
        elif len(parts) == 1:
            # Direct attribute on config (like dt, max_time)
            if hasattr(config, param_path):
                setattr(config, param_path, value)
    
    def _vector_to_config(self, x: np.ndarray) -> VehicleConfig:
        """
        Convert optimizer vector to vehicle configuration.
        
        Vector layout:
        [0] wheelbase
        [1] cg_x_ratio (CG position as ratio of wheelbase)
        [2] gear_ratio
        [3] radius_loaded
        [4] target_slip_ratio
        [5] mu_slip_optimal
        [6] launch_torque_limit
        [7] anti_squat_ratio
        """
        config = copy.deepcopy(self.base_config)
        
        # Apply fixed, minimize, maximize params first
        config = self._apply_fixed_params(config)
        config = self._apply_minimize_params(config)
        config = self._apply_maximize_params(config)
        
        # Apply optimized params
        wheelbase = x[0]
        cg_x_ratio = x[1]
        gear_ratio = x[2]
        radius_loaded = x[3]
        target_slip_ratio = x[4]
        mu_slip_optimal = x[5]
        launch_torque_limit = x[6]
        anti_squat_ratio = x[7]
        
        # Calculate absolute CG position from ratio
        cg_x = cg_x_ratio * wheelbase
        
        # Set values
        config.mass.wheelbase = wheelbase
        config.mass.cg_x = cg_x
        config.powertrain.gear_ratio = gear_ratio
        config.tires.radius_loaded = radius_loaded
        config.tires.mu_slip_optimal = mu_slip_optimal
        config.control.target_slip_ratio = target_slip_ratio
        config.control.launch_torque_limit = launch_torque_limit
        config.suspension.anti_squat_ratio = anti_squat_ratio
        
        return config
    
    def _objective(self, x: np.ndarray) -> float:
        """
        Objective function: minimize acceleration time.
        
        Returns large penalty for invalid/non-compliant configurations.
        """
        try:
            config = self._vector_to_config(x)
            
            # Validate configuration
            errors = config.validate()
            if errors:
                return 1e6 + len(errors) * 1e4
            
            # Run simulation
            sim = AccelerationSimulation(config)
            result = sim.run()
            
            self.n_evaluations += 1
            
            # Penalty for rule violations
            penalty = 0.0
            if not result.power_compliant:
                penalty += 1e5
            if not result.time_compliant:
                penalty += 1e4
            if result.wheelie_detected:
                penalty += 1e3  # Penalize wheelies
            
            obj_value = result.final_time + penalty
            
            # Track best
            if obj_value < self.best_time:
                self.best_time = obj_value
                self.convergence_history.append(obj_value)
            
            return obj_value
            
        except Exception as e:
            return 1e6
    
    def optimize(
        self,
        max_iterations: int = 50,
        population_size: int = 30,
        verbose: bool = True
    ) -> OptimizationResult:
        """
        Run optimization to find best configuration.
        
        Args:
            max_iterations: Maximum generations for differential evolution
            population_size: Population size (more = better exploration, slower)
            verbose: Print progress updates
            
        Returns:
            OptimizationResult with best configuration and statistics
        """
        # Build bounds list
        bounds = [
            OPTIMIZE_PARAMS['wheelbase'][:2],
            OPTIMIZE_PARAMS['cg_x_ratio'][:2],
            OPTIMIZE_PARAMS['gear_ratio'][:2],
            OPTIMIZE_PARAMS['radius_loaded'][:2],
            OPTIMIZE_PARAMS['target_slip_ratio'][:2],
            OPTIMIZE_PARAMS['mu_slip_optimal'][:2],
            OPTIMIZE_PARAMS['launch_torque_limit'][:2],
            OPTIMIZE_PARAMS['anti_squat_ratio'][:2],
        ]
        
        if verbose:
            print("=" * 70)
            print("IMPROVED VEHICLE OPTIMIZATION")
            print("=" * 70)
            print(f"\nOptimizing {len(bounds)} parameters with trade-offs:")
            for name, (lo, hi, desc) in OPTIMIZE_PARAMS.items():
                print(f"  • {name}: [{lo}, {hi}] - {desc}")
            print(f"\nSettings: {max_iterations} iterations × {population_size} population")
            print(f"Estimated evaluations: ~{max_iterations * population_size * 10}")
            print("\nStarting optimization...\n")
        
        start_time = time.time()
        self.n_evaluations = 0
        self.best_time = float('inf')
        self.convergence_history = []
        
        # Callback for progress
        def callback(xk, convergence):
            if verbose:
                print(f"  Generation complete | Best time: {self.best_time:.4f}s | "
                      f"Evaluations: {self.n_evaluations}", flush=True)
        
        # Run differential evolution
        result = differential_evolution(
            self._objective,
            bounds,
            maxiter=max_iterations,
            popsize=population_size,
            workers=1,  # Avoid multiprocessing issues
            updating='deferred',
            callback=callback,
            seed=42,  # Reproducibility
            atol=0.001,
            tol=0.001,
        )
        
        elapsed = time.time() - start_time
        
        # Get best configuration
        best_config = self._vector_to_config(result.x)
        
        # Run final simulation for complete results
        sim = AccelerationSimulation(best_config)
        best_result = sim.run()
        
        # Extract optimized parameter values
        optimized_params = {
            'wheelbase': result.x[0],
            'cg_x_ratio': result.x[1],
            'cg_x': result.x[1] * result.x[0],  # Absolute CG position
            'gear_ratio': result.x[2],
            'radius_loaded': result.x[3],
            'target_slip_ratio': result.x[4],
            'mu_slip_optimal': result.x[5],
            'launch_torque_limit': result.x[6],
            'anti_squat_ratio': result.x[7],
        }
        
        return OptimizationResult(
            best_config=best_config,
            best_result=best_result,
            best_time=best_result.final_time,
            optimized_params=optimized_params,
            n_evaluations=self.n_evaluations,
            elapsed_time=elapsed,
            convergence_history=self.convergence_history,
        )


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def save_config(config: VehicleConfig, filepath: Path):
    """Save configuration to JSON file."""
    config_dict = {
        'mass': {
            'total_mass': config.mass.total_mass,
            'cg_x': config.mass.cg_x,
            'cg_z': config.mass.cg_z,
            'wheelbase': config.mass.wheelbase,
            'front_track': config.mass.front_track,
            'rear_track': config.mass.rear_track,
            'i_yaw': config.mass.i_yaw,
            'i_pitch': config.mass.i_pitch,
            'unsprung_mass_front': config.mass.unsprung_mass_front,
            'unsprung_mass_rear': config.mass.unsprung_mass_rear,
        },
        'tires': {
            'radius_loaded': config.tires.radius_loaded,
            'mass': config.tires.mass,
            'mu_max': config.tires.mu_max,
            'mu_slip_optimal': config.tires.mu_slip_optimal,
            'rolling_resistance_coeff': config.tires.rolling_resistance_coeff,
        },
        'powertrain': {
            'motor_torque_constant': config.powertrain.motor_torque_constant,
            'motor_max_current': config.powertrain.motor_max_current,
            'motor_max_speed': config.powertrain.motor_max_speed,
            'motor_efficiency': config.powertrain.motor_efficiency,
            'battery_voltage_nominal': config.powertrain.battery_voltage_nominal,
            'battery_internal_resistance': config.powertrain.battery_internal_resistance,
            'battery_max_current': config.powertrain.battery_max_current,
            'gear_ratio': config.powertrain.gear_ratio,
            'drivetrain_efficiency': config.powertrain.drivetrain_efficiency,
            'differential_ratio': config.powertrain.differential_ratio,
            'max_power_accumulator_outlet': config.powertrain.max_power_accumulator_outlet,
            'wheel_inertia': config.powertrain.wheel_inertia,
        },
        'aerodynamics': {
            'cda': config.aerodynamics.cda,
            'cl_front': config.aerodynamics.cl_front,
            'cl_rear': config.aerodynamics.cl_rear,
            'air_density': config.aerodynamics.air_density,
        },
        'suspension': {
            'anti_squat_ratio': config.suspension.anti_squat_ratio,
            'ride_height_front': config.suspension.ride_height_front,
            'ride_height_rear': config.suspension.ride_height_rear,
            'wheel_rate_front': config.suspension.wheel_rate_front,
            'wheel_rate_rear': config.suspension.wheel_rate_rear,
        },
        'control': {
            'launch_torque_limit': config.control.launch_torque_limit,
            'target_slip_ratio': config.control.target_slip_ratio,
            'torque_ramp_rate': config.control.torque_ramp_rate,
            'traction_control_enabled': config.control.traction_control_enabled,
        },
        'environment': {
            'air_density': config.environment.air_density,
            'ambient_temperature': config.environment.ambient_temperature,
            'track_grade': config.environment.track_grade,
            'wind_speed': config.environment.wind_speed,
            'surface_mu_scaling': config.environment.surface_mu_scaling,
        },
        'simulation': {
            'dt': config.dt,
            'max_time': config.max_time,
            'target_distance': config.target_distance,
        },
    }
    
    with open(filepath, 'w') as f:
        json.dump(config_dict, f, indent=2)


def main():
    """Main optimization routine."""
    
    print("=" * 70)
    print("FORMULA STUDENT ACCELERATION - IMPROVED OPTIMIZATION")
    print("=" * 70)
    print()
    
    # Load base config
    config_path = PACKAGE_ROOT / "config" / "vehicle_configs" / "base_vehicle.json"
    base_config = load_config(str(config_path))
    
    print("Parameter Classification:")
    print("-" * 70)
    print(f"  MINIMIZE parameters: {len(MINIMIZE_PARAMS)} (set to practical lower bounds)")
    print(f"  MAXIMIZE parameters: {len(MAXIMIZE_PARAMS)} (set to practical upper bounds)")
    print(f"  FIXED parameters:    {len(FIXED_PARAMS)} (rules/components)")
    print(f"  OPTIMIZE parameters: {len(OPTIMIZE_PARAMS)} (trade-offs - optimizer finds optimal)")
    print()
    
    # Create optimizer
    optimizer = ImprovedOptimizer(base_config)
    
    # Run optimization
    result = optimizer.optimize(
        max_iterations=50,
        population_size=30,
        verbose=True
    )
    
    # Display results
    print()
    print("=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)
    
    print(f"\n✓ Best Time: {result.best_time:.4f} seconds")
    print(f"✓ Final Velocity: {result.best_result.final_velocity:.2f} m/s "
          f"({result.best_result.final_velocity * 3.6:.1f} km/h)")
    print(f"✓ Power Compliant: {result.best_result.power_compliant}")
    print(f"✓ Wheelie Detected: {result.best_result.wheelie_detected}")
    print(f"✓ Total Evaluations: {result.n_evaluations}")
    print(f"✓ Optimization Time: {result.elapsed_time:.1f} seconds")
    
    print("\n" + "=" * 70)
    print("OPTIMIZED PARAMETERS (Trade-off parameters)")
    print("=" * 70)
    
    params = result.optimized_params
    print(f"\n  Chassis Geometry:")
    print(f"    Wheelbase:           {params['wheelbase']:.4f} m")
    print(f"    CG X (absolute):     {params['cg_x']:.4f} m from front axle")
    print(f"    CG X (ratio):        {params['cg_x_ratio']:.2%} of wheelbase (rearward)")
    
    print(f"\n  Powertrain:")
    print(f"    Gear Ratio:          {params['gear_ratio']:.3f}")
    
    print(f"\n  Tires:")
    print(f"    Loaded Radius:       {params['radius_loaded']:.4f} m ({params['radius_loaded']*1000:.1f} mm)")
    print(f"    Optimal Slip Ratio:  {params['mu_slip_optimal']:.4f}")
    
    print(f"\n  Control Strategy:")
    print(f"    Target Slip Ratio:   {params['target_slip_ratio']:.4f}")
    print(f"    Launch Torque Limit: {params['launch_torque_limit']:.1f} N·m")
    
    print(f"\n  Suspension:")
    print(f"    Anti-Squat Ratio:    {params['anti_squat_ratio']:.4f}")
    
    print("\n" + "=" * 70)
    print("ENGINEERING RECOMMENDATIONS")
    print("=" * 70)
    
    print("\n  MINIMIZE these (as low as practically achievable):")
    for param, value in MINIMIZE_PARAMS.items():
        print(f"    • {param}: target ≤ {value}")
    
    print("\n  MAXIMIZE these (as high as practically achievable):")
    for param, value in MAXIMIZE_PARAMS.items():
        print(f"    • {param}: target ≥ {value}")
    
    # Save optimized config
    output_path = PACKAGE_ROOT / "config" / "vehicle_configs" / "optimized_vehicle.json"
    save_config(result.best_config, output_path)
    print(f"\n✓ Optimized configuration saved to: {output_path}")
    
    # Also save a summary report
    report_path = PACKAGE_ROOT / "optimization_report.json"
    report = {
        'best_time_seconds': result.best_time,
        'final_velocity_ms': result.best_result.final_velocity,
        'power_compliant': result.best_result.power_compliant,
        'wheelie_detected': result.best_result.wheelie_detected,
        'n_evaluations': result.n_evaluations,
        'optimization_time_seconds': result.elapsed_time,
        'optimized_parameters': result.optimized_params,
        'minimize_targets': MINIMIZE_PARAMS,
        'maximize_targets': MAXIMIZE_PARAMS,
    }
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"✓ Optimization report saved to: {report_path}")
    
    print("\n" + "=" * 70)
    print("OPTIMIZATION COMPLETE")
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    result = main()
