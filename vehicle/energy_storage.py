"""Energy storage models for acceleration simulation.

This module provides abstract base class and concrete implementations for:
- Battery (constant voltage, existing behavior)
- Supercapacitor (voltage decay during discharge)

Based on supercapacitor model from main.m provided by the electrical engineer.
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class EnergyStorageState:
    """State of the energy storage system."""
    voltage: float  # Current terminal voltage (V)
    current: float  # Current draw (A)
    power_output: float  # Power delivered to inverter (W)
    power_loss: float  # Power lost to internal resistance (W)
    energy_remaining: float  # Remaining energy (J)
    state_of_charge: float  # 0.0 to 1.0


class EnergyStorage(ABC):
    """Abstract base class for energy storage systems."""
    
    @abstractmethod
    def get_voltage(self) -> float:
        """Get current terminal voltage."""
        pass
    
    @abstractmethod
    def get_state(self) -> EnergyStorageState:
        """Get current state of the energy storage."""
        pass
    
    @abstractmethod
    def update(self, dt: float, power_demanded: float) -> EnergyStorageState:
        """
        Update energy storage state for one timestep.
        
        Args:
            dt: Time step (s)
            power_demanded: Power demanded by inverter (W)
            
        Returns:
            Updated state after this timestep
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset to initial state (fully charged)."""
        pass
    
    @property
    @abstractmethod
    def initial_voltage(self) -> float:
        """Initial voltage when fully charged."""
        pass
    
    @property
    @abstractmethod
    def min_voltage(self) -> float:
        """Minimum operating voltage (inverter threshold)."""
        pass


class BatteryModel(EnergyStorage):
    """
    Battery energy storage model.
    
    Simplified model assuming nearly constant voltage throughout discharge.
    This is valid for short-duration events like the 75m acceleration
    where state of charge change is minimal (~1-2%).
    
    Attributes:
        voltage_nominal: Nominal battery voltage (V)
        internal_resistance: Battery internal resistance (Ω)
        capacity_wh: Battery capacity (Wh) - for SoC tracking only
    """
    
    def __init__(
        self,
        voltage_nominal: float = 300.0,
        internal_resistance: float = 0.01,
        capacity_wh: float = 5000.0,  # 5 kWh typical for FS
        min_operating_voltage: float = 250.0
    ):
        """
        Initialize battery model.
        
        Args:
            voltage_nominal: Nominal voltage (V)
            internal_resistance: Internal resistance (Ω)
            capacity_wh: Capacity in Wh (for SoC tracking)
            min_operating_voltage: Minimum voltage before cutoff (V)
        """
        self._voltage_nominal = voltage_nominal
        self._internal_resistance = internal_resistance
        self._capacity_j = capacity_wh * 3600  # Convert to Joules
        self._min_voltage = min_operating_voltage
        
        # State variables
        self._energy_remaining = self._capacity_j
        self._current = 0.0
        self._power_output = 0.0
        self._power_loss = 0.0
    
    @property
    def initial_voltage(self) -> float:
        return self._voltage_nominal
    
    @property
    def min_voltage(self) -> float:
        return self._min_voltage
    
    def get_voltage(self) -> float:
        """
        Get terminal voltage.
        
        For batteries, voltage is nearly constant with small sag under load.
        V_terminal = V_nominal - I * R_internal
        """
        return self._voltage_nominal - self._current * self._internal_resistance
    
    def get_state(self) -> EnergyStorageState:
        return EnergyStorageState(
            voltage=self.get_voltage(),
            current=self._current,
            power_output=self._power_output,
            power_loss=self._power_loss,
            energy_remaining=self._energy_remaining,
            state_of_charge=self._energy_remaining / self._capacity_j
        )
    
    def update(self, dt: float, power_demanded: float) -> EnergyStorageState:
        """
        Update battery state.
        
        Battery maintains nearly constant voltage, so current scales with power.
        """
        # Calculate current needed for demanded power
        # P = V * I, so I = P / V (using terminal voltage)
        # This is iterative since V depends on I, but for small R, one iteration is fine
        self._current = power_demanded / self._voltage_nominal
        
        # Terminal voltage with resistive drop
        v_terminal = self.get_voltage()
        
        # Actual power output (slightly less due to resistance)
        self._power_output = v_terminal * self._current
        
        # Power lost to internal resistance
        self._power_loss = self._current ** 2 * self._internal_resistance
        
        # Energy consumed (from battery's perspective)
        energy_consumed = power_demanded * dt
        self._energy_remaining -= energy_consumed
        
        return self.get_state()
    
    def reset(self) -> None:
        """Reset to fully charged state."""
        self._energy_remaining = self._capacity_j
        self._current = 0.0
        self._power_output = 0.0
        self._power_loss = 0.0


class SupercapacitorModel(EnergyStorage):
    """
    Supercapacitor energy storage model.
    
    Based on the MATLAB model (main.m) provided by the electrical engineer.
    Models voltage decay during constant-power discharge with ESR losses.
    
    Key equations from main.m:
        dV/dt = -P/(C*V) - P²*ESR/(C*V³)
        
    Where:
        V = pack voltage
        P = constant power output
        C = total pack capacitance (series reduces this)
        ESR = total equivalent series resistance (series adds this)
    
    Supercapacitor: C46W-3R0-0600
        - Cell voltage: 3.0 V
        - Cell capacitance: 600 F
        - Cell ESR: 0.7 mΩ
        - Configuration: 200 cells in series
    
    Attributes:
        cell_voltage: Voltage per cell (V)
        cell_capacitance: Capacitance per cell (F)
        cell_esr: ESR per cell (Ω)
        num_cells: Number of cells in series
    """
    
    def __init__(
        self,
        cell_voltage: float = 3.0,
        cell_capacitance: float = 600.0,
        cell_esr: float = 0.7e-3,
        num_cells: int = 200,
        min_operating_voltage: float = 350.0  # Inverter minimum threshold
    ):
        """
        Initialize supercapacitor model.
        
        Args:
            cell_voltage: Nominal voltage per cell (V)
            cell_capacitance: Capacitance per cell (F)
            cell_esr: ESR per cell (Ω)
            num_cells: Number of cells in series
            min_operating_voltage: Minimum inverter operating voltage (V)
        """
        # Cell parameters
        self._cell_voltage = cell_voltage
        self._cell_capacitance = cell_capacitance
        self._cell_esr = cell_esr
        self._num_cells = num_cells
        self._min_voltage = min_operating_voltage
        
        # Pack parameters (series configuration)
        self._initial_voltage = cell_voltage * num_cells  # 3V * 200 = 600V
        self._total_capacitance = cell_capacitance / num_cells  # 600F / 200 = 3F
        self._total_esr = cell_esr * num_cells  # 0.7mΩ * 200 = 0.14Ω
        
        # Initial energy: E = 0.5 * C * V²
        self._initial_energy = 0.5 * self._total_capacitance * self._initial_voltage ** 2
        
        # State variables
        self._voltage = self._initial_voltage  # Current voltage (decays)
        self._current = 0.0
        self._power_output = 0.0
        self._power_loss = 0.0
        self._energy_remaining = self._initial_energy
    
    @property
    def initial_voltage(self) -> float:
        return self._initial_voltage
    
    @property
    def min_voltage(self) -> float:
        return self._min_voltage
    
    @property
    def total_capacitance(self) -> float:
        """Total pack capacitance (F)."""
        return self._total_capacitance
    
    @property
    def total_esr(self) -> float:
        """Total pack ESR (Ω)."""
        return self._total_esr
    
    def get_voltage(self) -> float:
        """
        Get terminal voltage.
        
        For supercapacitors, voltage decays as charge is removed.
        Terminal voltage also has resistive drop under load.
        """
        # Terminal voltage = capacitor voltage - ESR drop
        return self._voltage - self._current * self._total_esr
    
    def get_state(self) -> EnergyStorageState:
        # Calculate SoC based on voltage (for capacitor: E ∝ V²)
        # SoC = (V² - Vmin²) / (Vmax² - Vmin²)
        v_max = self._initial_voltage
        v_min = self._min_voltage
        v_current = self._voltage
        
        soc = (v_current ** 2 - v_min ** 2) / (v_max ** 2 - v_min ** 2)
        soc = np.clip(soc, 0.0, 1.0)
        
        return EnergyStorageState(
            voltage=self.get_voltage(),
            current=self._current,
            power_output=self._power_output,
            power_loss=self._power_loss,
            energy_remaining=self._energy_remaining,
            state_of_charge=soc
        )
    
    def update(self, dt: float, power_demanded: float) -> EnergyStorageState:
        """
        Update supercapacitor state using the ODE from main.m.
        
        The voltage decays according to:
            dV/dt = -P/(C*V) - P²*ESR/(C*V³)
        
        This is integrated using a simple Euler step (sufficient for small dt).
        """
        if self._voltage <= self._min_voltage:
            # Below minimum voltage - cannot deliver power
            self._current = 0.0
            self._power_output = 0.0
            self._power_loss = 0.0
            return self.get_state()
        
        # Current required to deliver demanded power
        # P = V * I, so I = P / V (using capacitor voltage, not terminal)
        self._current = power_demanded / self._voltage
        
        # Power lost to ESR: P_loss = I² * R
        self._power_loss = self._current ** 2 * self._total_esr
        
        # Actual power delivered (after ESR loss)
        self._power_output = power_demanded - self._power_loss
        
        # Voltage decay from the ODE in main.m:
        # dV/dt = -P/(C*V) - P²*ESR/(C*V³)
        C = self._total_capacitance
        V = self._voltage
        P = power_demanded
        ESR = self._total_esr
        
        dV_dt = -P / (C * V) - (P ** 2 * ESR) / (C * V ** 3)
        
        # Euler integration (could use RK4 for more accuracy, but dt is small)
        self._voltage += dV_dt * dt
        
        # Ensure voltage doesn't go below minimum
        self._voltage = max(self._voltage, self._min_voltage * 0.9)  # Allow slight undershoot
        
        # Update remaining energy: E = 0.5 * C * V²
        self._energy_remaining = 0.5 * self._total_capacitance * self._voltage ** 2
        
        return self.get_state()
    
    def reset(self) -> None:
        """Reset to fully charged state (600V)."""
        self._voltage = self._initial_voltage
        self._current = 0.0
        self._power_output = 0.0
        self._power_loss = 0.0
        self._energy_remaining = self._initial_energy


def create_energy_storage(storage_type: str, config: dict) -> EnergyStorage:
    """
    Factory function to create energy storage from configuration.
    
    Args:
        storage_type: "battery" or "supercapacitor"
        config: Dictionary of configuration parameters
        
    Returns:
        EnergyStorage instance
    """
    if storage_type.lower() == "battery":
        return BatteryModel(
            voltage_nominal=config.get("voltage_nominal", 300.0),
            internal_resistance=config.get("internal_resistance", 0.01),
            capacity_wh=config.get("capacity_wh", 5000.0),
            min_operating_voltage=config.get("min_operating_voltage", 250.0)
        )
    elif storage_type.lower() == "supercapacitor":
        return SupercapacitorModel(
            cell_voltage=config.get("cell_voltage", 3.0),
            cell_capacitance=config.get("cell_capacitance", 600.0),
            cell_esr=config.get("cell_esr", 0.7e-3),
            num_cells=config.get("num_cells", 200),
            min_operating_voltage=config.get("min_operating_voltage", 350.0)
        )
    else:
        raise ValueError(f"Unknown energy storage type: {storage_type}")
