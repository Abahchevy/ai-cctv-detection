from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def centre(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def as_ints(self) -> tuple[int, int, int, int]:
        return (int(self.x1), int(self.y1), int(self.x2), int(self.y2))


@dataclass
class Detection:
    """Single object detected in a frame."""
    class_name: str          # Raw class label from the model
    ppe_id: Optional[str]    # Canonical PPE id after class_map lookup (None = unknown)
    confidence: float
    bbox: BoundingBox
    track_id: Optional[int] = None   # Populated when using ByteTrack / BoT-SORT


@dataclass
class PersonObservation:
    """
    Groups all detections associated with one person in a single frame.
    Uses a bounding-box proximity heuristic: PPE detections whose centre
    falls inside or near the person bbox are attributed to that person.
    """
    track_id: Optional[int]
    person_bbox: BoundingBox
    worn_ppe: set[str] = field(default_factory=set)    # Canonical PPE ids
    raw_detections: list[Detection] = field(default_factory=list)

    def is_missing(self, ppe_id: str) -> bool:
        return ppe_id not in self.worn_ppe


@dataclass
class FrameResult:
    """Full analysis result for one processed video frame."""
    camera_id: str
    zone_id: str
    frame_index: int
    timestamp_utc: str          # ISO-8601
    persons: list[PersonObservation]
    violations: list["Violation"]
    raw_frame: object = field(repr=False, default=None)   # numpy ndarray
    annotated_frame: object = field(repr=False, default=None)


@dataclass
class Violation:
    camera_id: str
    zone_id: str
    track_id: Optional[int]
    missing_ppe: list[str]      # Which required items were absent
    confidence: float           # Person detection confidence
    person_bbox: BoundingBox
    timestamp_utc: str
    frame_index: int
