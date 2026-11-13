"""PydanticAI-backed example.

Requires:
    pip install "streaming-dash-chat[pydantic-ai]"
    export OPENAI_API_KEY=sk-...   # or whichever provider your model string selects

Run with:
    python examples/pydantic_ai_chat.py
"""

import dash
from dash import Dash, html

from streaming_dash_chat import AIChat
from streaming_dash_chat.providers import PydanticAIProvider

app = Dash(__name__, shared_storage=dash.LocalSharedStorage)

chat = AIChat(
    id="pydantic-ai-chat",
    provider=PydanticAIProvider(
        model="openai:gpt-4.1",
        system_prompt="You are a concise, friendly assistant embedded in a Dash app.",
    ),
    title="AI Assistant",
    subtitle="PydanticAI agent",
    placement="start",
)

app.layout = html.Div(
    [
        html.H2("streaming_dash_chat + PydanticAI"),
        html.P("This example opens on the left -- placement is just a config option."),
        chat.layout,
    ],
    style={"fontFamily": "sans-serif", "padding": "40px"},
)
chat.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
