"""Dynamics solver for acceleration simulation."""

import numpy as np
from typing import List, Optional
import sys
from pathlib import Path

# Setup path for development mode first
package_root = Path(__file__).parent.parent.resolve()
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

# Import with fallback for both package and development modes
try:
    from .state import SimulationState
    from ..config.vehicle_config import VehicleConfig
except (ImportError, ValueError):
    from dynamics.state import SimulationState
    from config.vehicle_config import VehicleConfig

# Import vehicle modules directly (avoid going through vehicle/__init__ to prevent circular imports)
try:
    from ..vehicle.tire_model import TireModel
    from ..vehicle.aerodynamics import AerodynamicsModel
    from ..vehicle.mass_properties import MassPropertiesModel
    from ..vehicle.suspension import SuspensionModel
except (ImportError, ValueError):
    from vehicle.tire_model import TireModel
    from vehicle.aerodynamics import AerodynamicsModel
    from vehicle.mass_properties import MassPropertiesModel
    from vehicle.suspension import SuspensionModel

# Lazy import for powertrain to avoid circular imports
# These will be imported when DynamicsSolver is instantiated
_PowertrainModel = None
_create_powertrain_with_battery = None
_create_powertrain_with_supercapacitor = None

def _ensure_powertrain_imports():
    """Lazy import of powertrain module to avoid circular imports."""
    global _PowertrainModel, _create_powertrain_with_battery, _create_powertrain_with_supercapacitor
    if _PowertrainModel is None:
        # Direct file import to bypass package __init__
        import importlib.util
        pt_path = Path(__file__).parent.parent / "vehicle" / "powertrain.py"
        spec = importlib.util.spec_from_file_location("powertrain_direct", pt_path)
        pt_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pt_module)
        _PowertrainModel = pt_module.PowertrainModel
        _create_powertrain_with_battery = pt_module.create_powertrain_with_battery
        _create_powertrain_with_supercapacitor = pt_module.create_powertrain_with_supercapacitor


