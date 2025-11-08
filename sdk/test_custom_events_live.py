#!/usr/bin/env python3
"""
Test script to send custom events to the local server.
"""

import sys
sys.path.insert(0, '.')

import klyne

def main():
    print("Sending test custom events to local server...")
    print("=" * 60)

    # Initialize with local server
    klyne.init(
        base_url="http://localhost:8000",
        api_key="klyne__HVqua3oQTYeF_w_u_dCh4JmA21KMcwL6j5gmPNsEvU",
        project="asd",
        package_version="1.0.0",
        enabled=True,
        debug=True
    )

    # Send various custom events
    print("\n1. Sending user_login events...")
    for i in range(5):
        klyne.track('user_login', {
            'user_id': f'user_{i+1}',
            'login_method': 'google' if i % 2 == 0 else 'github',
            'session_duration': i * 100
        })
        print(f"   ✓ Sent user_login #{i+1}")

    print("\n2. Sending feature_used events...")
    for i in range(3):
        klyne.track('feature_used', {
            'feature_name': 'export' if i % 2 == 0 else 'import',
            'file_format': 'csv',
            'rows_count': (i+1) * 1000
        })
        print(f"   ✓ Sent feature_used #{i+1}")

    print("\n3. Sending error_occurred events...")
    for i in range(2):
        klyne.track('error_occurred', {
            'error_type': 'ValidationError',
            'module': 'data_processor',
            'severity': 'high' if i == 0 else 'low'
        })
        print(f"   ✓ Sent error_occurred #{i+1}")

    # Flush to ensure all events are sent
    print("\n4. Flushing events...")
    klyne.flush(timeout=5.0)
    print("   ✓ All events flushed")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("\nYou can now check the dashboard at:")
    print("http://localhost:8000/dashboard")
    print("\nLook for the 'Custom Event Tracking' widget!")

if __name__ == "__main__":
    main()
