#!/usr/bin/env python3
"""
Example usage of the Klyne Python SDK.

This demonstrates how package maintainers would integrate Klyne
into their Python packages for analytics collection.
"""

import sys

# Add the SDK to the path for testing
sys.path.insert(0, '.')

import klyne


def main():
    """Example integration of Klyne SDK."""
    
    print("🚀 Klyne SDK Example")
    print("=" * 50)
    
    # Initialize Klyne (this would normally be done in your package's __init__.py)
    print("1. Initializing Klyne...")
    klyne.init(
        base_url="http://localhost:8000",  # Use local server for testing
        api_key="klyne__HVqua3oQTYeF_w_u_dCh4JmA21KMcwL6j5gmPNsEvU",
        project="asd",
        package_version="1.0.0",
        enabled=True,  # Disabled for demo to avoid network calls
        debug=True
    )
    klyne.enable()  # Enable analytics for this example
    print(f"   ✓ Klyne initialized (enabled: {klyne.is_enabled()})")
    
    # Track some example events
    print("\n2. Tracking events...")
    
    # Track a function call
    klyne.track_event(
        entry_point="main_function",
        extra_data={"demo": True, "feature": "basic"}
    )
    print("   ✓ Tracked main_function event")
    
    # Track a feature usage
    klyne.track_event(
        entry_point="advanced_feature",
        extra_data={"premium": True, "complexity": "high"}
    )
    print("   ✓ Tracked advanced_feature event")
    
    # Track an API call
    klyne.track_event(
        entry_point="api_endpoint",
        extra_data={"endpoint": "/data", "method": "GET"}
    )
    print("   ✓ Tracked api_endpoint event")
    
    print("\n3. SDK State Management...")
    print(f"   Current state: {'enabled' if klyne.is_enabled() else 'disabled'}")
    
    # Demonstrate enable/disable
    klyne.enable()
    print(f"   After enable(): {'enabled' if klyne.is_enabled() else 'disabled'}")
    
    print("\n4. Flushing events...")
    klyne.flush(timeout=2.0)
    print("   ✓ Events flushed")
    
    print("\n✅ Example completed successfully!")
    print("\nIn a real integration, you would:")
    print("  • Set enabled=True to send real analytics")
    print("  • Use your actual Klyne API key")
    print("  • Call klyne.init() in your package's __init__.py")
    print("  • Track events throughout your package")


if __name__ == "__main__":
    main()