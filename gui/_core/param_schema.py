"""Schema describing which config parameters are editable in the GUI.

One flat list of fields grouped by section, each with:
  - section / key        : addresses the field as data[section][key]
  - label / unit / help  : for the widget
  - min / max / step     : widget ranges (practical FS bounds, drawn from
                            run_quick_optimization.py where relevant)
  - widget               : "number" (default), "bool", or "choice"
  - choices              : for "choice" widgets

Sweep and optimiser pages reuse this list to let the user pick parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ParamSpec:
    section: str
    key: str
    label: str
    unit: str = ""
    help: str = ""
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    widget: str = "number"
    choices: Tuple[str, ...] = ()

    @property
    def dotted(self) -> str:
        return f"{self.section}.{self.key}"


# Ordered list: sidebar sections follow this order, expanders group by section.
PARAMS: List[ParamSpec] = [
    # --- Mass ---
    ParamSpec("mass", "total_mass", "Total mass", "kg", min=120.0, max=350.0, step=1.0,
              help="Total vehicle mass including driver."),
    ParamSpec("mass", "cg_x", "CG X (from front axle)", "m", min=0.1, max=2.0, step=0.01,
              help="Longitudinal CG position measured from the front axle."),
    ParamSpec("mass", "cg_z", "CG height", "m", min=0.1, max=0.6, step=0.01,
              help="CG vertical position above ground."),
    ParamSpec("mass", "wheelbase", "Wheelbase", "m", min=1.4, max=2.0, step=0.001),
    ParamSpec("mass", "front_track", "Front track", "m", min=1.0, max=1.5, step=0.01),
    ParamSpec("mass", "rear_track", "Rear track", "m", min=1.0, max=1.5, step=0.01),
    ParamSpec("mass", "i_yaw", "Yaw inertia", "kg.m^2", min=50.0, max=300.0, step=1.0),
    ParamSpec("mass", "i_pitch", "Pitch inertia", "kg.m^2", min=50.0, max=400.0, step=1.0),
    ParamSpec("mass", "unsprung_mass_front", "Unsprung mass (front)", "kg", min=2.0, max=30.0, step=0.5),
    ParamSpec("mass", "unsprung_mass_rear", "Unsprung mass (rear)", "kg", min=2.0, max=30.0, step=0.5),

    # --- Tires ---
    ParamSpec("tires", "radius_loaded", "Loaded radius", "m", min=0.18, max=0.30, step=0.001),
    ParamSpec("tires", "mass", "Tire mass", "kg", min=1.0, max=10.0, step=0.1),
    ParamSpec("tires", "mu_max", "Max friction (mu_max)", "-", min=0.5, max=2.2, step=0.01,
              help="Peak longitudinal friction coefficient."),
    ParamSpec("tires", "mu_slip_optimal", "Optimal slip ratio", "-", min=0.05, max=0.30, step=0.005),
    ParamSpec("tires", "rolling_resistance_coeff", "Rolling resistance coeff", "-",
              min=0.005, max=0.05, step=0.001),
    ParamSpec("tires", "tire_model_type", "Tire model", "", widget="choice",
              choices=("pacejka", "simple")),
    ParamSpec("tires", "pacejka_C", "Pacejka C (shape)", "-", min=1.0, max=2.2, step=0.01),
    ParamSpec("tires", "pacejka_E", "Pacejka E (curvature)", "-", min=-2.0, max=1.0, step=0.01),
    ParamSpec("tires", "pacejka_pDx1", "Pacejka pDx1", "-", min=0.5, max=2.5, step=0.01),
    ParamSpec("tires", "pacejka_pDx2", "Pacejka pDx2 (load sens.)", "-", min=-0.5, max=0.2, step=0.01),
    ParamSpec("tires", "pacejka_pKx1", "Pacejka pKx1", "N/rad", min=5000.0, max=80000.0, step=500.0),
    ParamSpec("tires", "pacejka_pKx2", "Pacejka pKx2", "N/rad", min=-10000.0, max=5000.0, step=100.0),
    ParamSpec("tires", "pacejka_Fz0", "Pacejka Fz0 (nominal load)", "N", min=500.0, max=3000.0, step=50.0),

    # --- Powertrain ---
    ParamSpec("powertrain", "motor_torque_constant", "Motor Kt", "N.m/A", min=0.1, max=2.0, step=0.01),
    ParamSpec("powertrain", "motor_max_current", "Motor max current", "A", min=50.0, max=800.0, step=5.0),
    ParamSpec("powertrain", "motor_max_speed", "Motor max speed", "rad/s", min=200.0, max=2000.0, step=10.0),
    ParamSpec("powertrain", "motor_efficiency", "Motor efficiency", "-", min=0.80, max=0.99, step=0.005),
    ParamSpec("powertrain", "battery_voltage_nominal", "Battery voltage (nominal)", "V",
              min=100.0, max=800.0, step=5.0),
    ParamSpec("powertrain", "battery_internal_resistance", "Battery resistance", "ohm",
              min=0.001, max=0.5, step=0.001,
              help="Pack + bus equivalent resistance (supercap stacks can be ~0.1–0.2 Ω)."),
    ParamSpec("powertrain", "battery_max_current", "Battery max current", "A",
              min=50.0, max=500.0, step=5.0),
    ParamSpec("powertrain", "gear_ratio", "Gear ratio", "-", min=2.0, max=15.0, step=0.1),
    ParamSpec("powertrain", "drivetrain_efficiency", "Drivetrain efficiency", "-",
              min=0.80, max=0.99, step=0.005),
    ParamSpec("powertrain", "differential_ratio", "Differential ratio", "-", min=0.5, max=5.0, step=0.1),
    ParamSpec("powertrain", "max_power_accumulator_outlet", "Max accumulator power", "W",
              min=10000.0, max=80000.0, step=1000.0,
              help="EV 2.2 rule: must not exceed 80 kW."),
    ParamSpec("powertrain", "wheel_inertia", "Wheel inertia (per driven wheel)", "kg.m^2",
              min=0.01, max=1.0, step=0.01,
              help="Rotational inertia of one driven wheel + hub; total rear inertia is 2x this."),
    ParamSpec("powertrain", "driveline_compliance_enabled", "Driveline compliance", "",
              widget="bool",
              help="Model halfshafts + gearbox as a torsional spring-damper between "
                   "motor and wheel. Off = rigid coupling. Enable for realistic launch "
                   "transients, smoother torque trace, and to see driveline ringing."),
    ParamSpec("powertrain", "motor_inertia", "Motor rotor inertia", "kg.m^2",
              min=0.001, max=0.5, step=0.001,
              help="YASA P400R datasheet rotor inertia is ~0.077 kg.m^2. Reflected onto the "
                   "wheel hub as I_motor * gear_ratio^2, so it dominates rotating inertia."),
    ParamSpec("powertrain", "driveline_stiffness", "Driveline stiffness", "N.m/rad",
              min=500.0, max=100000.0, step=500.0,
              help="Combined halfshaft + gearbox torsional stiffness at the wheel hub. "
                   "Only active when driveline compliance is enabled."),
    ParamSpec("powertrain", "driveline_damping", "Driveline damping", "N.m.s/rad",
              min=0.0, max=500.0, step=1.0,
              help="Viscous damping in the driveline spring. Tune with stiffness for critical or "
                   "near-critical damping."),
    ParamSpec("powertrain", "energy_storage_type", "Energy storage", "", widget="choice",
              choices=("battery", "supercapacitor")),
    ParamSpec("powertrain", "supercap_cell_voltage", "Supercap cell voltage", "V",
              min=1.0, max=5.0, step=0.1),
    ParamSpec("powertrain", "supercap_cell_capacitance", "Supercap cell capacitance", "F",
              min=10.0, max=3000.0, step=10.0),
    ParamSpec("powertrain", "supercap_cell_esr", "Supercap cell ESR", "ohm",
              min=1e-4, max=0.01, step=1e-4),
    ParamSpec("powertrain", "supercap_num_cells", "Supercap # cells", "",
              min=10.0, max=500.0, step=1.0),
    ParamSpec("powertrain", "supercap_min_voltage", "Supercap min voltage", "V",
              min=50.0, max=600.0, step=5.0),

    # --- Aerodynamics ---
    ParamSpec("aerodynamics", "cda", "Drag area (CdA)", "m^2", min=0.2, max=2.0, step=0.01),
    ParamSpec("aerodynamics", "cl_front", "Downforce coeff (front)", "-",
              min=0.0, max=3.0, step=0.05,
              help="Positive = downforce (adds normal load). Typical FS front wing: 0-2."),
    ParamSpec("aerodynamics", "cl_rear", "Downforce coeff (rear)", "-",
              min=0.0, max=3.0, step=0.05,
              help="Positive = downforce (adds normal load). Typical FS rear wing: 0-3."),
    ParamSpec("aerodynamics", "air_density", "Air density", "kg/m^3", min=0.9, max=1.4, step=0.005),

    # --- Suspension ---
    ParamSpec("suspension", "anti_squat_ratio", "Anti-squat ratio", "-", min=0.0, max=1.0, step=0.01),
    ParamSpec("suspension", "ride_height_front", "Ride height (front)", "m", min=0.02, max=0.20, step=0.005),
    ParamSpec("suspension", "ride_height_rear", "Ride height (rear)", "m", min=0.02, max=0.20, step=0.005),
    ParamSpec("suspension", "wheel_rate_front", "Wheel rate (front)", "N/m",
              min=5000.0, max=80000.0, step=500.0),
    ParamSpec("suspension", "wheel_rate_rear", "Wheel rate (rear)", "N/m",
              min=5000.0, max=80000.0, step=500.0),

    # --- Control ---
    ParamSpec("control", "launch_torque_limit", "Launch torque limit", "N.m",
              min=100.0, max=2000.0, step=10.0),
    ParamSpec("control", "traction_control_enabled", "Traction control", "", widget="bool"),

    # --- Environment ---
    ParamSpec("environment", "air_density", "Air density", "kg/m^3", min=0.9, max=1.4, step=0.005),
    ParamSpec("environment", "ambient_temperature", "Ambient temperature", "C",
              min=-20.0, max=50.0, step=0.5),
    ParamSpec("environment", "track_grade", "Track grade", "rad", min=-0.1, max=0.1, step=0.001),
    ParamSpec("environment", "wind_speed", "Wind speed", "m/s", min=-15.0, max=15.0, step=0.1),
    ParamSpec("environment", "surface_mu_scaling", "Surface mu scaling", "-",
              min=0.3, max=1.2, step=0.01,
              help="Multiplier applied to tire friction (e.g. 0.6 for wet)."),

    # --- Simulation ---
    ParamSpec("simulation", "dt", "Time step", "s", min=1e-4, max=0.05, step=1e-4,
              help="Smaller = more accurate, slower. 0.001 s is default."),
    ParamSpec("simulation", "max_time", "Max simulation time", "s", min=5.0, max=60.0, step=1.0),
    ParamSpec("simulation", "target_distance", "Target distance", "m", min=25.0, max=300.0, step=1.0),
]


SECTION_ORDER: List[str] = [
    "mass", "tires", "powertrain", "aerodynamics",
    "suspension", "control", "environment", "simulation",
]

SECTION_LABELS: Dict[str, str] = {
    "mass": "Mass & geometry",
    "tires": "Tires",
    "powertrain": "Powertrain",
    "aerodynamics": "Aerodynamics",
    "suspension": "Suspension",
    "control": "Control",
    "environment": "Environment",
    "simulation": "Simulation",
}


def params_by_section() -> Dict[str, List[ParamSpec]]:
    """Group the flat PARAMS list by section, preserving order."""
    out: Dict[str, List[ParamSpec]] = {s: [] for s in SECTION_ORDER}
    for p in PARAMS:
        out.setdefault(p.section, []).append(p)
    return out


def get_value(data: Dict, spec: ParamSpec, default: Any = None) -> Any:
    """Fetch data[section][key] with a fallback."""
    return data.get(spec.section, {}).get(spec.key, default)


def set_value(data: Dict, spec: ParamSpec, value: Any) -> None:
    """Set data[section][key] = value, creating the section dict if needed."""
    data.setdefault(spec.section, {})[spec.key] = value


def find(dotted: str) -> Optional[ParamSpec]:
    """Look up a ParamSpec by 'section.key'."""
    for p in PARAMS:
        if p.dotted == dotted:
            return p
    return None


# Numeric-only subset, useful for the sweep + optimiser pages.
NUMERIC_PARAMS: List[ParamSpec] = [p for p in PARAMS if p.widget == "number"]
