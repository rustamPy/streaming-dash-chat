"""Demonstrates all four Offcanvas placements at once, each an independent
AIChat instance on the same page/app -- useful for visually checking that
multiple chat instances don't interfere with each other and that streaming
is genuinely incremental (the mock provider has a visible per-token delay).

Run with:
    python examples/streaming_chat.py
"""

import dash
from dash import Dash, html

from streaming_dash_chat import AIChat
from streaming_dash_chat.providers import MockProvider

app = Dash(__name__, shared_storage=dash.LocalSharedStorage)

LONG_REPLY = (
    "Here is a longer response so you can watch it arrive token by token. "
    "It includes a list:\n\n- First point\n- Second point\n- Third point\n\n"
    "and a code block:\n\n```python\ndef hello():\n    return 'world'\n```\n\n"
    "Try clicking Stop partway through to see cancellation take effect, or "
    "Regenerate once it finishes."
)

PLACEMENTS = ("start", "end", "top", "bottom")

chats = [
    AIChat(
        id=f"chat-{placement}",
        provider=MockProvider(reply=LONG_REPLY, delay_seconds=0.05),
        placement=placement,
        title=f"Assistant ({placement})",
        # The library's floating toggle button is fixed-position; with four
        # instances on one page they'd stack on top of each other, so each
        # gets its own inline trigger below instead, reusing the same
        # {"type": "sdc-toggle", "chat": ...} id the built-in callback
        # already listens on.
        show_toggle_button=False,
    )
    for placement in PLACEMENTS
]

app.layout = html.Div(
    [
        html.H2("streaming_dash_chat -- all four placements"),
        html.P("Each button below opens an independently-running chat instance."),
        html.Div(
            [
                html.Button(f"Open {placement}", id={"type": "sdc-toggle", "chat": f"chat-{placement}"})
                for placement in PLACEMENTS
            ],
            style={"display": "flex", "gap": "12px"},
        ),
        *[chat.layout for chat in chats],
    ],
    style={"fontFamily": "sans-serif", "padding": "40px"},
)
for chat in chats:
    chat.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
