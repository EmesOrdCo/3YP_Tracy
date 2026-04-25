"""Dynamics solver for acceleration simulation."""

import numpy as np
from typing import List, Optional, Tuple
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
        surface_mu_scaling = getattr(config.environment, 'surface_mu_scaling', 1.0)
        self.tire_model = TireModel(config.tires, use_pacejka=use_pacejka, surface_mu_scaling=surface_mu_scaling)
        
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

        # --- Driveline compliance configuration ---
        # Effective gear ratio (matches PowertrainModel): gear_ratio * differential.
        self._drive_ratio = (
            config.powertrain.gear_ratio * config.powertrain.differential_ratio
        )
        self._use_compliance = bool(
            getattr(config.powertrain, "driveline_compliance_enabled", False)
        )
        self._motor_inertia = float(getattr(config.powertrain, "motor_inertia", 0.077))
        self._driveline_K = float(getattr(config.powertrain, "driveline_stiffness", 5000.0))
        self._driveline_C = float(getattr(config.powertrain, "driveline_damping", 30.0))

        # --- Tyre thermal configuration ---
        self._use_thermal = bool(getattr(config.tires, "thermal_model_enabled", False))
        self._thermal_ambient = float(getattr(config.tires, "thermal_ambient_temp", 25.0))
        self._thermal_capacity = float(getattr(config.tires, "thermal_capacity", 3600.0))
        self._thermal_cooling = float(getattr(config.tires, "thermal_cooling_coefficient", 15.0))

        # Anti-wheelie feedback: closed-loop torque reduction kicks in once
        # measured front Fz drops below this threshold (N). Chosen so that the
        # 50 N static cap margin has plenty of headroom before activation.
        self._fz_feedback_threshold = 150.0

        # Tracks the last converged front Fz across integrator sub-steps so
        # the closed-loop anti-wheelie feedback sees a consistent value
        # regardless of which RK4 mid-point is currently being evaluated.
        # Initialised to a large sentinel so the feedback is inactive until
        # the first real step populates it.
        self._last_fz_front = float("inf")

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
        # Seed the normal loads with the static distribution so the anti-
        # wheelie feedback sees a sensible previous-step value on the very
        # first integrator iteration (rather than the dataclass default of 0).
        front_static, rear_static = self.mass_model.calculate_static_load_distribution()
        state.normal_force_front = front_static
        state.normal_force_rear = rear_static
        self._last_fz_front = front_static
        # Compliance-mode initial conditions: motor and wheel both at rest,
        # no pre-load in the driveline spring.
        state.motor_speed = 0.0
        state.driveline_twist = 0.0
        # Thermal model initial condition: both axles at the specified
        # ``thermal_initial_temp``. When the thermal model is disabled the
        # fields still carry sensible default values so logging/plotting
        # code that reads them doesn't trip.
        initial_temp = float(getattr(self.config.tires, "thermal_initial_temp", 25.0))
        state.tyre_temp_front = initial_temp
        state.tyre_temp_rear = initial_temp
        self.state_history = [state.copy()]
        
        # Simulation loop
        while state.position < self.target_distance and state.time < self.max_time:
            # Calculate derivatives
            dstate_dt = self._calculate_derivatives(state)

            # Integrate using RK4
            state = self._rk4_step(state, dstate_dt, self.dt)

            # Refresh the feedback reference for the next step's sub-evals.
            self._last_fz_front = state.normal_force_front

            # Store state
            self.state_history.append(state.copy())
        
        return state
    
    def _axle_tire_force(self, normal_axle: float, slip: float,
                         velocity: float,
                         tyre_temp_c: Optional[float] = None) -> Tuple[float, float]:
        """Return (axle_long_force, axle_rolling_resistance) for one axle.

        Pacejka is a per-tyre curve with a load-sensitive peak (pDx2). Feeding
        the whole axle Fz into it biases the peak force; instead evaluate the
        curve at Fz/2 per tyre and double the result. Temperature, if
        supplied, is forwarded to the tyre model and applied as a grip-window
        multiplier by ``TireModel.thermal_mu_factor``.
        """
        per_tyre_fz = max(0.0, normal_axle) / 2.0
        fx_one, rr_one = self.tire_model.calculate_longitudinal_force(
            per_tyre_fz, slip, velocity, tyre_temp_c=tyre_temp_c,
        )
        return 2.0 * fx_one, 2.0 * rr_one

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

        # Calculate wheel speeds (simplified: assume RWD, front wheels free-rolling)
        wheel_speed_front = state.velocity / self.tire_model.radius if state.velocity > 0 else 0.0
        wheel_speed_rear = state.wheel_angular_velocity_rear

        # Calculate slip ratios
        slip_front = self.tire_model.calculate_slip_ratio(wheel_speed_front, state.velocity)
        slip_rear = self.tire_model.calculate_slip_ratio(wheel_speed_rear, state.velocity)

        # Motor speed.
        #
        # Rigid mode (compliance off): motor speed is directly tied to rear
        # wheel speed through the gearing. This is how the solver has always
        # worked and matches the historical results.
        #
        # Compliant mode: motor speed is an independent integrated state,
        # exposed via ``SimulationState.motor_speed``. The spring-damper
        # between rotor and hub is evaluated below.
        if self._use_compliance:
            motor_speed = state.motor_speed
        else:
            motor_speed = self.powertrain.calculate_motor_speed(wheel_speed_rear)

        # Vehicle effective mass (includes 2 front wheels rotating with vehicle)
        wheel_inertia = self.config.powertrain.wheel_inertia
        wheel_rotational_mass_front = 2.0 * wheel_inertia / (self.tire_model.radius ** 2)
        effective_mass = self.config.mass.total_mass + wheel_rotational_mass_front

        # === FIXED-POINT ITERATION ON ACCELERATION ===
        # Normal forces depend on acceleration (longitudinal load transfer),
        # tyre longitudinal forces depend on those normals (load-sensitive
        # Pacejka), and acceleration is ultimately determined by the tyre
        # forces. Iterate until a self-consistent solution converges.
        #
        # Convergence is typically 2-3 iterations for this problem; the loop
        # bounds run-time to 5 iterations with a 0.01 m/s^2 tolerance.
        accel = state.acceleration if state.acceleration != 0 else 1.0
        max_iter = 5
        tol = 0.01
        for _iteration in range(max_iter):
            # Normals at current acceleration estimate.
            normal_front, normal_rear = self.mass_model.calculate_normal_forces(
                accel, downforce_front, downforce_rear,
            )
            anti_squat_delta = self.suspension_model.load_transfer_correction(
                mass=self.config.mass.total_mass,
                longitudinal_acceleration=accel,
                cg_height=self.config.mass.cg_z,
                wheelbase=self.config.mass.wheelbase,
            )
            normal_rear += anti_squat_delta
            normal_front = max(0.0, normal_front - anti_squat_delta)

            # Per-tyre Pacejka (see _axle_tire_force docstring). Temperature
            # is passed when the thermal model is enabled; the tyre model
            # applies a Gaussian grip-window multiplier to Fx.
            t_front = state.tyre_temp_front if self._use_thermal else None
            t_rear = state.tyre_temp_rear if self._use_thermal else None
            tire_force_front, rr_front = self._axle_tire_force(
                normal_front, slip_front, state.velocity, tyre_temp_c=t_front,
            )
            tire_force_rear, rr_rear = self._axle_tire_force(
                normal_rear, slip_rear, state.velocity, tyre_temp_c=t_rear,
            )

            # Anti-wheelie torque cap: limit rear drive so front Fz stays
            # above a safety margin. See _wheelie_torque_cap docstring.
            wheelie_cap = self._wheelie_torque_cap(
                downforce_front=downforce_front,
                drag_force=drag_force,
                rr_total=rr_front + rr_rear,
                effective_mass=effective_mass,
            )

            # Traction control uses the converged rear normal load.
            requested_torque = self._calculate_requested_torque(
                state, normal_rear, slip_rear, wheelie_cap,
            )
            wheel_torque, motor_current, power = self.powertrain.calculate_torque(
                requested_torque,
                motor_speed,
                state.velocity,
                dt=self.dt,
                update_storage=False,  # handled after the RK4 step
            )

            total_tire_force = tire_force_rear  # Rear drive only
            total_resistive = drag_force + rr_front + rr_rear
            net_force_vehicle = total_tire_force + total_resistive
            new_accel = net_force_vehicle / effective_mass

            if abs(new_accel - accel) < tol:
                accel = new_accel
                break
            accel = new_accel

        acceleration = accel

        # === WHEEL / MOTOR ANGULAR ACCELERATION ===
        # Total rear wheel inertia (both driven wheels).
        rear_wheel_inertia = 2.0 * wheel_inertia
        tire_reaction_torque = tire_force_rear * self.tire_model.radius

        # Pull motor torque (raw shaft torque, before gear reduction) off the
        # powertrain's last state. calculate_torque populates ``motor_torque``
        # whenever the advanced motor model is used; for the legacy model it
        # still reflects the torque actually applied at the motor shaft.
        pt_state = self.powertrain.get_last_state()
        motor_shaft_torque = (
            pt_state.motor_torque if pt_state is not None else 0.0
        )

        if self._use_compliance:
            # Drive torque at the wheel hub from the spring-damper.
            rel_speed_hub = motor_speed / self._drive_ratio - wheel_speed_rear
            drive_torque_at_hub = (
                self._driveline_K * state.driveline_twist
                + self._driveline_C * rel_speed_hub
            )
            # Reaction back onto the motor shaft: reduce by gear * efficiency
            # so that steady-state power balance matches the rigid case (in
            # the limit of very stiff K, the two ODEs collapse to the rigid
            # coupling).
            eta = max(1e-3, self.config.powertrain.drivetrain_efficiency)
            drive_torque_at_motor = drive_torque_at_hub / (self._drive_ratio * eta)

            wheel_alpha_rear = (
                drive_torque_at_hub - tire_reaction_torque
            ) / rear_wheel_inertia
            motor_alpha = (
                motor_shaft_torque - drive_torque_at_motor
            ) / max(1e-6, self._motor_inertia)
            twist_rate = rel_speed_hub
            applied_wheel_torque = drive_torque_at_hub
        else:
            # Rigid coupling: motor and wheels rotate in fixed ratio. The
            # motor's rotational inertia reflects onto the wheel hub as
            # ``I_motor * gear_ratio^2``; neglecting it (as the legacy solver
            # did) undercounts rotating inertia by ~15x for a typical
            # geared EV powertrain. Total effective inertia at the hub is
            # therefore ``2 * I_wheel + I_motor * gear^2``.
            effective_rear_inertia = (
                rear_wheel_inertia + self._motor_inertia * self._drive_ratio ** 2
            )
            wheel_alpha_rear = (
                wheel_torque - tire_reaction_torque
            ) / effective_rear_inertia
            motor_alpha = 0.0
            twist_rate = 0.0
            applied_wheel_torque = wheel_torque

        # Get optimal slip for logging (per-tyre load).
        optimal_slip = self.tire_model.get_optimal_slip_ratio(normal_rear / 2.0)

        # --- Tyre thermal rates ---
        # Heat into the tyres is the sliding friction work at the contact
        # patch: P_sliding = |F_long| * |slip_velocity|. slip_velocity is
        # the difference between wheel surface speed and vehicle speed.
        # Cooling is linear in (T - T_ambient) with coefficient h.
        if self._use_thermal:
            slip_v_front = abs(
                wheel_speed_front * self.tire_model.radius - state.velocity
            )
            slip_v_rear = abs(
                wheel_speed_rear * self.tire_model.radius - state.velocity
            )
            q_in_front = abs(tire_force_front) * slip_v_front
            q_in_rear = abs(tire_force_rear) * slip_v_rear
            q_out_front = self._thermal_cooling * (
                state.tyre_temp_front - self._thermal_ambient
            )
            q_out_rear = self._thermal_cooling * (
                state.tyre_temp_rear - self._thermal_ambient
            )
            dT_front = (q_in_front - q_out_front) / max(1e-3, self._thermal_capacity)
            dT_rear = (q_in_rear - q_out_rear) / max(1e-3, self._thermal_capacity)
        else:
            dT_front = 0.0
            dT_rear = 0.0

        # Create derivative state. For integrated quantities (position,
        # velocity, wheel_angular_velocity_rear) the named slot holds the
        # derivative. For logging-only slots (motor_speed, forces, ...) it
        # holds the value. motor_speed and driveline_twist are a special
        # case: their *values* are written into those slots for logging, and
        # their *derivatives* are carried in motor_alpha / driveline_twist_rate
        # which _rk4_step reads when compliance is enabled.
        dstate = SimulationState()
        dstate.velocity = acceleration
        dstate.position = state.velocity
        dstate.wheel_angular_velocity_rear = wheel_alpha_rear
        dstate.wheel_angular_velocity_front = 0.0  # Free-rolling
        dstate.motor_alpha = motor_alpha
        dstate.driveline_twist_rate = twist_rate
        dstate.driveline_twist = state.driveline_twist  # current value (not integrated here)
        dstate.tyre_temp_front = state.tyre_temp_front  # value carried forward
        dstate.tyre_temp_rear = state.tyre_temp_rear
        dstate.tyre_temp_front_rate = dT_front
        dstate.tyre_temp_rear_rate = dT_rear
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
        dstate.motor_torque = applied_wheel_torque  # torque delivered to wheels
        dstate.power_consumed = power
        dstate.time = 1.0  # dt will be applied in integration
        
        # Energy storage state (not derivatives, but captured for logging)
        if pt_state is not None:
            dstate.dc_bus_voltage = pt_state.dc_bus_voltage
            dstate.energy_storage_soc = pt_state.state_of_charge
            dstate.energy_storage_loss = pt_state.storage_power_loss
            dstate.in_field_weakening = pt_state.in_field_weakening
        
        return dstate
    
    def _wheelie_torque_cap(
        self,
        downforce_front: float,
        drag_force: float,
        rr_total: float,
        effective_mass: float,
    ) -> float:
        """Return the maximum wheel torque that keeps front Fz above a margin.

        Moment balance about the rear contact patch (steady-state, per the
        same model used by ``MassPropertiesModel.calculate_normal_forces``)
        gives the vehicle longitudinal acceleration at which front Fz hits a
        chosen safety margin ``Fz_margin``:

            Fz_front = m*g*(L - cg_x)/L - (1 - k_as_eff)*m*a*cg_z/L
                       + F_df_front
            => a_max = (m*g*(L - cg_x) + F_df_front*L - Fz_margin*L)
                       / ((1 - k_as_eff) * m * cg_z)

        ``k_as_eff = 0.2 * anti_squat_ratio`` mirrors the scaling used in
        ``SuspensionModel.load_transfer_correction``.

        That acceleration is then converted to an equivalent wheel torque via
        Newton's second law: the rear drive force must overcome drag and
        rolling resistance and still deliver ``a_max`` to the vehicle:

            F_drive_max = effective_mass * a_max + drag + rolling_resistance
            T_wheel_max = F_drive_max * tyre_radius

        ``Fz_margin`` is held at 50 N so numerical float noise and the RK4
        mid-points don't occasionally dip below zero and trip the wheelie
        detector. Returns ``+inf`` if the geometry makes a wheelie impossible
        (e.g. cg_z = 0 or front-heavy CG that can't be lifted).
        """
        g = 9.81
        m = self.config.mass.total_mass
        L = self.config.mass.wheelbase
        cg_x = self.config.mass.cg_x
        cg_z = self.config.mass.cg_z

        if cg_z <= 0.0 or L <= 0.0 or m <= 0.0:
            return float("inf")

        fz_margin = 50.0  # N — keep a small positive front load
        k_as = getattr(self.config.suspension, "anti_squat_ratio", 0.0)
        k_as_eff = max(0.0, min(1.0, k_as)) * 0.2
        transfer_denom = (1.0 - k_as_eff) * m * cg_z
        if transfer_denom <= 0.0:
            return float("inf")

        stabilising = m * g * (L - cg_x) + downforce_front * L - fz_margin * L
        if stabilising <= 0.0:
            # CG so far back that front Fz never positive — any throttle
            # wheelies. Return 0 so the controller cuts torque completely.
            return 0.0

        a_max = stabilising / transfer_denom
        f_drive_max = effective_mass * a_max + max(0.0, drag_force) + max(0.0, rr_total)
        t_wheel_max = f_drive_max * self.tire_model.radius
        return max(0.0, t_wheel_max)

    def _calculate_requested_torque(
        self,
        state: SimulationState,
        normal_force_rear: float,
        current_slip_ratio: float,
        wheelie_torque_cap: float = float("inf"),
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
        # Get Pacejka load-dependent optimal slip ratio and peak mu. Pacejka
        # coefficients are per-tyre, so evaluate at the per-tyre load.
        per_tyre_fz = normal_force_rear / 2.0
        optimal_slip = self.tire_model.get_optimal_slip_ratio(per_tyre_fz)
        mu_peak = self.tire_model.get_peak_friction_coefficient(per_tyre_fz)

        # Axle peak force = 2 * (mu_peak_per_tyre * Fz_per_tyre) = mu_peak * Fz_axle.
        max_tire_force = mu_peak * normal_force_rear
        max_torque_grip = max_tire_force * self.tire_model.radius
        
        # Base torque limit. ``wheelie_torque_cap`` is derived from a pitch
        # moment balance (see :meth:`_wheelie_torque_cap`) and is applied
        # before launch ramping so that the transient is also wheelie-safe.
        base_torque = min(
            self.config.control.launch_torque_limit,
            max_torque_grip,
            wheelie_torque_cap,
        )

        # Closed-loop anti-wheelie feedback on observed front Fz. The static
        # cap is correct for steady-state longitudinal dynamics, but at launch
        # the wheel spins through the Pacejka peak (slip ~0.15) and delivers
        # transient tyre forces that exceed the cap's implied drive force.
        # Real launch controllers use IMU pitch/vertical-load feedback; here
        # we track the last-converged ``normal_force_front`` on the solver
        # (``_last_fz_front``) so every RK4 sub-evaluation sees the same
        # physically meaningful value rather than a freshly-defaulted zero.
        fz_front_prev = self._last_fz_front
        if state.time > 0.0 and fz_front_prev < self._fz_feedback_threshold:
            fz_scale = max(0.0, fz_front_prev / self._fz_feedback_threshold)
            base_torque *= fz_scale
        
        # === TORQUE RAMP AT LAUNCH (optimal FS practice) ===
        # Ramp torque over the first 80 ms to reduce jerk and give the rear
        # wheel inertia time to track vehicle speed without overshoot. A
        # shorter ramp tends to spin the wheels through the Pacejka peak
        # before the controller can react, producing transient wheelies.
        ramp_duration = 0.08  # s
        if state.time < ramp_duration:
            ramp = state.time / ramp_duration
            base_torque *= ramp

        if not self.config.control.traction_control_enabled:
            return base_torque

        # === SLIP-RATIO GOVERNOR ===
        # Pacejka peak sits around slip ~= optimal_slip (typically 0.13-0.17).
        # Above that, tyre force drops off; below it, force is a monotone
        # function of slip. We never want to run *past* the peak because the
        # trip through the peak dumps max grip into the chassis, which on a
        # rear-biased CG lifts the front. Collapse torque to zero any time
        # slip rises well above optimal so the wheel slows back into the safe
        # regime — functionally equivalent to real slip-based launch control.
        slip_ceiling = 2.0 * max(0.05, optimal_slip)
        if current_slip_ratio > slip_ceiling:
            return 0.0

        # === OPTIMAL SLIP-TRACKING TRACTION CONTROL ===
        #
        # Physics: Tire force is maximized at optimal slip (~15%).
        # Strategy: Track wheel velocity to maintain optimal slip.
        # Target: wheel_v = vehicle_v * (1 + optimal_slip)

        wheel_velocity = state.wheel_angular_velocity_rear * self.tire_model.radius
        target_wheel_v = state.velocity * (1.0 + optimal_slip)
        wheel_error = wheel_velocity - target_wheel_v

        if wheel_error > 0.05:
            # Collapse all the way to zero under strong overspeed — the
            # previous 0.1 floor left enough residual torque to keep the
            # slip oscillation running on wheelie-prone chassis.
            reduction = max(0.0, 1.0 - wheel_error * 2.0)
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
        def _avg(field: str) -> float:
            return (
                getattr(k1, field) + 2 * getattr(k2, field)
                + 2 * getattr(k3, field) + getattr(k4, field)
            ) / 6.0

        avg_d_position = _avg("position")
        avg_d_velocity = _avg("velocity")
        avg_d_wheel_rear = _avg("wheel_angular_velocity_rear")

        # Create new state with integrated values
        new_state = SimulationState()
        new_state.time = state.time + dt
        new_state.position = state.position + avg_d_position * dt
        new_state.velocity = state.velocity + avg_d_velocity * dt
        new_state.wheel_angular_velocity_rear = state.wheel_angular_velocity_rear + avg_d_wheel_rear * dt

        # Driveline torsional states are only integrated when compliance is on.
        if self._use_compliance:
            avg_motor_alpha = _avg("motor_alpha")
            avg_twist_rate = _avg("driveline_twist_rate")
            new_state.motor_speed = state.motor_speed + avg_motor_alpha * dt
            new_state.driveline_twist = state.driveline_twist + avg_twist_rate * dt

        # Tyre temperature: always integrated (rates are zero when the thermal
        # model is disabled so this is a no-op in that case).
        avg_dT_front = _avg("tyre_temp_front_rate")
        avg_dT_rear = _avg("tyre_temp_rear_rate")
        new_state.tyre_temp_front = state.tyre_temp_front + avg_dT_front * dt
        new_state.tyre_temp_rear = state.tyre_temp_rear + avg_dT_rear * dt

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

        # Copy derived (non-integrated) values from final calculation.
        # In rigid mode, final_derivatives.motor_speed is the fresh
        # wheel_speed*gear value; in compliant mode we *already* have the
        # integrated motor_speed on new_state and must not overwrite it.
        # tyre_temp_* are always integrated, so never overwrite from
        # final_derivatives (which holds only the value-slot carry).
        if not self._use_compliance:
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

        # Driveline torsional states (compliance mode): integrate using the
        # dedicated derivative carriers stashed by _calculate_derivatives.
        if self._use_compliance:
            result.motor_speed = state.motor_speed + derivatives.motor_alpha * dt
            result.driveline_twist = state.driveline_twist + derivatives.driveline_twist_rate * dt
        else:
            # Rigid mode: motor_speed is algebraically tied to wheel speed.
            # Derive it from the freshly-integrated wheel speed so every RK4
            # mid-point sees the correct motor speed.
            result.motor_speed = (
                result.wheel_angular_velocity_rear * self._drive_ratio
            )
            result.driveline_twist = 0.0

        # Tyre temperature (integrated regardless of thermal model: the rates
        # are zero when the thermal model is disabled, so this is a no-op in
        # that case and stays exact).
        result.tyre_temp_front = state.tyre_temp_front + derivatives.tyre_temp_front_rate * dt
        result.tyre_temp_rear = state.tyre_temp_rear + derivatives.tyre_temp_rear_rate * dt

        # Time
        result.time = state.time + dt

        # Copy non-integrated values from derivatives (they'll be recalculated anyway)
        result.acceleration = derivatives.acceleration
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


