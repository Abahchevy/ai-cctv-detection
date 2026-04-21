"""
Zone Type Presets
=================
Defines reusable zone configuration templates for different risk levels.
Each preset encapsulates specific PPE requirements and alert behavior based on
the hazard level of the zone.

When users create a new zone via the interactive CLI, they select a preset
and the system generates a zone configuration with matching requirements.

Zone Types:
  - High Hazard: Maximum PPE protection (hard hat, vest, gloves)
  - Medium Hazard: Standard PPE protection (hard hat, vest)
  - Low Hazard: Basic PPE protection (vest only)
"""

# Define reusable zone type presets
# Each preset specifies:
#   - required_ppe: List of equipment persons must wear in this zone
#   - alert_cooldown_seconds: Minimum seconds between alerts for same person
#     (prevents alert flooding for the same violation)
ZONE_PRESETS = {
    "High Hazard": {
        "description": "Maximum protection required (e.g., chemical handling, welding)",
        "required_ppe": ["hard_hat", "vest", "gloves"],
        "alert_cooldown_seconds": 15,  # Alert every 15s for persistent violations
    },
    "Medium Hazard": {
        "description": "Standard protection required (e.g., general plant floor)",
        "required_ppe": ["hard_hat", "vest"],
        "alert_cooldown_seconds": 30,  # Alert every 30s for persistent violations
    },
    "Low Hazard": {
        "description": "Basic protection recommended (e.g., office areas, general entry)",
        "required_ppe": ["vest"],
        "alert_cooldown_seconds": 60,  # Alert every 60s for persistent violations
    },
}


def get_zone_preset(zone_type_name: str) -> dict | None:
    """
    Retrieve a preset by its display name.

    Parameters
    ----------
    zone_type_name : str
        The human-readable zone type name (e.g., "High Hazard")

    Returns
    -------
    dict | None
        The preset configuration dict, or None if not found
    """
    return ZONE_PRESETS.get(zone_type_name)


def list_zone_types() -> list[str]:
    """
    Get all available zone type names in order.

    Returns
    -------
    list[str]
        Sorted list of zone type names available in ZONE_PRESETS
    """
    return sorted(ZONE_PRESETS.keys())
