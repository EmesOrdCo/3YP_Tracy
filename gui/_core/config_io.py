"""Load, save, and convert vehicle configuration JSON files for the GUI.

Mirrors the behaviour of config.config_loader.load_config but:
  - Returns a plain dict (easier to edit via widgets) in addition to a VehicleConfig.
  - Does not raise on validation failure; returns the error list instead so the
    UI can display it inline.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict, List, Tuple

from . import CONFIG_DIR
from config.vehicle_config import (
    AerodynamicsProperties,
    ControlProperties,
    EnvironmentProperties,
    MassProperties,
    PowertrainProperties,
    SuspensionProperties,
    TireProperties,
    VehicleConfig,
)


SECTION_CLASSES = {
    "mass": MassProperties,
    "tires": TireProperties,
    "powertrain": PowertrainProperties,
    "aerodynamics": AerodynamicsProperties,
    "suspension": SuspensionProperties,
    "control": ControlProperties,
    "environment": EnvironmentProperties,
}


def list_configs() -> List[str]:
    """Return JSON config filenames (without extension) in config/vehicle_configs/."""
    if not CONFIG_DIR.exists():
        return []
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))


def config_path(name: str) -> Path:
    """Return the absolute path to a named JSON config."""
    if name.endswith(".json"):
        name = name[:-5]
    return CONFIG_DIR / f"{name}.json"


def load_as_dict(name: str) -> Dict:
    """Load a named config from config/vehicle_configs/ as a nested dict."""
    with open(config_path(name), "r") as f:
        return json.load(f)


def save_config(name: str, data: Dict) -> Path:
    """Persist a nested config dict as JSON. Returns the written path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out = config_path(name)
    with open(out, "w") as f:
        json.dump(data, f, indent=2)
    return out


def dict_to_config(data: Dict) -> VehicleConfig:
    """Build a VehicleConfig from a nested dict (does not run validation).

    Unknown keys in each section are ignored so old configs (e.g. files with
    the retired ``control.target_slip_ratio`` field) still load cleanly.
    """
    def _filter(cls, section: Dict) -> Dict:
        allowed = set(cls.__dataclass_fields__.keys())
        return {k: v for k, v in (section or {}).items() if k in allowed}

    sections = {
        key: cls(**_filter(cls, data.get(key, {})))
        for key, cls in SECTION_CLASSES.items()
    }
    sim_params = data.get("simulation", {})
    return VehicleConfig(
        **sections,
        dt=sim_params.get("dt", 0.001),
        max_time=sim_params.get("max_time", 30.0),
        target_distance=sim_params.get("target_distance", 75.0),
    )


def config_to_dict(config: VehicleConfig) -> Dict:
    """Round-trip a VehicleConfig back to a nested JSON-serialisable dict."""
    out: Dict = {}
    for key in SECTION_CLASSES:
        section = getattr(config, key)
        out[key] = {
            field: getattr(section, field) for field in section.__dataclass_fields__
        }
    out["simulation"] = {
        "dt": config.dt,
        "max_time": config.max_time,
        "target_distance": config.target_distance,
    }
    return out


def validate(data: Dict) -> Tuple[VehicleConfig | None, List[str]]:
    """Try to build + validate a config. Returns (config, error_list)."""
    try:
        cfg = dict_to_config(data)
    except TypeError as exc:
        return None, [f"Could not build config: {exc}"]
    errors = cfg.validate()
    return cfg, errors


def deep_copy_dict(data: Dict) -> Dict:
    """Convenience: deep-copy a config dict (for editing without aliasing)."""
    return copy.deepcopy(data)


def make_hashable(data: Dict) -> Tuple:
    """Freeze a nested config dict into a tuple for use as a cache key."""
    def _freeze(value):
        if isinstance(value, dict):
            return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
        if isinstance(value, (list, tuple)):
            return tuple(_freeze(v) for v in value)
        return value

    return _freeze(data)
