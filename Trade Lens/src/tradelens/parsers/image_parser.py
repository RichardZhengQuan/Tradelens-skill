"""Image extraction boundary.

Trade Lens currently relies on the host AI environment for screenshot reading. This
module records the boundary and returns a conservative extraction placeholder.
"""

from __future__ import annotations

from tradelens.models import ExtractionBundle


def extraction_placeholder(source: str = "screenshot") -> ExtractionBundle:
    return ExtractionBundle(
        visible_facts=[],
        user_claims=[],
        ai_inferences=[
            f"Image source received: {source}. Host AI must extract visible facts before saving."
        ],
        missing_data=[
            "confirmed OCR text",
            "user confirmation",
        ],
        confidence="unconfirmed image extraction",
    )

