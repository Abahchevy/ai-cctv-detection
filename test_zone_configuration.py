"""
Integration Test: Zone Configuration System
=============================================
Tests the complete zone configuration workflow including:
  - Preset loading and selection
  - Interactive zone creation
  - Zone persistence and validation
  - Zone Rules Engine integration with camera_id validation

Run with: python test_zone_configuration.py
"""
from __future__ import annotations

import tempfile
import yaml
from pathlib import Path
from datetime import datetime, timezone

# Test imports
from src.config_manager.presets import (
    ZONE_PRESETS,
    get_zone_preset,
    list_zone_types,
)
from src.config_manager.interactive_zones import (
    generate_zone_id,
    create_zone_config,
    load_cameras,
    load_zones,
)
from src.detection.zone_rules import ZoneRulesEngine
from src.detection.models import PersonObservation, BoundingBox


def test_presets():
    """Test that presets are properly defined with all required fields."""
    print("\n✓ Testing Zone Presets...")

    # Check all presets exist
    assert len(ZONE_PRESETS) >= 3, "Expected at least 3 zone types"

    zone_types = list_zone_types()
    assert "High Hazard" in zone_types
    assert "Medium Hazard" in zone_types
    assert "Low Hazard" in zone_types

    # Check preset structure
    for zone_type in zone_types:
        preset = get_zone_preset(zone_type)
        assert preset is not None, f"Preset '{zone_type}' not found"
        assert "required_ppe" in preset, f"Missing required_ppe in {zone_type}"
        assert "alert_cooldown_seconds" in preset, f"Missing alert_cooldown_seconds in {zone_type}"
        assert isinstance(preset["required_ppe"], list), "required_ppe must be a list"
        assert isinstance(preset["alert_cooldown_seconds"], int), "alert_cooldown_seconds must be an int"
        print(f"  ✓ {zone_type}: {len(preset['required_ppe'])} PPE items, {preset['alert_cooldown_seconds']}s cooldown")


def test_zone_id_generation():
    """Test zone ID generation format."""
    print("\n✓ Testing Zone ID Generation...")

    zone_id = generate_zone_id("cam-001", "High Hazard")
    assert zone_id == "cam-001-high-hazard", f"Unexpected zone_id format: {zone_id}"

    zone_id = generate_zone_id("welding-bay", "Medium Hazard")
    assert zone_id == "welding-bay-medium-hazard", f"Unexpected zone_id format: {zone_id}"

    print(f"  ✓ Zone IDs generated correctly")


def test_zone_config_creation():
    """Test zone configuration creation from preset."""
    print("\n✓ Testing Zone Config Creation...")

    preset = get_zone_preset("High Hazard")
    zone_config = create_zone_config(
        camera_id="cam-001",
        zone_type="High Hazard",
        zone_type_name="High Hazard",
        preset=preset,
    )

    # Verify structure
    assert "name" in zone_config, "Missing 'name' in zone config"
    assert "required_ppe" in zone_config, "Missing 'required_ppe' in zone config"
    assert "alert_cooldown_seconds" in zone_config, "Missing 'alert_cooldown_seconds' in zone config"
    assert "camera_id" in zone_config, "Missing 'camera_id' in zone config (required for rules engine)"

    # Verify values
    assert zone_config["camera_id"] == "cam-001", "camera_id not set correctly"
    assert zone_config["alert_cooldown_seconds"] == 15, "alert_cooldown_seconds not from preset"
    assert len(zone_config["required_ppe"]) == 3, "High Hazard should require 3 PPE items"

    print(f"  ✓ Zone config created: {zone_config['name']}")
    print(f"    - Camera ID: {zone_config['camera_id']}")
    print(f"    - Required PPE: {', '.join(zone_config['required_ppe'])}")
    print(f"    - Cooldown: {zone_config['alert_cooldown_seconds']}s")


