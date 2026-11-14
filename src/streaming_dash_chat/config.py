"""Configuration model for the AIChat component."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Placement(str, Enum):
    """Maps 1:1 onto ``dbc.Offcanvas(placement=...)`` values."""

    START = "start"  # left in LTR layouts
    END = "end"  # right in LTR layouts
    TOP = "top"
    BOTTOM = "bottom"


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"


class AIChatConfig(BaseModel):
    """Validated, serializable configuration for a single ``AIChat`` instance.

    Only JSON-safe values belong here, since parts of it are embedded into
    Dash component props and read back by clientside JavaScript.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str
    placement: Placement = Placement.END
    is_open: bool = False
    width: str | None = None  # CSS width, only meaningful for start/end placements
    height: str | None = None  # CSS height, only meaningful for top/bottom placements
    title: str = "Assistant"
    subtitle: str | None = None
    theme: Theme = Theme.LIGHT
    class_name: str | None = None
    welcome_message: str | None = "Hi! How can I help you today?"
    assistant_name: str = "Assistant"
    avatar: str | None = None  # URL or data-URI
    allow_regenerate: bool = True
    allow_feedback: bool = True
    allow_report: bool = True
    show_timestamps: bool = False
    show_toggle_button: bool = True
    expandable: bool = False
    expanded_width: str = "720px"
