"""Custom chat header -- deliberately not dbc.Offcanvas's built-in title bar,
so the component doesn't look like a default Bootstrap modal."""

from __future__ import annotations

from dash import html

from streaming_dash_chat.config import AIChatConfig


def render_header(chat_id: str, config: AIChatConfig) -> html.Div:
    if config.avatar:
        avatar = html.Img(src=config.avatar, className="sdc-avatar")
    else:
        avatar = html.Div(
            (config.assistant_name or "A")[:1].upper(),
            className="sdc-avatar sdc-avatar--fallback",
        )

    text_children = [html.Div(config.title, className="sdc-header-title")]
    if config.subtitle:
        text_children.append(html.Div(config.subtitle, className="sdc-header-subtitle"))

    buttons = [
        html.Button(
            "New chat",
            id={"type": "sdc-new-conversation", "chat": chat_id},
            className="sdc-header-btn",
            title="Start a new conversation",
        ),
    ]

    if config.expandable:
        buttons.append(
            html.Button(
                id={"type": "sdc-expand", "chat": chat_id},
                className="sdc-action-btn sdc-icon--expand sdc-expand-btn",
                title="Expand",
                type="button",
                **{
                    "aria-label": "Expand chat",
                    "data-expanded": "false",
                    "data-expanded-width": config.expanded_width,
                },
            )
        )

    buttons.append(
        html.Button(
            "×",
            id={"type": "sdc-close", "chat": chat_id},
            className="sdc-close-btn",
            **{"aria-label": "Close chat"},
        )
    )

    return html.Div(
        [
            avatar,
            html.Div(text_children, className="sdc-header-text"),
            html.Div(className="sdc-header-spacer"),
            *buttons,
        ],
        className="sdc-header",
    )
