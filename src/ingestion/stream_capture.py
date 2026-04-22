"""
Lightweight Stream Capture for Low-Latency MJPEG Serving
==========================================================

This module provides a dedicated thread for capturing raw frames from webcams/RTSP
streams and making them immediately available for MJPEG streaming, bypassing the
heavy detection pipeline for minimum latency.

Key design principles:
- Single capture thread per camera
- Only the latest frame is stored (old frames dropped immediately)
- Frame-ready event for efficient polling
- Minimal buffering: single buffer approach
- No frame queuing or accumulation
"""
from __future__ import annotations

import logging 
import threading
import time
from typing import Optional

import cv2
import numpy as np
import platform

logger = logging.getLogger(__name__)


class StreamCapture(threading.Thread):
    """
    Dedicated capture thread for real-time webcam/RTSP streaming.

    Reads frames continuously from a camera source and maintains ONLY the
    latest frame in a thread-safe buffer. Old frames are instantly dropped.
    This thread is separate from the detection pipeline to minimize latency.

    Typical FPS for webcam: 15-30 fps raw capture → MJPEG can stream any
    subset of those frames without lag.
    """

    def __init__(
        self,
        camera_id: str,
        uri: str,
        target_fps: Optional[float] = None,
        jpeg_quality: int = 75,
    ) -> None:
        """
        Initialize stream capture.

        Parameters
        ----------
        camera_id : str
            Unique camera identifier (e.g., "cam-test")
        uri : str
            Camera URI: RTSP URL or webcam index (as string, e.g., "0" for /dev/video0)
        target_fps : Optional[float]
            If set, cap capture to this FPS to reduce CPU. Default: ~30 fps (0.04s interval)
        jpeg_quality : int
            JPEG quality 1-100. Lower = faster encode, more CPU for stream generation.
            Default 75 balances quality and speed.
        """
        super().__init__(daemon=True, name=f"capture-{camera_id}")
        self.camera_id = camera_id
        self._uri = uri

        # Frame buffer: single slot for the latest frame
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._frame_ready = threading.Event()

        # Capture interval: time to wait between reads (0 = no limit)
        self._frame_interval = 0 if target_fps is None else (1.0 / max(target_fps, 1))
        self._jpeg_quality = max(1, min(100, jpeg_quality))
        self._stop_event = threading.Event()

    # ======================================================================
    # Public API
    # ======================================================================

    def get_frame(self) -> Optional[np.ndarray]:
        """Return the latest captured frame, or None if no frame yet."""
        with self._frame_lock:
            return self._frame.copy() if self._frame is not None else None

    def wait_for_frame(self, timeout: float = 1.0) -> bool:
        """
        Wait for the next frame to be available.

        Parameters
        ----------
        timeout : float
            Maximum time to wait (seconds)

        Returns
        -------
        bool
            True if frame became available, False if timeout
        """
        self._frame_ready.clear()
        return self._frame_ready.wait(timeout=timeout)

    def stop(self) -> None:
        """Signal the capture thread to stop."""
        self._stop_event.set()

    # ======================================================================
    # Thread execution
    # ======================================================================

    def run(self) -> None:
        """Main capture loop: continuously read frames from camera."""
        uri = self._uri
        if uri.isdigit():
            uri = int(uri)

        # Attempt to open the camera with multiple backends (fallback mechanism)
        def open_camera():
            if isinstance(uri, int) and platform.system() == "Windows":
                # Try DirectShow first, then fallback to MSMF
                cap = cv2.VideoCapture(uri, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    logger.warning("[%s] CAP_DSHOW failed, trying CAP_MSMF.", self.camera_id)
                    cap = cv2.VideoCapture(uri, cv2.CAP_MSMF)
            else:
                cap = cv2.VideoCapture(uri)
            return cap

        cap = open_camera()
        if not cap.isOpened():
            logger.error("[%s] Cannot open stream: %s", self.camera_id, self._uri)
            return

        logger.info("[%s] Stream capture started: %s", self.camera_id, self._uri)
        last_captured = 0.0

        try:
            while not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning("[%s] Frame read failed — reconnecting in 3s.", self.camera_id)
                    cap.release()
                    time.sleep(3)
                    cap = open_camera()
                    if not cap.isOpened():
                        logger.error("[%s] Reconnection failed: %s", self.camera_id, self._uri)
                        break
                    continue

                # Enforce target FPS if set (skip frames to save CPU)
                now = time.monotonic()
                if self._frame_interval > 0 and (now - last_captured) < self._frame_interval:
                    continue
                last_captured = now

                # Store ONLY latest frame (drop any older buffered frame)
                with self._frame_lock:
                    self._frame = frame
                self._frame_ready.set()

        finally:
            cap.release()
            logger.info("[%s] Stream capture stopped.", self.camera_id)
