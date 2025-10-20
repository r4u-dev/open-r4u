#!/usr/bin/env python3
"""
Example demonstrating patch detection to avoid double-patching.

This example shows how the R4U HTTP integrations detect if a function
has already been patched to prevent double-patching.
"""

import requests
from r4u.integrations.http.requests import trace_session, PrintTracer


def demonstrate_patch_detection():
    """Demonstrate that patching the same session twice is safe."""
    print("=== Patch Detection Example ===")
    print()
    
    # Create a requests session
    session = requests.Session()
    print(f"Original send method: {session.send}")
    print(f"Has _r4u_patched attribute: {hasattr(session.send, '_r4u_patched')}")
    print()

    # First patch
    print("1. Applying first patch...")
    trace_session(session, PrintTracer())
    print(f"After first patch - send method: {session.send}")
    print(f"Has _r4u_patched attribute: {hasattr(session.send, '_r4u_patched')}")
    session_send = session.send
    print()
    
    # Second patch (should be ignored)
    print("2. Applying second patch (should be ignored)...")
    trace_session(session, PrintTracer())
    print(f"After second patch - send method: {session.send}")
    print(f"Has _r4u_patched attribute: {hasattr(session.send, '_r4u_patched')}")
    print()
    
    # Verify the method is the same (not double-wrapped)
    print("3. Verification:")
    print(f"✓ Method object is the same: {session_send is session.send}")
    print(f"✓ Still has the patch marker: {hasattr(session.send, '_r4u_patched')}")
    print()
    
    print("=== Example Complete ===")
    print("The session was only patched once, preventing double-wrapping!")


if __name__ == "__main__":
    demonstrate_patch_detection()
