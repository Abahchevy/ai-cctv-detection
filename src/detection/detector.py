"""
PPE Detector
============
Wraps a YOLOv8 model to produce per-frame Detection objects.

Recommended model options (pass as `model_path`):
  • "keremberke/yolov8n-hard-hat-detection"  – Hugging Face hosted, auto-download
  • A local .pt file fine-tuned on your PPE dataset
  • "yolov8n.pt" for a generic COCO model (person class only; no PPE classes)

The detector optionally enables ByteTrack for cross-frame person tracking,
which is needed to apply cooldown-based alert suppression.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.detection.models import BoundingBox, Detection, PersonObservation

logger = logging.getLogger(__name__)

# Proximity factor: a PPE bbox centre must be within this fraction of the
# person bbox dimensions to be attributed to that person.
_PROXIMITY_SCALE = 1.2


class PPEDetector:
    def __init__(
        self,
        model_path: str = "keremberke/yolov8m-hard-hat-detection",
        class_map: Optional[dict[str, str]] = None,
        confidence_threshold: float = 0.45,
        device: str = "cpu",
        enable_tracking: bool = True,
    ) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required. Install it with: pip install ultralytics"
            ) from exc

        logger.info("Loading model: %s on device=%s", model_path, device)
        self._model = YOLO(model_path)
        self._model.to(device)
        self._conf = confidence_threshold
        self._class_map: dict[str, str] = {k.lower(): v for k, v in (class_map or {}).items()}
        self._enable_tracking = enable_tracking

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_frame(
        self, frame: np.ndarray
    ) -> tuple[list[Detection], list[PersonObservation]]:
        """
        Run inference on a single BGR frame.

        Returns
        -------
        detections : all raw detections in the frame
        persons    : PersonObservation list (PPE grouped per person)
        """
        if self._enable_tracking:
            results = self._model.track(
                frame,
                persist=True,
                conf=self._conf,
                verbose=False,
            )
        else:
            results = self._model(frame, conf=self._conf, verbose=False)

        detections = self._parse_results(results)
        persons = self._group_ppe_to_persons(detections)
        return detections, persons

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_results(self, results) -> list[Detection]:
        detections: list[Detection] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            names: dict[int, str] = result.names

            for i, box in enumerate(boxes):
                cls_id = int(box.cls[0].item())
                raw_name = names.get(cls_id, str(cls_id))
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()
                track_id = None
                if boxes.id is not None:
                    track_id = int(boxes.id[i].item())

                ppe_id = self._resolve_class(raw_name)
                detections.append(
                    Detection(
                        class_name=raw_name,
                        ppe_id=ppe_id,
                        confidence=conf,
                        bbox=BoundingBox(*xyxy),
                        track_id=track_id,
                    )
                )
        return detections

    def _resolve_class(self, raw_name: str) -> Optional[str]:
        return self._class_map.get(raw_name.lower())

    def _group_ppe_to_persons(
        self, detections: list[Detection]
    ) -> list[PersonObservation]:
        persons_det = [d for d in detections if d.ppe_id == "person"]
        ppe_det = [d for d in detections if d.ppe_id and d.ppe_id != "person"]

        observations: list[PersonObservation] = []
        for p in persons_det:
            obs = PersonObservation(
                track_id=p.track_id,
                person_bbox=p.bbox,
            )
            # Attribute nearby PPE to this person
            for ppe in ppe_det:
                if self._ppe_belongs_to_person(ppe.bbox, p.bbox):
                    obs.worn_ppe.add(ppe.ppe_id)
                    obs.raw_detections.append(ppe)
            observations.append(obs)
        return observations

    @staticmethod
    def _ppe_belongs_to_person(ppe_bbox: BoundingBox, person_bbox: BoundingBox) -> bool:
        """True if the PPE bounding box centre falls within the expanded person bbox."""
        cx, cy = ppe_bbox.centre
        pw, ph = person_bbox.width, person_bbox.height
        margin_x = pw * (_PROXIMITY_SCALE - 1) / 2
        margin_y = ph * (_PROXIMITY_SCALE - 1) / 2
        return (
            person_bbox.x1 - margin_x <= cx <= person_bbox.x2 + margin_x
            and person_bbox.y1 - margin_y <= cy <= person_bbox.y2 + margin_y
        )
