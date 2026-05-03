"""Motor electrical envelopes applied at JSON load time.

The written report may still cite YASA P400R + BAMOCAR PG-D3 where appropriate;
the simulation can use a different envelope via ``motor_simulation_preset`` in
the vehicle JSON (see :func:`apply_motor_preset`).

Replace ``p600r_provisional`` numbers when the team P600R datasheet is
available — there is no public YASA ``P600R`` product sheet in-repo.
"""

from __future__ import annotations

from typing import Any, Dict

# Keys must match :class:`config.vehicle_config.PowertrainProperties` fields only.
PRESETS: Dict[str, Dict[str, Any]] = {
    # Matches thesis table / inverter RMS-oriented torque cap (BAMOCAR family).
    "p400r_report": {
        "motor_torque_constant": 0.822,
        "motor_max_current": 285.0,
        "motor_max_speed": 838.0,
    },
    # Placeholder until P600R datasheet: higher Kt at same inverter RMS cap.
    "p600r_provisional": {
        "motor_torque_constant": 0.95,
        "motor_max_current": 285.0,
        "motor_max_speed": 838.0,
    },
}


def apply_motor_preset(data: dict, preset_name: str | None) -> None:
    """Shallow-merge preset powertrain fields into ``data['powertrain']``."""
    if not preset_name:
        return
    key = str(preset_name).strip().lower()
    ov = PRESETS.get(key)
    if ov is None:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(
            f"Unknown motor_simulation_preset {preset_name!r}. "
            f"Choose one of: {known}"
        )
    pt = data.setdefault("powertrain", {})
    for k, v in ov.items():
        pt[k] = v
