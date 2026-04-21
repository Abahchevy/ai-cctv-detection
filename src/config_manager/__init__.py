"""
Config Manager Module
=====================
Provides configuration and zone management utilities for the Inspection AI system.

Submodules:
  - presets: Zone type definitions (High/Medium/Low Hazard)
  - interactive_zones: CLI tool for user-friendly zone configuration

Example Usage:
    from src.config_manager.interactive_zones import interactive_configure
    zone_id = interactive_configure()
"""

from .presets import ZONE_PRESETS, get_zone_preset, list_zone_types
from .interactive_zones import interactive_configure, main

__all__ = [
    "ZONE_PRESETS",
    "get_zone_preset",
    "list_zone_types",
    "interactive_configure",
    "main",
]
