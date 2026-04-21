"""Motor model with voltage-dependent field weakening.

Based on YASA P400R motor specifications:
- Peak Torque @ 450A: 370 Nm
- Continuous Torque: up to 200 Nm  
- Peak Power @ 700V: 160 kW
- Continuous Power: up to 60 kW
- Maximum Speed: 8000 rpm (838 rad/s)

This module provides a realistic motor model that accounts for:
1. Constant torque region (below base speed)
2. Field weakening / constant power region (above base speed)
3. Voltage-dependent base speed (critical for supercapacitor operation)
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class MotorState:
    """Motor operating state."""
    speed: float  # Motor speed (rad/s)
    torque: float  # Motor torque (Nm)
    current: float  # Motor current (A)
    power_mechanical: float  # Mechanical power output (W)
    power_electrical: float  # Electrical power input (W)
    efficiency: float  # Current operating efficiency
    in_field_weakening: bool  # True if operating in field weakening region
    voltage_limited: bool  # True if voltage saturation is limiting torque


class MotorModel:
    """
    PMSM motor model with field weakening based on YASA P400R.
    
    The motor has two operating regions:
    
    1. Constant Torque Region (0 to base_speed):
       - Full torque available (limited by current)
       - Torque = Kt * I
       
    2. Field Weakening Region (base_speed to max_speed):
       - Torque decreases as speed increases
       - Approximately constant power: P = T * ω = constant
       - Torque = T_base * (base_speed / current_speed)
    
    The base speed is VOLTAGE DEPENDENT:
       - Higher DC bus voltage → higher base speed
       - Lower DC bus voltage → lower base speed (earlier field weakening)
    
    This is critical for supercapacitor operation where voltage drops
    from 600V to ~400V during discharge.
    """
    
    def __init__(
        self,
        peak_torque: float = 370.0,  # Nm @ peak current
        continuous_torque: float = 200.0,  # Nm continuous
        peak_current: float = 450.0,  # A
        continuous_current: float = 200.0,  # A (estimated)
        max_speed: float = 838.0,  # rad/s (8000 rpm)
        rated_voltage: float = 700.0,  # V (voltage for peak power spec)
        peak_power: float = 160e3,  # W (160 kW @ rated voltage)
        efficiency_peak: float = 0.97,  # Peak efficiency
        efficiency_low_load: float = 0.90  # Efficiency at low load
    ):
        """
        Initialize motor model.
        
        Args:
            peak_torque: Peak torque at peak current (Nm)
            continuous_torque: Continuous rated torque (Nm)
            peak_current: Peak current (A)
            continuous_current: Continuous current (A)
            max_speed: Maximum motor speed (rad/s)
            rated_voltage: DC bus voltage for peak power rating (V)
            peak_power: Peak power at rated voltage (W)
            efficiency_peak: Peak efficiency (0-1)
            efficiency_low_load: Efficiency at low load (0-1)
        """
        self.peak_torque = peak_torque
        self.continuous_torque = continuous_torque
        self.peak_current = peak_current
        self.continuous_current = continuous_current
        self.max_speed = max_speed
        self.rated_voltage = rated_voltage
        self.peak_power = peak_power
        self.efficiency_peak = efficiency_peak
        self.efficiency_low_load = efficiency_low_load
        
        # Derived parameters
        # Torque constant: Kt = T / I
        self.torque_constant = peak_torque / peak_current  # ~0.82 Nm/A
        
        # Base speed at rated voltage (where field weakening begins)
        # At base speed: P = T_peak * ω_base = peak_power
        # So: ω_base = peak_power / peak_torque
        self.base_speed_at_rated_voltage = peak_power / peak_torque  # ~432 rad/s
        
        # However, this might exceed max_speed, so we need to check
        # Actually, for YASA P400R, peak power is achieved in field weakening
        # Let's estimate base speed from voltage/back-EMF relationship
        # At max speed with rated voltage, the motor is at voltage limit
        # So back-EMF constant: Ke = V_rated / (omega_max * sqrt(3) * modulation_index)
        # Simplified: base_speed scales linearly with voltage
        # At 700V, base speed is approximately where torque starts to drop
        # From datasheet analysis, this is around 400-450 rad/s
        self.base_speed_at_rated_voltage = 430.0  # rad/s (estimated from P400R characteristics)
    
    def calculate_base_speed(self, dc_bus_voltage: float) -> float:
        """
        Calculate base speed (transition to field weakening) at given voltage.
        
        Base speed scales linearly with DC bus voltage since back-EMF
        is proportional to speed, and available voltage determines max back-EMF.
        
        Args:
            dc_bus_voltage: DC bus voltage from energy storage (V)
            
        Returns:
            Base speed (rad/s) at this voltage
        """
        # Base speed scales with voltage
        return self.base_speed_at_rated_voltage * (dc_bus_voltage / self.rated_voltage)
    
    def calculate_max_torque(
        self,
        motor_speed: float,
        dc_bus_voltage: float,
        use_peak: bool = True
    ) -> Tuple[float, bool, bool]:
        """
        Calculate maximum available torque at given speed and voltage.
        
        Args:
            motor_speed: Motor angular velocity (rad/s)
            dc_bus_voltage: DC bus voltage (V)
            use_peak: If True, use peak torque; if False, use continuous
            
        Returns:
            Tuple of:
            - max_torque: Maximum available torque (Nm)
            - in_field_weakening: True if in field weakening region
            - voltage_limited: True if voltage is limiting torque
        """
        motor_speed = abs(motor_speed)
        
        # Select torque limit
        torque_limit = self.peak_torque if use_peak else self.continuous_torque
        
        # Calculate base speed at current voltage
        base_speed = self.calculate_base_speed(dc_bus_voltage)
        
        # Hard speed limit at motor max speed
        # The motor physically cannot produce torque above this speed
        # Use a very steep rolloff in a narrow band to prevent numerical issues
        if motor_speed >= self.max_speed:
            # At or beyond max speed: torque drops to zero very quickly
            # Use steep exponential decay in a 1% band for numerical stability
            if motor_speed > self.max_speed * 1.01:
                return 0.0, True, True
            else:
                # Transition region (max_speed to 1.01*max_speed)
                # Torque decays from field-weakening value to zero
                overspeed_fraction = (motor_speed - self.max_speed) / (0.01 * self.max_speed)
                torque_at_max = torque_limit * (base_speed / self.max_speed) if base_speed < self.max_speed else torque_limit
                return torque_at_max * (1.0 - overspeed_fraction), True, True
        
        # Constant torque region
        if motor_speed <= base_speed:
            return torque_limit, False, False
        
        # Field weakening region: torque decreases to maintain constant power
        # T = T_base * (base_speed / current_speed)
        torque_field_weakening = torque_limit * (base_speed / motor_speed)
        
        # In field weakening, we're voltage limited
        return torque_field_weakening, True, True
    
    def calculate_efficiency(
        self,
        torque: float,
        speed: float
    ) -> float:
        """
        Calculate motor efficiency at operating point.
        
        Simplified efficiency model - real motors have efficiency maps.
        Efficiency is highest at rated load and decreases at low and high loads.
        
        Args:
            torque: Motor torque (Nm)
            speed: Motor speed (rad/s)
            
        Returns:
            Efficiency (0-1)
        """
        if speed < 1.0 or torque < 1.0:
            return self.efficiency_low_load
        
        # Power at this operating point
        power = torque * speed
        
        # Normalized power (0 to 1, relative to peak)
        power_normalized = power / self.peak_power
        
        # Simple efficiency curve: peaks around 50-80% load
        # η = η_low + (η_peak - η_low) * f(power_normalized)
        # where f peaks around 0.6
        optimal_load = 0.6
        width = 0.4
        
        efficiency_factor = np.exp(-((power_normalized - optimal_load) / width) ** 2)
        efficiency = self.efficiency_low_load + (self.efficiency_peak - self.efficiency_low_load) * efficiency_factor
        
        return np.clip(efficiency, self.efficiency_low_load, self.efficiency_peak)
    
    def calculate_operating_point(
        self,
        requested_torque: float,
        motor_speed: float,
        dc_bus_voltage: float
    ) -> MotorState:
        """
        Calculate motor operating point given torque request and constraints.
        
        Args:
            requested_torque: Requested motor torque (Nm)
            motor_speed: Motor angular velocity (rad/s)
            dc_bus_voltage: DC bus voltage from energy storage (V)
            
        Returns:
            MotorState with actual operating point
        """
        motor_speed = abs(motor_speed)
        
        # Get maximum available torque at this speed and voltage
        max_torque, in_field_weakening, voltage_limited = self.calculate_max_torque(
            motor_speed, dc_bus_voltage, use_peak=True
        )
        
        # Limit torque to maximum available
        actual_torque = min(abs(requested_torque), max_torque)
        actual_torque = np.sign(requested_torque) * actual_torque if requested_torque != 0 else actual_torque
        
        # Calculate current: I = T / Kt
        current = abs(actual_torque) / self.torque_constant
        
        # Calculate mechanical power
        power_mechanical = actual_torque * motor_speed
        
        # Calculate efficiency
        efficiency = self.calculate_efficiency(abs(actual_torque), motor_speed)
        
        # Calculate electrical power (input)
        if efficiency > 0:
            power_electrical = power_mechanical / efficiency
        else:
            power_electrical = 0.0
        
        return MotorState(
            speed=motor_speed,
            torque=actual_torque,
            current=current,
            power_mechanical=power_mechanical,
            power_electrical=power_electrical,
            efficiency=efficiency,
            in_field_weakening=in_field_weakening,
            voltage_limited=voltage_limited and abs(requested_torque) > max_torque
        )


# Pre-configured motor for YASA P400R
def create_yasa_p400r() -> MotorModel:
    """Create a MotorModel configured for YASA P400R specifications."""
    return MotorModel(
        peak_torque=370.0,  # Nm @ 450A
        continuous_torque=200.0,  # Nm
        peak_current=450.0,  # A
        continuous_current=200.0,  # A (estimated)
        max_speed=838.0,  # rad/s (8000 rpm)
        rated_voltage=700.0,  # V
        peak_power=160e3,  # W (160 kW)
        efficiency_peak=0.97,
        efficiency_low_load=0.90
    )


def create_motor_from_config(config) -> MotorModel:
    """Build a MotorModel using fields from PowertrainProperties.

    Config-driven fields:
      - ``motor_torque_constant`` (Kt, N.m/A) and ``motor_max_current`` (A)
        together define ``peak_torque = Kt * I_peak``.
      - ``motor_max_speed`` (rad/s) caps motor speed.
      - ``motor_efficiency`` (0-1) is used for both peak and low-load points
        (no separate low-load efficiency in config).
      - ``battery_voltage_nominal`` (V) is used as the motor's rated voltage
        so field-weakening base speed is correct for the actual bus voltage.

    Defaults are used for fields absent from the config:
      - continuous_current = 200 A (or peak_current if smaller)
      - rated_voltage = battery_voltage_nominal, falling back to 700 V
      - peak_power scales with rated_voltage so that the torque/speed envelope
        matches the YASA P400R's 160 kW @ 700 V datapoint when the bus is at
        700 V, and drops proportionally at lower bus voltages.
    """
    kt = float(getattr(config, "motor_torque_constant", 0.82))
    peak_current = float(getattr(config, "motor_max_current", 450.0))
    max_speed = float(getattr(config, "motor_max_speed", 838.0))
    efficiency = float(getattr(config, "motor_efficiency", 0.95))
    rated_voltage = float(getattr(config, "battery_voltage_nominal", 700.0))

    # Derived envelope.
    peak_torque = kt * peak_current
    continuous_current = min(200.0, peak_current)
    continuous_torque = kt * continuous_current

    # Peak power scales with both rated_voltage and torque. At 700 V, Kt=0.82,
    # I=450, max_speed=838 rad/s this evaluates to ~155 kW, close to the
    # YASA P400R datasheet value of 160 kW @ 700 V.
    # (P_max = T_peak * omega_base where omega_base = max_speed/2 at full rated V.)
    peak_power = peak_torque * (max_speed / 2.0) * (rated_voltage / 700.0)
    # Ensure the FS 80 kW rule is at least reachable at the inverter electrical
    # input (the accumulator outlet cap is enforced separately in the solver).
    peak_power = max(peak_power, 80_000.0)

    return MotorModel(
        peak_torque=peak_torque,
        continuous_torque=continuous_torque,
        peak_current=peak_current,
        continuous_current=continuous_current,
        max_speed=max_speed,
        rated_voltage=rated_voltage,
        peak_power=peak_power,
        efficiency_peak=efficiency,
        efficiency_low_load=max(0.85, efficiency - 0.05),
    )
