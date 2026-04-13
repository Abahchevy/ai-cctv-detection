"""
Evidence Store
==============
Persists violation evidence as:
  • An annotated JPEG snapshot on disk
  • A structured record in SQLite via SQLAlchemy

Evidence directory layout:
  evidence/
    <camera_id>/
      <date>/
        <timestamp>_frame<N>.jpg
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import cv2

from src.detection.models import Violation, FrameResult
from src.database.session import get_session
from src.database import models as db_models

logger = logging.getLogger(__name__)

_JPEG_QUALITY = 90


class EvidenceStore:
    def __init__(self, evidence_root: Path = Path("evidence")) -> None:
        self._root = evidence_root
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, result: FrameResult) -> list[str]:
        """
        Save evidence for all violations in the FrameResult.
        Returns list of saved file paths.
        """
        if not result.violations:
            return []

        saved: list[str] = []
        for violation in result.violations:
            path = self._save_snapshot(result, violation)
            self._persist_to_db(violation, path)
            saved.append(str(path))
        return saved

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save_snapshot(self, result: FrameResult, violation: Violation) -> Path:
        ts = datetime.fromisoformat(violation.timestamp_utc)
        date_str = ts.strftime("%Y-%m-%d")
        ts_str = ts.strftime("%H%M%S")

        dir_path = self._root / violation.camera_id / date_str
        dir_path.mkdir(parents=True, exist_ok=True)

        filename = f"{ts_str}_frame{violation.frame_index}.jpg"
        file_path = dir_path / filename

        frame = result.annotated_frame if result.annotated_frame is not None else result.raw_frame
        if frame is not None:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY]
            cv2.imwrite(str(file_path), frame, encode_params)
            logger.info("Evidence saved: %s", file_path)
        return file_path

    def _persist_to_db(self, violation: Violation, snapshot_path: Path) -> None:
        with get_session() as session:
            record = db_models.ViolationRecord(
                camera_id=violation.camera_id,
                zone_id=violation.zone_id,
                track_id=violation.track_id,
                missing_ppe=json.dumps(violation.missing_ppe),
                snapshot_path=str(snapshot_path),
                timestamp_utc=violation.timestamp_utc,
                frame_index=violation.frame_index,
            )
            session.add(record)
            session.commit()
