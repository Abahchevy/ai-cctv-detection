"""
Zone Rules Engine
=================
Evaluates PersonObservation objects against zone-specific PPE requirements
and produces Violation records.

Includes a cooldown cache keyed on (zone_id, track_id) so the same person
does not generate repeated alerts within the configured window.
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
        zone = self._zones.get(zone_id)
        if zone is None:
            logger.warning("Unknown zone_id '%s' — skipping rules evaluation.", zone_id)
            return []

        required: set[str] = set(zone.get("required_ppe", []))
        cooldown: float = float(zone.get("alert_cooldown_seconds", 30))
        now_ts = datetime.fromisoformat(timestamp_utc).timestamp()

        violations: list[Violation] = []
        for person in persons:
            missing = [ppe for ppe in required if person.is_missing(ppe)]
            if not missing:
                continue

            cache_key = (zone_id, person.track_id)
            last_alert = self._cooldown_cache.get(cache_key, 0.0)
            if now_ts - last_alert < cooldown:
                logger.debug(
                    "Cooldown active for %s track=%s — suppressing alert.",
                    zone_id,
                    person.track_id,
                )
                continue

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
