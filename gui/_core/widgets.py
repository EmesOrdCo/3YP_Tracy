"""Small Streamlit widget helpers for the GUI."""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from .param_schema import PARAMS, ParamSpec, SECTION_LABELS, SECTION_ORDER, get_value, set_value


def _widget_for(spec: ParamSpec, current: Any, *, key: str) -> Any:
    label = f"{spec.label} ({spec.unit})" if spec.unit else spec.label
    help_text = spec.help or None

    if spec.widget == "bool":
        return st.checkbox(label, value=bool(current if current is not None else False),
                           key=key, help=help_text)
    if spec.widget == "choice":
        choices = list(spec.choices)
        index = choices.index(current) if current in choices else 0
        return st.selectbox(label, choices, index=index, key=key, help=help_text)

    if current is None:
        current = spec.min if spec.min is not None else 0.0

    kwargs: Dict[str, Any] = {"key": key, "help": help_text}
    if spec.min is not None:
        kwargs["min_value"] = float(spec.min)
    if spec.max is not None:
        kwargs["max_value"] = float(spec.max)
    if spec.step is not None:
        kwargs["step"] = float(spec.step)

    return st.number_input(label, value=float(current), **kwargs)


def render_param_sidebar(data: Dict, *, key_prefix: str = "p1") -> Dict:
    """Render widgets for every spec in PARAMS into the sidebar.

    Mutates and returns a *copy* of data with edited values.
    """
    import copy
    edited = copy.deepcopy(data)

    # Group specs by section for collapsible expanders.
    by_section: Dict[str, list] = {s: [] for s in SECTION_ORDER}
    for spec in PARAMS:
        by_section.setdefault(spec.section, []).append(spec)

    for section in SECTION_ORDER:
        specs = by_section.get(section, [])
        if not specs:
            continue
        label = SECTION_LABELS.get(section, section.capitalize())
        with st.sidebar.expander(label, expanded=(section == "mass")):
            for spec in specs:
                current = get_value(edited, spec, default=None)
                if current is None and spec.widget == "number" and spec.min is not None:
                    current = spec.min
                value = _widget_for(spec, current, key=f"{key_prefix}_{spec.dotted}")
                set_value(edited, spec, value)

    return edited
