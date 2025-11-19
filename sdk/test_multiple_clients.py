#!/usr/bin/env python3
"""
Test that multiple libraries can use Klyne simultaneously without conflicts.

This test verifies the fix for the dependency conflict issue where:
  - If library A depends on library B
  - And library B uses Klyne
  - Then library A should also be able to use Klyne

The original issue was that only one client could exist per process.
"""

import os
import sys

# Set testing environment before importing klyne
os.environ["KLYNE_ENV"] = "test"

# Add the SDK to path
sys.path.insert(0, ".")

import klyne


def test_multiple_clients_coexist():
    """Test that multiple clients can be initialized and used simultaneously."""
    print("Testing multiple clients coexistence...")

    # Simulate Library B initializing Klyne
    client_b = klyne.init(
        api_key="klyne_test_key_b",
        project="library-b",
        package_version="2.0.0",
        enabled=False,
    )

    assert client_b is not None, "Library B client should be created"
    assert client_b.project == "library-b"
    print("✓ Library B initialized successfully")

    # Simulate Library A initializing Klyne (should NOT fail or warn)
    client_a = klyne.init(
        api_key="klyne_test_key_a",
        project="library-a",
        package_version="1.0.0",
        enabled=False,
    )

    assert client_a is not None, "Library A client should be created"
    assert client_a.project == "library-a"
    print("✓ Library A initialized successfully")

    # Verify both clients are different instances
    assert client_a is not client_b, "Clients should be separate instances"
    print("✓ Clients are separate instances")

    # Verify both clients are tracked in the registry
    from klyne.client import _clients

    assert "library-a" in _clients, "Library A should be in registry"
    assert "library-b" in _clients, "Library B should be in registry"
    assert _clients["library-a"] is client_a
    assert _clients["library-b"] is client_b
    print("✓ Both clients registered correctly")


def test_instance_based_api():
    """Test that each client can be used independently via instance methods."""
    print("\nTesting instance-based API...")

    # Initialize two separate clients
    client_x = klyne.init(
        api_key="klyne_test_key_x",
        project="library-x",
        package_version="1.0.0",
        enabled=False,
    )

    client_y = klyne.init(
        api_key="klyne_test_key_y",
        project="library-y",
        package_version="2.0.0",
        enabled=False,
    )

    # Both should be able to track events independently
    client_x.track("event_x", {"source": "library-x"})
    client_y.track("event_y", {"source": "library-y"})

    print("✓ Both clients can track events independently")

    # Test client-specific state management
    client_x.enable()
    client_y.disable()

    # Note: is_enabled() checks both self.enabled and transport state
    # Since transport is disabled in tests, we check the enabled flag directly
    assert client_x.enabled == True, "Client X should be enabled"
    assert client_y.enabled == False, "Client Y should be disabled"

    print("✓ Clients have independent state")


def test_same_project_returns_existing_client():
    """Test that initializing the same project twice returns the existing client."""
    print("\nTesting same project initialization...")

    # First initialization
    client1 = klyne.init(
        api_key="klyne_test_key_z",
        project="library-z",
        package_version="1.0.0",
        enabled=False,
    )

    # Second initialization with same project (should return existing)
    client2 = klyne.init(
        api_key="klyne_test_key_z",
        project="library-z",
        package_version="1.0.0",
        enabled=False,
    )

    assert client1 is client2, "Should return the same client instance"
    print("✓ Same project returns existing client")


def test_backward_compatibility():
    """Test that the module-level API still works (backward compatibility)."""
    print("\nTesting backward compatibility...")

    # Module-level init (old style)
    klyne.init(
        api_key="klyne_test_compat",
        project="compat-test",
        package_version="1.0.0",
        enabled=False,
    )

    # Module-level functions should work
    klyne.track("compat_event", {"test": True})
    klyne.flush(timeout=1.0)
    klyne.disable()
    klyne.enable()

    print("✓ Module-level API works (backward compatible)")


def test_no_auto_initialization():
    """Test that importing klyne doesn't auto-initialize."""
    print("\nTesting no auto-initialization...")

    # Import a fresh copy (simulate new import)
    from klyne.client import _internal_client

    # Internal client should NOT be initialized unless KLYNE_SELF_ANALYTICS=1
    assert (
        _internal_client is None
    ), "Internal client should not auto-initialize without env var"
    print("✓ No auto-initialization on import")


def test_nested_library_scenario():
    """
    Test the exact scenario from the bug report:
    Library A depends on Library B, both use Klyne.
    """
    print("\nTesting nested library scenario...")

    # Simulate library structure
    class LibraryB:
        """Simulates a library that uses Klyne."""

        def __init__(self):
            self.analytics = klyne.init(
                api_key="klyne_lib_b_key",
                project="dependency-lib",
                package_version="3.0.0",
                enabled=False,
            )

        def do_something(self):
            """Library B does its work and tracks analytics."""
            if self.analytics:
                self.analytics.track("lib_b_operation", {"status": "success"})
            return "Library B result"

    class LibraryA:
        """Simulates a library that depends on Library B and also uses Klyne."""

        def __init__(self):
            # Library A uses Library B
            self.dependency = LibraryB()

            # Library A also uses Klyne (this is what used to fail)
            self.analytics = klyne.init(
                api_key="klyne_lib_a_key",
                project="main-lib",
                package_version="5.0.0",
                enabled=False,
            )

        def do_something(self):
            """Library A uses Library B and tracks its own analytics."""
            result = self.dependency.do_something()

            if self.analytics:
                self.analytics.track("lib_a_operation", {"dependency_result": result})

            return "Library A result"

    # Create Library A (which creates Library B internally)
    lib_a = LibraryA()

    # Verify both libraries have working analytics clients
    assert lib_a.analytics is not None, "Library A should have analytics"
    assert lib_a.dependency.analytics is not None, "Library B should have analytics"
    assert (
        lib_a.analytics is not lib_a.dependency.analytics
    ), "Should have separate clients"

    print("✓ Library A analytics initialized:", lib_a.analytics.project)
    print("✓ Library B analytics initialized:", lib_a.dependency.analytics.project)

    # Both should be able to track events
    lib_a.do_something()

    print("✓ Nested library scenario works!")


def main():
    """Run all multiple client tests."""
    print("🧪 Klyne SDK Multiple Clients Test")
    print("=" * 50)

    try:
        test_multiple_clients_coexist()
        test_instance_based_api()
        test_same_project_returns_existing_client()
        test_backward_compatibility()
        test_no_auto_initialization()
        test_nested_library_scenario()

        print("\n✅ All multiple client tests passed!")
        print("\nFix Summary:")
        print("  • Multiple clients can coexist: ✓")
        print("  • Instance-based API works: ✓")
        print("  • Backward compatibility maintained: ✓")
        print("  • No auto-initialization: ✓")
        print("  • Nested library scenario works: ✓")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
