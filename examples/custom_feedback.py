"""Demonstrates wiring feedback/report handling to your own storage --
streaming_dash_chat never hardcodes a database.

Run with:
    python examples/custom_feedback.py
Then like/dislike or report the welcome message and watch the console.
"""

import logging

import dash
from dash import Dash, html

from streaming_dash_chat import AIChat
from streaming_dash_chat.models import Feedback, Report
from streaming_dash_chat.providers import MockProvider

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("custom_feedback_example")

app = Dash(__name__, shared_storage=dash.LocalSharedStorage)


def save_feedback(feedback: Feedback) -> None:
    # Replace with a real write to your own database/analytics system.
    logger.info(
        "FEEDBACK conversation=%s message=%s type=%s at=%s",
        feedback.conversation_id,
        feedback.message_id,
        feedback.feedback_type,
        feedback.timestamp,
    )


def save_report(report: Report) -> None:
    logger.info(
        "REPORT conversation=%s message=%s reason=%r details=%r",
        report.conversation_id,
        report.message_id,
        report.reason,
        report.details,
    )


chat = AIChat(
    id="feedback-demo-chat",
    provider=MockProvider(),
    title="Feedback demo",
    on_feedback=save_feedback,
    on_report=save_report,
)

app.layout = html.Div(
    [
        html.H2("streaming_dash_chat -- custom feedback handling"),
        html.P("Like/dislike or report a message, then check this process's console output."),
        chat.layout,
    ],
    style={"fontFamily": "sans-serif", "padding": "40px"},
)
chat.register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
