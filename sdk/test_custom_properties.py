#!/usr/bin/env python3
"""
Test script to verify custom properties are captured in the Pydantic schema.
"""

import sys
sys.path.insert(0, '../app')

from src.schemas.analytics import AnalyticsEventCreate
from datetime import datetime

def test_custom_properties_at_root():
    """Test that custom properties at root level are captured in extra_data."""

    # Create event data with custom properties at root level
    event_data = {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "package_name": "test-package",
        "package_version": "1.0.0",
        "python_version": "3.11.0",
        "os_type": "Darwin",
        "event_timestamp": datetime.now().isoformat(),
        "entry_point": "user_login",
        # Custom properties at root level
        "user_id": "12345",
        "login_method": "google",
        "custom_field": "value"
    }

    print("Testing custom properties at root level...")
    print(f"Input data keys: {list(event_data.keys())}")

    # Validate with Pydantic
    event = AnalyticsEventCreate(**event_data)

    print(f"\nValidation successful!")
    print(f"Event entry_point: {event.entry_point}")
    print(f"Event extra_data: {event.extra_data}")

    # Verify custom properties were captured
    assert event.extra_data is not None, "extra_data should not be None"
    assert "user_id" in event.extra_data, "user_id should be in extra_data"
    assert event.extra_data["user_id"] == "12345", "user_id value should match"
    assert "login_method" in event.extra_data, "login_method should be in extra_data"
    assert event.extra_data["login_method"] == "google", "login_method value should match"
    assert "custom_field" in event.extra_data, "custom_field should be in extra_data"

    print("\n✅ All assertions passed!")
    print(f"✅ Custom properties successfully captured in extra_data")
    return True

def test_mixed_extra_data_and_properties():
    """Test mixing explicit extra_data with root-level custom properties."""

    event_data = {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "package_name": "test-package",
        "package_version": "1.0.0",
        "python_version": "3.11.0",
        "os_type": "Darwin",
        "event_timestamp": datetime.now().isoformat(),
        "entry_point": "feature_used",
        # Explicit extra_data
        "extra_data": {
            "nested_field": "nested_value"
        },
        # Custom properties at root level
        "feature_name": "export",
        "file_format": "csv"
    }

    print("\n\nTesting mixed extra_data and custom properties...")
    print(f"Input extra_data: {event_data['extra_data']}")
    print(f"Input custom properties: feature_name, file_format")

    event = AnalyticsEventCreate(**event_data)

    print(f"\nValidation successful!")
    print(f"Event extra_data: {event.extra_data}")

    # Verify both nested and root-level custom properties were captured
    assert event.extra_data is not None
    assert "nested_field" in event.extra_data, "nested_field should be preserved"
    assert event.extra_data["nested_field"] == "nested_value"
    assert "feature_name" in event.extra_data, "feature_name should be in extra_data"
    assert event.extra_data["feature_name"] == "export"
    assert "file_format" in event.extra_data, "file_format should be in extra_data"
    assert event.extra_data["file_format"] == "csv"

    print("\n✅ All assertions passed!")
    print(f"✅ Both explicit extra_data and custom properties were merged correctly")
    return True

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Pydantic Schema Custom Property Capture")
    print("=" * 70)

    try:
        test_custom_properties_at_root()
        test_mixed_extra_data_and_properties()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe backend schema now properly captures custom properties")
        print("sent at the root level and stores them in extra_data.")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
