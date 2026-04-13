"""
Stream Processor
================
Reads from an RTSP URL (or local file / webcam index) and feeds frames
through the detection pipeline at a configurable FPS limit.

Each camera runs in its own thread.  Processed FrameResults are placed on
an asyncio-compatible queue for the API layer to consume.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np
import platform

from src.detection.detector import PPEDetector
from src.detection.models import FrameResult
from src.detection.zone_rules import ZoneRulesEngine
from src.evidence.annotator import annotate_frame

logger = logging.getLogger(__name__)


class StreamProcessor(threading.Thread):
    """
    Daemon thread that continuously reads from a camera source and
    publishes FrameResult objects to `result_queue`.
    """

    def __init__(
        self,
        camera_id: str,
        zone_id: str,
        uri: str,
        detector: PPEDetector,
        rules_engine: ZoneRulesEngine,
        result_queue: queue.Queue,
        fps_limit: float = 5.0,
    ) -> None:
        super().__init__(daemon=True, name=f"stream-{camera_id}")
        self.camera_id = camera_id
        self.zone_id = zone_id
        self._uri = uri
        self._detector = detector
        self._rules = rules_engine
        self._queue = result_queue
        self._frame_interval = 1.0 / max(fps_limit, 0.1)
        self._stop_event = threading.Event()
        self._frame_index = 0

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def stop(self) -> None:
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        uri = self._uri
        # Allow integer index for webcams
        if uri.isdigit():
            uri = int(uri)

        # On Windows use DirectShow backend for local cameras to avoid MSMF errors
        if isinstance(uri, int) and platform.system() == "Windows":
            cap = cv2.VideoCapture(uri, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(uri)
        if not cap.isOpened():
            logger.error("[%s] Cannot open stream: %s", self.camera_id, self._uri)
            return

        logger.info("[%s] Stream opened: %s", self.camera_id, self._uri)
        last_processed = 0.0

        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning("[%s] Frame read failed — reconnecting in 5 s.", self.camera_id)
                    cap.release()
                    time.sleep(5)
                    if isinstance(uri, int) and platform.system() == "Windows":
                        cap = cv2.VideoCapture(uri, cv2.CAP_DSHOW)
                    else:
                        cap = cv2.VideoCapture(uri)
                    continue

                now = time.monotonic()
                if now - last_processed < self._frame_interval:
                    continue
                last_processed = now

                result = self._process(frame)
                try:
                    self._queue.put_nowait(result)
                except queue.Full:
                    pass   # Drop frame if consumer is slow

        finally:
            cap.release()
            logger.info("[%s] Stream closed.", self.camera_id)

    # ------------------------------------------------------------------
    # Per-frame processing
    # ------------------------------------------------------------------

    def _process(self, frame: np.ndarray) -> FrameResult:
        ts = datetime.now(timezone.utc).isoformat()
        self._frame_index += 1

        detections, persons = self._detector.process_frame(frame)
        violations = self._rules.evaluate(
            persons=persons,
            zone_id=self.zone_id,
            camera_id=self.camera_id,
            frame_index=self._frame_index,
            timestamp_utc=ts,
        )

        annotated = annotate_frame(frame.copy(), persons, violations)

        return FrameResult(
            camera_id=self.camera_id,
            zone_id=self.zone_id,
            frame_index=self._frame_index,
            timestamp_utc=ts,
            persons=persons,
            violations=violations,
            raw_frame=frame,
            annotated_frame=annotated,
        )