class DynamicsSolver:
    """Dynamics solver for 75m acceleration simulation."""
    
    def __init__(self, config: VehicleConfig):
        """
        Initialize dynamics solver.
        
        Args:
            config: Vehicle configuration
        """
        self.config = config
        
        # Initialize vehicle models
        self.tire_model = TireModel(config.tires)
        
        # Ensure powertrain imports are loaded (lazy import to avoid circular deps)
        _ensure_powertrain_imports()
        
        # Create powertrain with appropriate energy storage based on config
        energy_storage_type = getattr(config.powertrain, 'energy_storage_type', 'battery')
        if energy_storage_type == 'supercapacitor':
            self.powertrain = _create_powertrain_with_supercapacitor(
                config.powertrain,
                cell_voltage=getattr(config.powertrain, 'supercap_cell_voltage', 3.0),
                cell_capacitance=getattr(config.powertrain, 'supercap_cell_capacitance', 600.0),
                cell_esr=getattr(config.powertrain, 'supercap_cell_esr', 0.7e-3),
                num_cells=getattr(config.powertrain, 'supercap_num_cells', 200),
                min_operating_voltage=getattr(config.powertrain, 'supercap_min_voltage', 350.0)
            )
        else:
            self.powertrain = _create_powertrain_with_battery(config.powertrain)
        
        self.aero_model = AerodynamicsModel(config.aerodynamics)
        self.mass_model = MassPropertiesModel(config.mass)
        self.suspension_model = SuspensionModel(config.suspension)
        
        # Simulation parameters
        self.dt = config.dt
        self.max_time = config.max_time
        self.target_distance = config.target_distance
        
        # State history
        self.state_history: List[SimulationState] = []
    
    def solve(self) -> SimulationState:
        """
        Solve acceleration simulation until target distance is reached.
        
        Returns:
            Final simulation state
        """
        # Reset powertrain (important for supercapacitor - resets to full voltage)
        self.powertrain.reset()
        
        # Initialize state
        state = SimulationState()
        state.dc_bus_voltage = self.powertrain.get_dc_bus_voltage()  # Initial voltage
        state.energy_storage_soc = 1.0  # Start fully charged
        self.state_history = [state.copy()]
        
        # Simulation loop
        while state.position < self.target_distance and state.time < self.max_time:
            # Calculate derivatives
            dstate_dt = self._calculate_derivatives(state)
            
            # Integrate using RK4
            state = self._rk4_step(state, dstate_dt, self.dt)
            
            # Store state
            self.state_history.append(state.copy())
        
        return state
    
    def _calculate_derivatives(self, state: SimulationState) -> SimulationState:
        """
        Calculate time derivatives of state variables.
        
        Args:
            state: Current state
            
        Returns:
            State with derivatives in acceleration field
        """
        # Calculate aerodynamic forces
        drag_force, downforce_front, downforce_rear = self.aero_model.calculate_forces(state.velocity)
        
        # Calculate normal forces
        # Initial guess for acceleration (use previous or 0)
        accel_guess = state.acceleration if state.acceleration != 0 else 1.0
        normal_front, normal_rear = self.mass_model.calculate_normal_forces(
            accel_guess,
            downforce_front,
            downforce_rear
        )
        
        # Calculate wheel speeds (simplified: assume RWD, front wheels free-rolling)
        wheel_speed_front = state.velocity / self.tire_model.radius if state.velocity > 0 else 0.0
        wheel_speed_rear = state.wheel_angular_velocity_rear
        
        # Calculate slip ratios
        slip_front = self.tire_model.calculate_slip_ratio(wheel_speed_front, state.velocity)
        slip_rear = self.tire_model.calculate_slip_ratio(wheel_speed_rear, state.velocity)
        
        # Calculate tire forces
        tire_force_front, rr_front = self.tire_model.calculate_longitudinal_force(
            normal_front, slip_front, state.velocity
        )
        tire_force_rear, rr_rear = self.tire_model.calculate_longitudinal_force(
            normal_rear, slip_rear, state.velocity
        )
        
        # Calculate motor speed
        motor_speed = self.powertrain.calculate_motor_speed(wheel_speed_rear)
        
        # Control strategy: simple torque request
        # In a real implementation, this would be more sophisticated
        requested_torque = self._calculate_requested_torque(state, normal_rear)
        
        # Calculate powertrain torque (with power limit)
        # Pass dt for energy storage state update (supercapacitor voltage decay)
        wheel_torque, motor_current, power = self.powertrain.calculate_torque(
            requested_torque,
            motor_speed,
            state.velocity,
            dt=self.dt,
            update_storage=False  # Don't update during RK4 intermediate steps
        )
        
        # Convert wheel torque to force
        drive_force_rear = wheel_torque / self.tire_model.radius
        
        # Total drive force (rear wheel drive assumed)
        total_drive_force = drive_force_rear
        
        # Total resistive forces
        total_resistive = drag_force + rr_front + rr_rear
        
        # Net force (resistive forces oppose motion, so subtract them)
        net_force = total_drive_force + total_resistive  # resistive forces are already negative
        
        # Calculate effective mass accounting for wheel rotational inertia
        # When accelerating, we need to accelerate:
        # 1. The vehicle's translational mass
        # 2. The wheels' rotational inertia (all 4 wheels rotate)
        # Effective rotational mass = I_wheel / r² per wheel
        wheel_rotational_mass_per_wheel = self.config.powertrain.wheel_inertia / (self.tire_model.radius ** 2)
        total_rotational_mass = 4.0 * wheel_rotational_mass_per_wheel  # 4 wheels total
        effective_mass = self.config.mass.total_mass + total_rotational_mass
        
        # Acceleration (accounting for rotational inertia)
        acceleration = net_force / effective_mass
        
        # Update normal forces with actual acceleration
        normal_front, normal_rear = self.mass_model.calculate_normal_forces(
            acceleration,
            downforce_front,
            downforce_rear
        )
        
        # Wheel angular acceleration (rear wheel driven)
        # For RWD: wheel torque accelerates rear wheels
        # Angular acceleration = linear acceleration / radius (assuming no slip)
        # When there is slip, the relationship is more complex, but this approximation is reasonable
        wheel_alpha_rear = acceleration / self.tire_model.radius if self.tire_model.radius > 0 else 0.0
        
        # Get powertrain state for energy storage tracking
        pt_state = self.powertrain.get_last_state()
        
        # Create derivative state
        dstate = SimulationState()
        dstate.velocity = acceleration
        dstate.position = state.velocity
        dstate.wheel_angular_velocity_rear = wheel_alpha_rear
        dstate.wheel_angular_velocity_front = 0.0  # Free-rolling
        dstate.acceleration = acceleration
        dstate.drive_force = total_drive_force
        dstate.drag_force = drag_force
        dstate.rolling_resistance = rr_front + rr_rear
        dstate.normal_force_front = normal_front
        dstate.normal_force_rear = normal_rear
        dstate.tire_force_front = tire_force_front
        dstate.tire_force_rear = tire_force_rear
        dstate.motor_speed = motor_speed
        dstate.motor_current = motor_current
        dstate.motor_torque = wheel_torque
        dstate.power_consumed = power
        dstate.time = 1.0  # dt will be applied in integration
        
        # Energy storage state (not derivatives, but captured for logging)
        if pt_state is not None:
            dstate.dc_bus_voltage = pt_state.dc_bus_voltage
            dstate.energy_storage_soc = pt_state.state_of_charge
            dstate.energy_storage_loss = pt_state.storage_power_loss
            dstate.in_field_weakening = pt_state.in_field_weakening
        
        return dstate
    
    def _calculate_requested_torque(
        self,
        state: SimulationState,
        normal_force_rear: float
    ) -> float:
        """
        Calculate requested torque based on control strategy.
        
        Simplified control: request maximum available torque up to limit.
        
        Args:
            state: Current state
            normal_force_rear: Rear normal force
            
        Returns:
            Requested torque at wheels (N·m)
        """
        # Simple control: request maximum torque up to launch limit
        max_torque = self.config.control.launch_torque_limit
        
        # Limit based on available grip (simplified)
        max_tire_force = self.tire_model.mu_max * normal_force_rear
        max_torque_grip = max_tire_force * self.tire_model.radius
        
        # Use minimum of control limit and grip limit
        requested = min(max_torque, max_torque_grip)
        
        return requested
    
    def _rk4_step(
        self,
        state: SimulationState,
        dstate_dt: SimulationState,
        dt: float
    ) -> SimulationState:
        """
        Perform one RK4 integration step.
        
        Args:
            state: Current state
            dstate_dt: Time derivatives
            dt: Time step
            
        Returns:
            New state after integration
        """
        # k1
        k1 = dstate_dt
        
        # k2
        state_k2 = self._add_states(state, self._scale_state(k1, dt / 2.0))
        k2 = self._calculate_derivatives(state_k2)
        
        # k3
        state_k3 = self._add_states(state, self._scale_state(k2, dt / 2.0))
        k3 = self._calculate_derivatives(state_k3)
        
        # k4
        state_k4 = self._add_states(state, self._scale_state(k3, dt))
        k4 = self._calculate_derivatives(state_k4)
        
        # Combine
        weighted_avg = self._scale_state(
            self._add_states(
                k1,
                self._add_states(
                    self._scale_state(k2, 2.0),
                    self._add_states(
                        self._scale_state(k3, 2.0),
                        k4
                    )
                )
            ),
            1.0 / 6.0
        )
        
        # Update state
        new_state = self._add_states(state, self._scale_state(weighted_avg, dt))
        new_state.time = state.time + dt
        
        # Get the final power calculated by the last derivative (k4)
        # Then update energy storage ONCE per timestep with this power
        pt_state = self.powertrain.get_last_state()
        if pt_state is not None:
            # Update energy storage state with the final power value (once per timestep)
            # This ensures supercapacitor discharges at correct rate (not 4x during RK4)
            self.powertrain.update_energy_storage(dt, pt_state.power_electrical)
            
            # Re-get state after update to capture new voltage/SoC
            pt_state = self.powertrain.get_last_state()
            
            new_state.dc_bus_voltage = pt_state.dc_bus_voltage
            new_state.energy_storage_soc = pt_state.state_of_charge
            new_state.energy_storage_loss = pt_state.storage_power_loss
            new_state.in_field_weakening = pt_state.in_field_weakening
            # CRITICAL: Use actual values from powertrain/final derivative, not integrated
            new_state.power_consumed = pt_state.power_electrical
            new_state.motor_current = pt_state.motor_current
            new_state.motor_torque = pt_state.motor_torque
        
        # Capture acceleration from final derivative (k4), not the incorrectly integrated value
        new_state.acceleration = k4.acceleration
        new_state.drive_force = k4.drive_force
        new_state.drag_force = k4.drag_force
        new_state.rolling_resistance = k4.rolling_resistance
        
        return new_state
    
    def _add_states(self, s1: SimulationState, s2: SimulationState) -> SimulationState:
        """Add two states together."""
        result = SimulationState()
        result.position = s1.position + s2.position
        result.velocity = s1.velocity + s2.velocity
        result.acceleration = s1.acceleration + s2.acceleration
        result.wheel_angular_velocity_front = s1.wheel_angular_velocity_front + s2.wheel_angular_velocity_front
        result.wheel_angular_velocity_rear = s1.wheel_angular_velocity_rear + s2.wheel_angular_velocity_rear
        result.motor_speed = s1.motor_speed + s2.motor_speed
        result.motor_current = s1.motor_current + s2.motor_current
        result.motor_torque = s1.motor_torque + s2.motor_torque
        result.drive_force = s1.drive_force + s2.drive_force
        result.drag_force = s1.drag_force + s2.drag_force
        result.rolling_resistance = s1.rolling_resistance + s2.rolling_resistance
        result.normal_force_front = s1.normal_force_front + s2.normal_force_front
        result.normal_force_rear = s1.normal_force_rear + s2.normal_force_rear
        result.tire_force_front = s1.tire_force_front + s2.tire_force_front
        result.tire_force_rear = s1.tire_force_rear + s2.tire_force_rear
        result.power_consumed = s1.power_consumed + s2.power_consumed
        result.time = s1.time + s2.time
        return result
    
    def _scale_state(self, state: SimulationState, scale: float) -> SimulationState:
        """Scale state by a factor."""
        result = SimulationState()
        result.position = state.position * scale
        result.velocity = state.velocity * scale
        result.acceleration = state.acceleration * scale
        result.wheel_angular_velocity_front = state.wheel_angular_velocity_front * scale
        result.wheel_angular_velocity_rear = state.wheel_angular_velocity_rear * scale
        result.motor_speed = state.motor_speed * scale
        result.motor_current = state.motor_current * scale
        result.motor_torque = state.motor_torque * scale
        result.drive_force = state.drive_force * scale
        result.drag_force = state.drag_force * scale
        result.rolling_resistance = state.rolling_resistance * scale
        result.normal_force_front = state.normal_force_front * scale
        result.normal_force_rear = state.normal_force_rear * scale
        result.tire_force_front = state.tire_force_front * scale
        result.tire_force_rear = state.tire_force_rear * scale
        result.power_consumed = state.power_consumed * scale
        result.time = state.time * scale
        return result


