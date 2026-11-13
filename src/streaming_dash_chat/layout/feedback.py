"""Report modal: lets a user pick a reason and add optional details for a
specific assistant message. Rendered once per chat instance (not per
message) and repositioned via a hidden target-message-id store."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

REPORT_REASONS = [
    "Inaccurate or misleading",
    "Harmful or unsafe",
    "Offensive or inappropriate",
    "Not helpful",
    "Other",
]


def render_report_modal(chat_id: str) -> dbc.Modal:
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Report this response")),
            dbc.ModalBody(
                [
                    dbc.RadioItems(
                        id={"type": "sdc-report-reason", "chat": chat_id},
                        options=[{"label": r, "value": r} for r in REPORT_REASONS],
                        value=REPORT_REASONS[0],
                        className="sdc-report-reasons",
                    ),
                    dbc.Textarea(
                        id={"type": "sdc-report-details", "chat": chat_id},
                        placeholder="Additional details (optional)",
                        className="sdc-report-details mt-2",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Cancel",
                        id={"type": "sdc-report-cancel", "chat": chat_id},
                        color="secondary",
                        outline=True,
                    ),
                    dbc.Button(
                        "Submit report",
                        id={"type": "sdc-report-submit", "chat": chat_id},
                        color="danger",
                    ),
                ]
            ),
            dcc.Store(id={"type": "sdc-report-target", "chat": chat_id}),
        ],
        id={"type": "sdc-report-modal", "chat": chat_id},
        is_open=False,
        className="sdc-report-modal",
    )
