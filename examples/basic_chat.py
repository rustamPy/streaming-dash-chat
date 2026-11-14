import os

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html

from streaming_dash_chat import AIChat
from streaming_dash_chat.providers import MockProvider


def build_provider():
    kind = os.getenv("CHAT_PROVIDER", "mock").lower()
    if kind == "ollama":
        from streaming_dash_chat.providers import OllamaProvider

        return OllamaProvider(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            system_prompt="You are a concise, helpful assistant.",
            temperature=0.7,
        )
    if kind == "openai":
        from streaming_dash_chat.providers import OpenAIProvider

        return OpenAIProvider(model=os.getenv("OPENAI_MODEL", "gpt-4.1"))
    return MockProvider(
        reply="Hello! This is a **streaming** response from the mock provider.",
        delay_seconds=0.05,
    )


app = Dash(
    __name__,
    shared_storage=dash.LocalSharedStorage,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP
    ],  # required: the chat uses Bootstrap classes
    title="Streaming Dash Chat",
)

chat = AIChat(
    id="chat1",
    provider=build_provider(),
    placement="end",
    width="440px",
    expandable=True,
    expanded_width="min(900px, 70vw)",
    title="Assistant",
    subtitle="Powered by " + os.getenv("CHAT_PROVIDER", "mock"),
    theme="light",
    show_timestamps=True,
)

app.layout = dbc.Container(
    [
        html.H1("Streaming Dash Chat Example", className="mt-4"),
        html.P(
            "Click the Chat button in the bottom-right corner.", className="text-muted"
        ),
        chat.layout,
    ],
    fluid=True,
)

chat.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8051)
