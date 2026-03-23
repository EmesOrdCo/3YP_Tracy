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
        # Use Pacejka model if specified in config, otherwise use simple model
        use_pacejka = getattr(config.tires, 'tire_model_type', 'pacejka') == 'pacejka'
        self.tire_model = TireModel(config.tires, use_pacejka=use_pacejka)
        
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
        
        # Calculate tire forces from slip (using Pacejka model)
        tire_force_front, rr_front = self.tire_model.calculate_longitudinal_force(
            normal_front, slip_front, state.velocity
        )
        tire_force_rear, rr_rear = self.tire_model.calculate_longitudinal_force(
            normal_rear, slip_rear, state.velocity
        )
        
        # Calculate motor speed
        motor_speed = self.powertrain.calculate_motor_speed(wheel_speed_rear)
        
        # Control strategy: Pacejka-aware traction control
        # Uses load-dependent optimal slip ratio from Pacejka model
        requested_torque = self._calculate_requested_torque(state, normal_rear, slip_rear)
        
        # Calculate powertrain torque (with power limit)
        wheel_torque, motor_current, power = self.powertrain.calculate_torque(
            requested_torque,
            motor_speed,
            state.velocity,
            dt=self.dt,
            update_storage=False  # Don't update during RK4 intermediate steps
        )
        
        # === PROPER WHEEL DYNAMICS WITH SLIP ===
        # The tire force that propels the vehicle is determined by the Pacejka model
        # based on current slip - NOT directly from motor torque!
        
        # Vehicle acceleration is driven by actual tire force (from slip)
        # Plus rolling resistance from front tires (free-rolling)
        total_tire_force = tire_force_rear  # Rear drive only
        total_resistive = drag_force + rr_front + rr_rear
        net_force_vehicle = total_tire_force + total_resistive
        
        # Vehicle effective mass (includes 2 front wheels rotating with vehicle)
        wheel_inertia = self.config.powertrain.wheel_inertia
        wheel_rotational_mass_front = 2.0 * wheel_inertia / (self.tire_model.radius ** 2)
        effective_mass = self.config.mass.total_mass + wheel_rotational_mass_front
        
        # Vehicle acceleration (from tire forces, not motor torque)
        acceleration = net_force_vehicle / effective_mass
        
        # Update normal forces with actual acceleration
        normal_front, normal_rear = self.mass_model.calculate_normal_forces(
            acceleration,
            downforce_front,
            downforce_rear
        )
        
        # === WHEEL ANGULAR ACCELERATION (allows slip to develop) ===
        # The rear wheel accelerates based on torque imbalance:
        # Angular accel = (motor_torque - tire_reaction_torque) / I_wheel
        #
        # Where tire_reaction_torque = tire_force × radius
        # 
        # If motor_torque > grip, wheel spins up faster (positive slip)
        # If motor_torque < grip, wheel slows relative to vehicle (slip decreases)
        
        tire_reaction_torque = tire_force_rear * self.tire_model.radius
        
        # Total rear wheel inertia (2 driven wheels)
        rear_wheel_inertia = 2.0 * wheel_inertia
        
        # Wheel angular acceleration
        wheel_alpha_rear = (wheel_torque - tire_reaction_torque) / rear_wheel_inertia
        
        # Get powertrain state for energy storage tracking
        pt_state = self.powertrain.get_last_state()
        
        # Get optimal slip for logging
        optimal_slip = self.tire_model.get_optimal_slip_ratio(normal_rear)
        
        # Create derivative state
        dstate = SimulationState()
        dstate.velocity = acceleration
        dstate.position = state.velocity
        dstate.wheel_angular_velocity_rear = wheel_alpha_rear
        dstate.wheel_angular_velocity_front = 0.0  # Free-rolling
        dstate.acceleration = acceleration
        dstate.drive_force = total_tire_force
        dstate.drag_force = drag_force
        dstate.rolling_resistance = rr_front + rr_rear
        dstate.normal_force_front = normal_front
        dstate.normal_force_rear = normal_rear
        dstate.tire_force_front = tire_force_front
        dstate.tire_force_rear = tire_force_rear
        dstate.slip_ratio_rear = slip_rear
        dstate.optimal_slip_ratio = optimal_slip
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
        normal_force_rear: float,
        current_slip_ratio: float
    ) -> float:
        """
        Calculate requested torque with Pacejka-aware traction control.
        
        Uses closed-loop slip control targeting the load-dependent optimal slip
        ratio from the Pacejka model. This maximizes traction force.
        
        The control has two regimes:
        1. Launch (v < 2 m/s): Open-loop grip-based limiting
        2. Normal (v >= 2 m/s): Closed-loop slip tracking
        
        Args:
            state: Current state
            normal_force_rear: Rear normal force
            current_slip_ratio: Current rear tire slip ratio
            
        Returns:
            Requested torque at wheels (N·m)
        """
        # Get Pacejka load-dependent optimal slip ratio
        optimal_slip = self.tire_model.get_optimal_slip_ratio(normal_force_rear)
        
        # Get peak friction coefficient (load-sensitive)
        mu_peak = self.tire_model.get_peak_friction_coefficient(normal_force_rear)
        
        # Maximum tire force at optimal slip
        max_tire_force = mu_peak * normal_force_rear
        max_torque_grip = max_tire_force * self.tire_model.radius
        
        # Base torque limit
        base_torque = min(self.config.control.launch_torque_limit, max_torque_grip)
        
        # === TORQUE RAMP AT LAUNCH (optimal FS practice) ===
        # Ramp torque over first 50ms to reduce jerk, avoid slip overshoot.
        ramp_duration = 0.05  # s
        if state.time < ramp_duration:
            ramp = state.time / ramp_duration
            base_torque *= ramp
        
        if not self.config.control.traction_control_enabled:
            return base_torque
        
        # === OPTIMAL SLIP-TRACKING TRACTION CONTROL ===
        #
        # Physics: Tire force is maximized at optimal slip (~15%).
        # Strategy: Track wheel velocity to maintain optimal slip.
        # Target: wheel_v = vehicle_v * (1 + optimal_slip)
        
        wheel_velocity = state.wheel_angular_velocity_rear * self.tire_model.radius
        target_wheel_v = state.velocity * (1.0 + optimal_slip)
        wheel_error = wheel_velocity - target_wheel_v
        
        if wheel_error > 0.05:
            reduction = max(0.1, 1.0 - wheel_error * 2.0)
            return base_torque * reduction
        else:
            return base_torque
    
    def _rk4_step(
        self,
        state: SimulationState,
        dstate_dt: SimulationState,
        dt: float
    ) -> SimulationState:
        """
        Perform one RK4 integration step.
        
        Only position, velocity, and wheel_angular_velocity_rear are integrated.
        All other state variables (motor_speed, forces, power, etc.) are derived
        from the current state and should NOT be integrated.
        
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
        state_k2 = self._integrate_state(state, k1, dt / 2.0)
        k2 = self._calculate_derivatives(state_k2)
        
        # k3
        state_k3 = self._integrate_state(state, k2, dt / 2.0)
        k3 = self._calculate_derivatives(state_k3)
        
        # k4
        state_k4 = self._integrate_state(state, k3, dt)
        k4 = self._calculate_derivatives(state_k4)
        
        # RK4 weighted average of derivatives
        # d/dt = (k1 + 2*k2 + 2*k3 + k4) / 6
        avg_d_position = (k1.position + 2*k2.position + 2*k3.position + k4.position) / 6.0
        avg_d_velocity = (k1.velocity + 2*k2.velocity + 2*k3.velocity + k4.velocity) / 6.0
        avg_d_wheel_rear = (k1.wheel_angular_velocity_rear + 2*k2.wheel_angular_velocity_rear + 
                           2*k3.wheel_angular_velocity_rear + k4.wheel_angular_velocity_rear) / 6.0
        
        # Create new state with integrated values
        new_state = SimulationState()
        new_state.time = state.time + dt
        new_state.position = state.position + avg_d_position * dt
        new_state.velocity = state.velocity + avg_d_velocity * dt
        new_state.wheel_angular_velocity_rear = state.wheel_angular_velocity_rear + avg_d_wheel_rear * dt
        
        # Front wheels are free-rolling (velocity / tire_radius)
        new_state.wheel_angular_velocity_front = new_state.velocity / self.tire_model.radius if new_state.velocity > 0 else 0.0
        
        # Calculate TRUE acceleration as dv/dt (not instantaneous force-based)
        new_state.acceleration = (new_state.velocity - state.velocity) / dt
        
        # Update energy storage ONCE per timestep
        pt_state = self.powertrain.get_last_state()
        if pt_state is not None:
            self.powertrain.update_energy_storage(dt, pt_state.power_electrical)
            pt_state = self.powertrain.get_last_state()
        
        # Recalculate all derived quantities at the NEW state
        # This ensures motor_speed, forces, power etc. are correct for the new velocity
        final_derivatives = self._calculate_derivatives(new_state)
        
        # Copy derived (non-integrated) values from final calculation
        new_state.motor_speed = final_derivatives.motor_speed
        new_state.motor_current = final_derivatives.motor_current
        new_state.motor_torque = final_derivatives.motor_torque
        new_state.drive_force = final_derivatives.drive_force
        new_state.drag_force = final_derivatives.drag_force
        new_state.rolling_resistance = final_derivatives.rolling_resistance
        new_state.normal_force_front = final_derivatives.normal_force_front
        new_state.normal_force_rear = final_derivatives.normal_force_rear
        new_state.tire_force_front = final_derivatives.tire_force_front
        new_state.tire_force_rear = final_derivatives.tire_force_rear
        new_state.slip_ratio_rear = final_derivatives.slip_ratio_rear
        new_state.optimal_slip_ratio = final_derivatives.optimal_slip_ratio
        new_state.power_consumed = final_derivatives.power_consumed
        
        # Energy storage state
        if pt_state is not None:
            new_state.dc_bus_voltage = pt_state.dc_bus_voltage
            new_state.energy_storage_soc = pt_state.state_of_charge
            new_state.energy_storage_loss = pt_state.storage_power_loss
            new_state.in_field_weakening = pt_state.in_field_weakening
        
        return new_state
    
    def _integrate_state(
        self,
        state: SimulationState,
        derivatives: SimulationState,
        dt: float
    ) -> SimulationState:
        """
        Integrate ONLY the true state variables (position, velocity, wheel speed).
        
        Args:
            state: Current state
            derivatives: Time derivatives
            dt: Time step
            
        Returns:
            New state with integrated values (other fields copied from derivatives)
        """
        result = SimulationState()
        
        # Integrate only the true state variables
        result.position = state.position + derivatives.position * dt
        result.velocity = state.velocity + derivatives.velocity * dt
        result.wheel_angular_velocity_rear = state.wheel_angular_velocity_rear + derivatives.wheel_angular_velocity_rear * dt
        result.wheel_angular_velocity_front = result.velocity / self.tire_model.radius if result.velocity > 0 else 0.0
        
        # Time
        result.time = state.time + dt
        
        # Copy non-integrated values from derivatives (they'll be recalculated anyway)
        result.acceleration = derivatives.acceleration
        result.motor_speed = derivatives.motor_speed
        result.motor_current = derivatives.motor_current
        result.motor_torque = derivatives.motor_torque
        result.drive_force = derivatives.drive_force
        result.drag_force = derivatives.drag_force
        result.rolling_resistance = derivatives.rolling_resistance
        result.normal_force_front = derivatives.normal_force_front
        result.normal_force_rear = derivatives.normal_force_rear
        result.tire_force_front = derivatives.tire_force_front
        result.tire_force_rear = derivatives.tire_force_rear
        result.power_consumed = derivatives.power_consumed
        result.dc_bus_voltage = derivatives.dc_bus_voltage
        result.energy_storage_soc = derivatives.energy_storage_soc
        result.energy_storage_loss = derivatives.energy_storage_loss
        result.in_field_weakening = derivatives.in_field_weakening
        
        return result
    
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


