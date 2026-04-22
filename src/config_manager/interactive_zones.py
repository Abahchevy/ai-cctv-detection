"""
Interactive Zone Configuration CLI
===================================
Provides a user-friendly command-line interface for creating new zone configurations.

The workflow:
  1. Load existing cameras from config/cameras.yaml
  2. Display available cameras and let user select one
  3. Display available zone types (presets) and let user select one
  4. Generate a zone configuration linked to the selected camera
  5. Append the new zone to config/zones.yaml
  6. Display confirmation

This module makes configuration accessible to non-technical users by automating
the complex YAML structure and validation logic.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from .presets import get_zone_preset, list_zone_types

logger = logging.getLogger(__name__)

# File paths for configuration
CONFIG_DIR = Path("config")
CAMERAS_CONFIG_PATH = CONFIG_DIR / "cameras.yaml"
ZONES_CONFIG_PATH = CONFIG_DIR / "zones.yaml"


def load_cameras() -> list[dict]:
    """
    Load camera definitions from cameras.yaml.

    The cameras list includes camera metadata (id, name, uri, enabled status).
    Only enabled cameras are typically used, but we show all for configuration.

    Returns
    -------
    list[dict]
        List of camera configuration dicts, each with keys: id, name, uri, zone_id, etc.

    Raises
    ------
    FileNotFoundError
        If cameras.yaml does not exist
    yaml.YAMLError
        If cameras.yaml is malformed
    """
    if not CAMERAS_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Cameras config not found at {CAMERAS_CONFIG_PATH}")

    try:
        config = yaml.safe_load(CAMERAS_CONFIG_PATH.read_text())
        cameras = config.get("cameras", [])
        if not cameras:
            logger.warning("No cameras found in cameras.yaml")
        return cameras
    except yaml.YAMLError as e:
        logger.error("Failed to parse cameras.yaml: %s", e)
        raise


def load_zones() -> tuple[dict, dict]:
    """
    Load existing zone definitions from zones.yaml.

    Returns both the zones dict AND the class_map, so we can preserve
    the class_map when saving updated zones.

    Returns
    -------
    tuple[dict, dict]
        (zones_dict, class_map_dict)
        - zones_dict: keyed by zone_id, values are zone configurations
        - class_map_dict: YOLO class name -> PPE item name mapping

    Raises
    ------
    FileNotFoundError
        If zones.yaml does not exist
    yaml.YAMLError
        If zones.yaml is malformed
    """
    if not ZONES_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Zones config not found at {ZONES_CONFIG_PATH}")

    try:
        config = yaml.safe_load(ZONES_CONFIG_PATH.read_text())
        zones = config.get("zones", {})
        class_map = config.get("class_map", {})
        return zones, class_map
    except yaml.YAMLError as e:
        logger.error("Failed to parse zones.yaml: %s", e)
        raise


def display_cameras(cameras: list[dict]) -> None:
    """
    Display available cameras in a numbered list for user selection.

    Parameters
    ----------
    cameras : list[dict]
        List of camera configurations
    """
    print("\n" + "=" * 60)
    print("AVAILABLE CAMERAS")
    print("=" * 60)
    for i, cam in enumerate(cameras):
        status = "✓ ENABLED" if cam.get("enabled", True) else "✗ DISABLED"
        print(f"[{i}] {cam['id']:15} | {cam['name']:25} | {status}")
    print()


def select_camera(cameras: list[dict]) -> tuple[int, dict]:
    """
    Prompt user to select a camera by index.

    Parameters
    ----------
    cameras : list[dict]
        List of camera configurations

    Returns
    -------
    tuple[int, dict]
        (selected_index, selected_camera_dict)

    Raises
    ------
    ValueError
        If user input is invalid or index out of range
    """
    while True:
        try:
            index = int(input("Enter camera index: ").strip())
            if 0 <= index < len(cameras):
                return index, cameras[index]
            else:
                print(f"❌ Invalid index. Please enter 0-{len(cameras) - 1}")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")


def display_zone_types() -> None:
    """
    Display available zone types (presets) in a numbered list for user selection.
    """
    print("\n" + "=" * 60)
    print("AVAILABLE ZONE TYPES")
    print("=" * 60)
    zone_types = list_zone_types()
    for i, zone_type in enumerate(zone_types):
        preset = get_zone_preset(zone_type)
        ppe_str = ", ".join(preset["required_ppe"])
        print(f"[{i}] {zone_type:15} | PPE: {ppe_str}")
        print(f"    ↳ {preset['description']}")
    print()


def select_zone_type() -> tuple[str, dict]:
    """
    Prompt user to select a zone type (preset) by index.

    Returns
    -------
    tuple[str, dict]
        (zone_type_name, preset_config_dict)

    Raises
    ------
    ValueError
        If user input is invalid or index out of range
    """
    zone_types = list_zone_types()

    while True:
        try:
            index = int(input("Enter zone type index: ").strip())
            if 0 <= index < len(zone_types):
                zone_type = zone_types[index]
                preset = get_zone_preset(zone_type)
                return zone_type, preset
            else:
                print(f"❌ Invalid index. Please enter 0-{len(zone_types) - 1}")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")


def generate_zone_id(camera_id: str, zone_type: str) -> str:
    """
    Generate a unique zone_id from camera_id and zone type.

    Format: "{camera_id}-{zone_type_slug}"
    Example: "cam-001-high-hazard"

    Parameters
    ----------
    camera_id : str
        The camera ID (e.g., "cam-001")
    zone_type : str
        The zone type name (e.g., "High Hazard")

    Returns
    -------
    str
        Generated zone_id
    """
    zone_slug = zone_type.lower().replace(" ", "-")
    return f"{camera_id}-{zone_slug}"


def create_zone_config(
    camera_id: str,
    zone_type: str,
    zone_type_name: str,
    preset: dict,
) -> dict:
    """
    Build a complete zone configuration from a preset.

    Creates a zone config dict with:
    - Descriptive name including camera and zone type
    - Required PPE from the preset
    - Alert cooldown from the preset
    - Camera ID for zone-to-camera linkage (used by zone_rules_engine)

    Parameters
    ----------
    camera_id : str
        The camera this zone is associated with
    zone_type : str
        The zone type name (e.g., "High Hazard")
    zone_type_name : str
        The display name of the zone type (used in zone name)
    preset : dict
        The preset configuration (from ZONE_PRESETS)

    Returns
    -------
    dict
        A zone configuration dict with keys: name, required_ppe, alert_cooldown_seconds, camera_id
    """
    return {
        "name": f"{zone_type_name} — {camera_id}",
        "required_ppe": preset["required_ppe"],
        "alert_cooldown_seconds": preset["alert_cooldown_seconds"],
        "camera_id": camera_id,  # Link zone to camera for rules engine validation
    }


def save_zones(zones: dict[str, dict], class_map: dict) -> None:
    """
    Save updated zones configuration back to zones.yaml.

    Preserves the class_map from the original config and maintains
    YAML structure and formatting.

    Parameters
    ----------
    zones : dict[str, dict]
        Updated zones dictionary
    class_map : dict
        YOLO class -> PPE item mapping (preserved from original)

    Raises
    ------
    IOError
        If unable to write to zones.yaml
    """
    output = {
        "zones": zones,
        "class_map": class_map,
    }

    try:
        ZONES_CONFIG_PATH.write_text(yaml.dump(output, default_flow_style=False, sort_keys=False))
        logger.info("Zone configuration saved successfully")
    except IOError as e:
        logger.error("Failed to save zones.yaml: %s", e)
        raise


def interactive_configure() -> Optional[str]:
    """
    Run the interactive zone configuration workflow.

    Guides the user through selecting a camera and zone type,
    then creates and saves the zone configuration.

    Returns
    -------
    str | None
        The zone_id of the newly created zone, or None if canceled
    """
    try:
        # Step 1: Load existing configurations
        print("\n📂 Loading camera and zone configurations...")
        cameras = load_cameras()
        zones, class_map = load_zones()

        if not cameras:
            print("❌ No cameras found in configuration. Please configure cameras first.")
            return None

        # Step 2: Select camera
        display_cameras(cameras)
        camera_idx, selected_camera = select_camera(cameras)
        camera_id = selected_camera["id"]
        print(f"\n✓ Selected camera: {camera_id} ({selected_camera['name']})")

        # Step 3: Select zone type
        display_zone_types()
        zone_type, preset = select_zone_type()
        print(f"\n✓ Selected zone type: {zone_type}")

        # Step 4: Generate zone configuration
        zone_id = generate_zone_id(camera_id, zone_type)

        # Check if zone already exists
        if zone_id in zones:
            overwrite = input(
                f"\n⚠️  Zone '{zone_id}' already exists. Overwrite? (y/N): "
            ).strip().lower()
            if overwrite != "y":
                print("Cancelled.")
                return None

        zone_config = create_zone_config(camera_id, zone_type, zone_type, preset)

        # Step 5: Save to zones.yaml
        zones[zone_id] = zone_config
        save_zones(zones, class_map)

        # Success
        print("\n" + "=" * 60)
        print("✅ Zone Configuration Created Successfully!")
        print("=" * 60)
        print(f"Zone ID:          {zone_id}")
        print(f"Camera ID:        {camera_id}")
        print(f"Zone Type:        {zone_type}")
        print(f"Required PPE:     {', '.join(zone_config['required_ppe'])}")
        print(f"Alert Cooldown:   {zone_config['alert_cooldown_seconds']}s")
        print("=" * 60 + "\n")

        return zone_id

    except FileNotFoundError as e:
        logger.error("Configuration file error: %s", e)
        print(f"\n❌ Error: {e}")
        return None
    except yaml.YAMLError as e:
        logger.error("YAML parsing error: %s", e)
        print(f"\n❌ Configuration format error: {e}")
        return None
    except Exception as e:
        logger.error("Unexpected error during zone configuration: %s", e)
        print(f"\n❌ Unexpected error: {e}")
        return None


def main():
    """
    Entry point for the zone configuration CLI.

    Can be run directly for interactive configuration:
        python -m src.config_manager.interactive_zones
    """
    print("\n🔧 INTERACTIVE ZONE CONFIGURATION")
    print("=" * 60)
    print("This tool helps you create new PPE compliance zones")
    print("linked to your configured cameras.\n")

    result = interactive_configure()
    if result:
        print(f"💾 To apply changes, restart the Inspection AI service.")
    else:
        print("No changes made.")


if __name__ == "__main__":
    main()