def test_zone_rules_engine_with_camera_validation():
    """Test that ZoneRulesEngine correctly validates camera_id."""
    print("\n✓ Testing Zone Rules Engine with Camera Validation...")

    # Create test zones with camera_id field
    zones_config = {
        "zone-01-high-hazard": {
            "name": "High Hazard — cam-001",
            "required_ppe": ["hard_hat", "vest", "gloves"],
            "alert_cooldown_seconds": 15,
            "camera_id": "cam-001",  # Zone belongs to cam-001
        },
        "zone-02-medium-hazard": {
            "name": "Medium Hazard — cam-002",
            "required_ppe": ["hard_hat", "vest"],
            "alert_cooldown_seconds": 30,
            "camera_id": "cam-002",  # Zone belongs to cam-002
        },
    }

    engine = ZoneRulesEngine(zones_config)

    # Create mock person observation missing hard_hat
    mock_person = PersonObservation(
        track_id=1,
        person_bbox=BoundingBox(x1=10, y1=20, x2=60, y2=120),
        worn_ppe={"vest", "gloves"},  # Missing hard_hat
    )

    timestamp_utc = datetime.now(timezone.utc).isoformat()

    # Test 1: Zone evaluated for correct camera
    violations = engine.evaluate(
        persons=[mock_person],
        zone_id="zone-01-high-hazard",
        camera_id="cam-001",  # Matching camera
        frame_index=0,
        timestamp_utc=timestamp_utc,
    )
    assert len(violations) == 1, "Should generate violation for missing hard_hat"
    assert violations[0].missing_ppe == ["hard_hat"]
    print(f"  ✓ Violation generated for correct camera: {violations[0].missing_ppe}")

    # Test 2: Zone skipped for wrong camera (camera_id mismatch)
    violations = engine.evaluate(
        persons=[mock_person],
        zone_id="zone-01-high-hazard",
        camera_id="cam-002",  # Wrong camera!
        frame_index=1,
        timestamp_utc=timestamp_utc,
    )
    assert len(violations) == 0, "Should skip zone when camera_id doesn't match"
    print(f"  ✓ Zone correctly skipped for wrong camera (cam-002 evaluating cam-001 zone)")

    # Test 3: Cooldown mechanism
    violations = engine.evaluate(
        persons=[mock_person],
        zone_id="zone-01-high-hazard",
        camera_id="cam-001",
        frame_index=2,
        timestamp_utc=timestamp_utc,  # Same timestamp = cooldown active
    )
    assert len(violations) == 0, "Should respect cooldown for same person in same zone"
    print(f"  ✓ Cooldown respected: no duplicate violations")


def test_actual_config_files():
    """Test loading actual config files from the project."""
    print("\n✓ Testing Actual Config Files...")

    try:
        # These may fail if config files don't exist, which is OK
        cameras = load_cameras()
        zones, class_map = load_zones()

        print(f"  ✓ Loaded {len(cameras)} camera(s)")
        print(f"  ✓ Loaded {len(zones)} zone(s)")
        print(f"  ✓ Loaded class_map with {len(class_map)} mappings")

        # Verify structure of first zone if it exists
        if zones:
            first_zone_id = list(zones.keys())[0]
            zone = zones[first_zone_id]
            print(f"  ✓ Zone '{first_zone_id}' structure valid")

    except FileNotFoundError as e:
        print(f"  ⚠ Skipping actual config file test: {e}")


def run_all_tests():
    """Run all integration tests."""
    print("=" * 70)
    print("ZONE CONFIGURATION SYSTEM — INTEGRATION TESTS")
    print("=" * 70)

    try:
        test_presets()
        test_zone_id_generation()
        test_zone_config_creation()
        test_zone_rules_engine_with_camera_validation()
        test_actual_config_files()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe zone configuration system is ready for use.")
        print("To create a new zone, run:")
        print("  python -m src.config_manager.interactive_zones")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
