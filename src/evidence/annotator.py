"""
Frame Annotator
===============
Draws bounding boxes, PPE labels, and violation warnings onto a BGR frame
using OpenCV.  Returns an annotated copy; never modifies the original.
"""
from __future__ import annotations

import cv2
import numpy as np

from src.detection.models import PersonObservation, Violation

# Colour palette (BGR)
_GREEN = (0, 200, 0)
_RED = (0, 0, 220)
_ORANGE = (0, 140, 255)
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)
_FONT = cv2.FONT_HERSHEY_SIMPLEX


def annotate_frame(
    frame: np.ndarray,
    persons: list[PersonObservation],
    violations: list[Violation],
) -> np.ndarray:
    violation_track_ids = {v.track_id for v in violations}

    for person in persons:
        x1, y1, x2, y2 = person.person_bbox.as_ints()
        has_violation = person.track_id in violation_track_ids
        colour = _RED if has_violation else _GREEN

        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)

        label = f"ID:{person.track_id}" if person.track_id is not None else "Person"
        _draw_label(frame, label, x1, y1 - 6, colour)

        if person.worn_ppe:
            ppe_text = ", ".join(sorted(person.worn_ppe))
            _draw_label(frame, ppe_text, x1, y2 + 14, _GREEN, scale=0.45)

    for v in violations:
        x1, y1 = int(v.person_bbox.x1), int(v.person_bbox.y1)
        missing_text = "MISSING: " + ", ".join(v.missing_ppe).upper()
        _draw_label(frame, missing_text, x1, y1 - 22, _RED, scale=0.45)

    # Timestamp overlay
    cv2.putText(
        frame,
        _utc_now_label(),
        (8, frame.shape[0] - 8),
        _FONT,
        0.42,
        _WHITE,
        1,
        cv2.LINE_AA,
    )

    return frame


def _draw_label(
    frame: np.ndarray,
    text: str,
    x: int,
    y: int,
    colour: tuple,
    scale: float = 0.5,
    thickness: int = 1,
) -> None:
    (tw, th), baseline = cv2.getTextSize(text, _FONT, scale, thickness)
    y = max(y, th + baseline)
    # Background rectangle
    cv2.rectangle(frame, (x, y - th - baseline), (x + tw, y + baseline), _BLACK, cv2.FILLED)
    cv2.putText(frame, text, (x, y), _FONT, scale, colour, thickness, cv2.LINE_AA)


def _utc_now_label() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("UTC %Y-%m-%d %H:%M:%S")
