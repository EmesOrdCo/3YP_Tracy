"""Powertrain model for acceleration simulation.

This module integrates:
- Energy storage (Battery or Supercapacitor)
- Motor model (with field weakening)
- Drivetrain (gear ratio, efficiency)

Supports both battery and supercapacitor configurations for comparison.
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# Import with fallback for both package and development modes
try:
    from ..config.vehicle_config import PowertrainProperties
    from .energy_storage import EnergyStorage, BatteryModel, SupercapacitorModel, EnergyStorageState
    from .motor_model import MotorModel, MotorState, create_yasa_p400r
except (ImportError, ValueError):
    # Fall back to absolute imports (development mode)
    package_root = Path(__file__).parent.parent.parent.resolve()
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    from config.vehicle_config import PowertrainProperties
    from vehicle.energy_storage import EnergyStorage, BatteryModel, SupercapacitorModel, EnergyStorageState
    from vehicle.motor_model import MotorModel, MotorState, create_yasa_p400r


@dataclass
class PowertrainState:
    """Complete powertrain state for one timestep."""
    # Energy storage
    dc_bus_voltage: float  # V
    storage_current: float  # A
    storage_power_loss: float  # W
    energy_remaining: float  # J
    state_of_charge: float  # 0-1
    
    # Motor
    motor_speed: float  # rad/s
    motor_torque: float  # Nm
    motor_current: float  # A
    motor_efficiency: float  # 0-1
    in_field_weakening: bool
    voltage_limited: bool
    
    # Drivetrain output
    wheel_torque: float  # Nm
    wheel_power: float  # W
    
    # Power accounting
    power_electrical: float  # W (from energy storage)
    power_mechanical: float  # W (to wheels)
    drivetrain_loss: float  # W


class PowertrainModel:
    """
    Powertrain model including energy storage, motor, and drivetrain.
    
    This model supports two energy storage types:
    1. Battery: Nearly constant voltage (existing behavior)
    2. Supercapacitor: Voltage decays during discharge
    
    The motor model includes field weakening behavior, which is critical
    for supercapacitor operation where DC bus voltage drops significantly.
    """
    
    def __init__(
        self,
        config: PowertrainProperties,
        energy_storage: Optional[EnergyStorage] = None,
        motor: Optional[MotorModel] = None,
        use_advanced_motor: bool = True
    ):
        """
        Initialize powertrain model.
        
        Args:
            config: Powertrain properties configuration
            energy_storage: Energy storage model (Battery or Supercapacitor)
                           If None, creates default BatteryModel from config
            motor: Motor model with field weakening
                   If None and use_advanced_motor=True, creates YASA P400R
            use_advanced_motor: If True, use advanced motor model with field weakening
        """
        self.config = config
        self.max_power = config.max_power_accumulator_outlet  # 80kW FS limit
        self.gear_ratio = config.gear_ratio
        self.drivetrain_efficiency = config.drivetrain_efficiency
        self.wheel_inertia = config.wheel_inertia
        
        # Energy storage
        if energy_storage is not None:
            self.energy_storage = energy_storage
        else:
            # Create default battery from config
            self.energy_storage = BatteryModel(
                voltage_nominal=config.battery_voltage_nominal,
                internal_resistance=config.battery_internal_resistance,
                capacity_wh=5000.0,  # Default 5 kWh
                min_operating_voltage=config.battery_voltage_nominal * 0.8
            )
        
        # Motor model
        self.use_advanced_motor = use_advanced_motor
        if motor is not None:
            self.motor = motor
        elif use_advanced_motor:
            self.motor = create_yasa_p400r()
        else:
            self.motor = None
        
        # Legacy parameters for backwards compatibility
        self.motor_kt = config.motor_torque_constant
        self.motor_max_current = config.motor_max_current
        self.motor_max_speed = config.motor_max_speed
        self.motor_efficiency = config.motor_efficiency
        self.battery_voltage = config.battery_voltage_nominal
        self.battery_resistance = config.battery_internal_resistance
        
        # State tracking
        self._last_state: Optional[PowertrainState] = None
    
    def reset(self) -> None:
        """Reset energy storage and state."""
        self.energy_storage.reset()
        self._last_state = None
    
    def get_dc_bus_voltage(self) -> float:
        """Get current DC bus voltage from energy storage."""
        return self.energy_storage.get_voltage()
    
    def calculate_torque(
        self,
        requested_torque: float,
        motor_speed: float,
        vehicle_velocity: float,
        dt: float = 0.001,
        update_storage: bool = True
    ) -> Tuple[float, float, float]:
        """
        Calculate available motor torque considering all limits and power constraints.
        
        This method integrates:
        1. Energy storage voltage (may decay for supercaps)
        2. Motor field weakening (voltage-dependent)
        3. Formula Student 80kW power limit
        4. Drivetrain efficiency
        
        Args:
            requested_torque: Requested torque at wheels (N·m)
            motor_speed: Motor angular velocity (rad/s)
            vehicle_velocity: Vehicle velocity (m/s)
            dt: Time step for energy storage update (s)
            update_storage: If True, update energy storage state. Set False during
                           RK4 intermediate calculations to prevent 4x discharge rate.
            
        Returns:
            Tuple of (wheel_torque, motor_current, power_consumed)
            - wheel_torque: Actual torque at wheels (N·m)
            - motor_current: Motor current (A)
            - power_consumed: Power consumed at accumulator outlet (W)
        """
        # Get current DC bus voltage (read-only, doesn't modify state)
        dc_bus_voltage = self.energy_storage.get_voltage()
        
        # Convert wheel torque request to motor torque request
        motor_torque_requested = requested_torque / (self.gear_ratio * self.drivetrain_efficiency)
        
        # Track motor state for field weakening info
        motor_state = None
        
        if self.use_advanced_motor and self.motor is not None:
            # Use advanced motor model with field weakening
            motor_state = self.motor.calculate_operating_point(
                motor_torque_requested,
                motor_speed,
                dc_bus_voltage
            )
            
            actual_motor_torque = motor_state.torque
            motor_current = motor_state.current
            motor_efficiency = motor_state.efficiency
            
        else:
            # Legacy simplified motor model
            # Limit by motor speed (simplified - no field weakening)
            if abs(motor_speed) > self.motor_max_speed:
                motor_torque_requested = 0.0
            
            # Calculate motor current from requested torque
            motor_current_unlimited = motor_torque_requested / self.motor_kt if self.motor_kt > 0 else 0.0
            
            # Apply current limit
            max_current = min(self.motor_max_current, self.max_power / dc_bus_voltage)
            motor_current = np.sign(motor_current_unlimited) * min(abs(motor_current_unlimited), max_current)
            
            actual_motor_torque = motor_current * self.motor_kt
            motor_efficiency = self.motor_efficiency
        
        # Calculate electrical power at accumulator outlet
        electrical_power_unlimited = dc_bus_voltage * motor_current
        
        # Apply Formula Student 80kW power limit (EV 2.2)
        if abs(electrical_power_unlimited) > self.max_power:
            # Scale down to meet power limit
            scale_factor = self.max_power / abs(electrical_power_unlimited)
            motor_current *= scale_factor
            actual_motor_torque *= scale_factor
            electrical_power = np.sign(electrical_power_unlimited) * self.max_power
        else:
            electrical_power = electrical_power_unlimited
        
        # Update energy storage state ONLY if requested
        # During RK4 integration, this should be False for intermediate steps
        # to prevent the supercapacitor from discharging 4x too fast
        if update_storage:
            storage_state = self.energy_storage.update(dt, abs(electrical_power))
        else:
            # Just get current state without modifying it
            storage_state = self.energy_storage.get_state()
        
        # Convert motor torque to wheel torque
        wheel_torque = actual_motor_torque * self.gear_ratio * self.drivetrain_efficiency
        
        # Store state for diagnostics
        self._last_state = PowertrainState(
            dc_bus_voltage=dc_bus_voltage,
            storage_current=storage_state.current if update_storage else motor_current,
            storage_power_loss=storage_state.power_loss,
            energy_remaining=storage_state.energy_remaining,
            state_of_charge=storage_state.state_of_charge,
            motor_speed=motor_speed,
            motor_torque=actual_motor_torque,
            motor_current=motor_current,
            motor_efficiency=motor_efficiency if self.use_advanced_motor else self.motor_efficiency,
            in_field_weakening=motor_state.in_field_weakening if motor_state else False,
            voltage_limited=motor_state.voltage_limited if motor_state else False,
            wheel_torque=wheel_torque,
            wheel_power=wheel_torque * motor_speed / self.gear_ratio,
            power_electrical=electrical_power,
            power_mechanical=wheel_torque * motor_speed / self.gear_ratio,
            drivetrain_loss=abs(electrical_power) * (1 - self.drivetrain_efficiency)
        )
        
        return wheel_torque, motor_current, electrical_power
    
    def update_energy_storage(self, dt: float, power: float) -> None:
        """
        Update energy storage state directly.
        
        This is called once per timestep after RK4 integration completes,
        with the final power value to ensure correct discharge rate.
        
        Args:
            dt: Time step (s)
            power: Power consumed (W)
        """
        storage_state = self.energy_storage.update(dt, abs(power))
        
        # Update the last state with new storage values
        if self._last_state is not None:
            self._last_state = PowertrainState(
                dc_bus_voltage=self.energy_storage.get_voltage(),
                storage_current=storage_state.current,
                storage_power_loss=storage_state.power_loss,
                energy_remaining=storage_state.energy_remaining,
                state_of_charge=storage_state.state_of_charge,
                motor_speed=self._last_state.motor_speed,
                motor_torque=self._last_state.motor_torque,
                motor_current=self._last_state.motor_current,
                motor_efficiency=self._last_state.motor_efficiency,
                in_field_weakening=self._last_state.in_field_weakening,
                voltage_limited=self._last_state.voltage_limited,
                wheel_torque=self._last_state.wheel_torque,
                wheel_power=self._last_state.wheel_power,
                power_electrical=self._last_state.power_electrical,
                power_mechanical=self._last_state.power_mechanical,
                drivetrain_loss=self._last_state.drivetrain_loss
            )
    
    def get_last_state(self) -> Optional[PowertrainState]:
        """Get the last calculated powertrain state."""
        return self._last_state
    
    def calculate_motor_speed(self, wheel_angular_velocity: float) -> float:
        """
        Calculate motor speed from wheel speed.
        
        Args:
            wheel_angular_velocity: Wheel angular velocity (rad/s)
            
        Returns:
            Motor angular velocity (rad/s)
        """
        return wheel_angular_velocity * self.gear_ratio
    
    def calculate_wheel_speed(self, motor_speed: float) -> float:
        """
        Calculate wheel speed from motor speed.
        
        Args:
            motor_speed: Motor angular velocity (rad/s)
            
        Returns:
            Wheel angular velocity (rad/s)
        """
        return motor_speed / self.gear_ratio


def create_powertrain_with_battery(config: PowertrainProperties) -> PowertrainModel:
    """Create a PowertrainModel with battery energy storage."""
    battery = BatteryModel(
        voltage_nominal=config.battery_voltage_nominal,
        internal_resistance=config.battery_internal_resistance,
        capacity_wh=5000.0,
        min_operating_voltage=config.battery_voltage_nominal * 0.8
    )
    return PowertrainModel(config, energy_storage=battery, use_advanced_motor=True)


def create_powertrain_with_supercapacitor(
    config: PowertrainProperties,
    cell_voltage: float = 3.0,
    cell_capacitance: float = 600.0,
    cell_esr: float = 0.7e-3,
    num_cells: int = 200,
    min_operating_voltage: float = 350.0
) -> PowertrainModel:
    """
    Create a PowertrainModel with supercapacitor energy storage.
    
    Default values match C46W-3R0-0600 supercapacitor configuration.
    """
    supercap = SupercapacitorModel(
        cell_voltage=cell_voltage,
        cell_capacitance=cell_capacitance,
        cell_esr=cell_esr,
        num_cells=num_cells,
        min_operating_voltage=min_operating_voltage
    )
    return PowertrainModel(config, energy_storage=supercap, use_advanced_motor=True)
