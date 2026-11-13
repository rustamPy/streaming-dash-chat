"""Minimal runnable example: no API key needed.

Run with:
    python examples/basic_chat.py
Then open http://127.0.0.1:8050 and click the "Chat" button in the
bottom-right corner.
"""

import dash
from dash import Dash, html

from streaming_dash_chat import AIChat
from streaming_dash_chat.providers import MockProvider

app = Dash(__name__, shared_storage=dash.LocalSharedStorage)

chat = AIChat(
    id="basic-chat",
    provider=MockProvider(
        reply=(
            "This is a **mocked** streaming response -- no API key required. "
            "It demonstrates Markdown rendering, including `inline code` and:\n\n"
            "```python\nprint('genuine token-by-token streaming')\n```\n\n"
            "Swap in `OpenAIProvider` or `PydanticAIProvider` for a real model."
        )
    ),
    title="Demo Assistant",
    subtitle="Powered by a mock provider",
)

app.layout = html.Div(
    [
        html.H2("streaming_dash_chat basic example"),
        html.P("Click the Chat button in the bottom-right corner to open the assistant."),
        chat.layout,
    ],
    style={"fontFamily": "sans-serif", "padding": "40px"},
)
chat.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
