"""
Zone Rules Engine
=================
Evaluates PersonObservation objects against zone-specific PPE requirements
and produces Violation records.

How it works:
  1. Each zone specifies required PPE items (hard_hat, vest, gloves, etc.)
  2. For each detected person, we check if all required PPE is present
  3. Missing PPE triggers a Violation record
  4. Alert cooldown prevents alert flooding (e.g., don't alert every frame)

Camera-to-Zone Linkage:
  Since zones are now camera-specific (created via interactive_zones.py),
  the engine validates that a zone belongs to the camera that reports it.
  This prevents violations from being incorrectly attributed to cameras
  or zones that don't match, especially important in multi-camera setups.

Alert Cooldown:
  Includes a cooldown cache keyed on (zone_id, track_id) to suppress
  repeated alerts for the same person violating the same rule.
  Cooldown window is configurable per zone (e.g., 15s, 30s, 60s).
  Example: if a person violates High Hazard zone rules, we alert once
  and suppress alerts for that person in that zone for 15 seconds.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.detection.models import PersonObservation, Violation

logger = logging.getLogger(__name__)


class ZoneRulesEngine:
    def __init__(self, zones_config: dict) -> None:
        """
        Parameters
        ----------
        zones_config : the parsed content of config/zones.yaml under key 'zones'
        """
        self._zones = zones_config
        # cooldown cache:  (zone_id, track_id) -> last_violation_timestamp (UTC seconds)
        self._cooldown_cache: dict[tuple[str, Optional[int]], float] = {}

    def evaluate(
        self,
        persons: list[PersonObservation],
        zone_id: str,
        camera_id: str,
        frame_index: int,
        timestamp_utc: str,
    ) -> list[Violation]:
        """
        Evaluate person observations against zone PPE requirements.

        For each person detected in a frame, checks if required PPE items
        are missing. Generates Violation records for missing gear, respecting
        a per-person cooldown to avoid alert flooding.

        Camera-to-zone linkage validation:
        Since zones are now camera-specific (configured via interactive_zones),
        we verify that the zone belongs to the camera processing the frame.
        If they don't match, we skip evaluation to prevent cross-camera violations.

        Cooldown cache:
        Uses (zone_id, track_id) as key to track last violation timestamp.
        Only generates new alerts if cooldown window has elapsed, preventing
        duplicate alerts for the same person violating the same rule continuously.

        Parameters
        ----------
        persons : list[PersonObservation]
            List of detected persons in the frame
        zone_id : str
            The zone being evaluated
        camera_id : str
            The camera that captured this frame
        frame_index : int
            Frame sequence number in the stream
        timestamp_utc : str
            ISO 8601 formatted UTC timestamp

        Returns
        -------
        list[Violation]
            List of new violations (respecting cooldown)
        """
        # Load zone configuration
        zone = self._zones.get(zone_id)
        if zone is None:
            logger.warning("Unknown zone_id '%s' — skipping rules evaluation.", zone_id)
            return []

        # Validate zone belongs to this camera
        # (zones are now camera-specific as of interactive configuration update)
        zone_camera = zone.get("camera_id")
        if zone_camera != camera_id:
            logger.debug(
                "Zone '%s' does not belong to camera '%s' — skipping.",
                zone_id,
                camera_id,
            )
            return []

        # Extract zone configuration
        required: set[str] = set(zone.get("required_ppe", []))
        cooldown: float = float(zone.get("alert_cooldown_seconds", 30))
        now_ts = datetime.fromisoformat(timestamp_utc).timestamp()

        violations: list[Violation] = []
        for person in persons:
            # Check which required PPE items this person is missing
            missing = [ppe for ppe in required if person.is_missing(ppe)]
            if not missing:
                # All required PPE present — no violation
                continue

            # Check cooldown cache to avoid repeated alerts for the same person
            cache_key = (zone_id, person.track_id)
            last_alert = self._cooldown_cache.get(cache_key, 0.0)
            if now_ts - last_alert < cooldown:
                # Alert cooldown still active — suppress this violation
                logger.debug(
                    "Cooldown active for %s track=%s — suppressing alert.",
                    zone_id,
                    person.track_id,
                )
                continue

            # Generate and record the violation
            self._cooldown_cache[cache_key] = now_ts
            violations.append(
                Violation(
                    camera_id=camera_id,
                    zone_id=zone_id,
                    track_id=person.track_id,
                    missing_ppe=missing,
                    confidence=person.person_bbox.width,   # placeholder; pass real conf
                    person_bbox=person.person_bbox,
                    timestamp_utc=timestamp_utc,
                    frame_index=frame_index,
                )
            )
        return violations
