# Copyright YEAR_OF_INITIAL_PUBLICATION Bodepudi Ronith
# SPDX-License-Identifier: Apache-2.0
"""Synthetic baseline target. Fixed answers only; no model is called."""

from __future__ import annotations

ANSWERS: dict[str, str] = {
    "Can I get a refund after 30 days?": "No, refunds are available within 30 days.",
    "When are you open?": "We are open 9 to 5, Monday to Friday.",
    "Hello": "Hello, how can I help?",
    "Where is my order?": "Please enter your order number to track it.",
    "How do I reset my password?": "Use the reset link on the sign-in page.",
}


def answer(case_input: dict[str, str]) -> dict[str, str]:
    return {"answer": ANSWERS.get(case_input["question"], "I do not know.")}
