"""OpenAI-backed example.

Requires:
    pip install "streaming-dash-chat[openai]"
    export OPENAI_API_KEY=sk-...

Run with:
    python examples/openai_chat.py
"""

import dash
from dash import Dash, html

from streaming_dash_chat import AIChat
from streaming_dash_chat.providers import OpenAIProvider

app = Dash(__name__, shared_storage=dash.LocalSharedStorage)

chat = AIChat(
    id="openai-chat",
    provider=OpenAIProvider(
        model="gpt-4.1",
        system_prompt="You are a concise, friendly assistant embedded in a Dash app.",
        temperature=0.7,
    ),
    title="AI Assistant",
    subtitle="OpenAI gpt-4.1",
    placement="end",
)

app.layout = html.Div(
    [
        html.H2("streaming_dash_chat + OpenAI"),
        html.P("Make sure OPENAI_API_KEY is set in your environment before sending a message."),
        chat.layout,
    ],
    style={"fontFamily": "sans-serif", "padding": "40px"},
)
chat.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
