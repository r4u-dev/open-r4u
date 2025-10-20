#!/usr/bin/env python3
"""Test script to verify call path extraction with mocked OpenAI."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unittest.mock import Mock, patch
from r4u.utils import extract_call_path


def level_3():
    """Third level function."""
    return extract_call_path()


def level_2():
    """Second level function."""
    return level_3()


def level_1():
    """First level function."""
    return level_2()


def main():
    """Test call path extraction at different levels."""
    print("Testing call path extraction...")
    print()
    
    # Test from main
    path, line = extract_call_path()
    print(f"Called from main:")
    print(f"  Path: {path}")
    print(f"  Line: {line}")
    print()
    
    # Test from nested functions
    path, line = level_1()
    print(f"Called from level_1->level_2->level_3:")
    print(f"  Path: {path}")
    print(f"  Line: {line}")
    print()
    
    # Verify expected format
    if "test_call_path_simple.py" in path:
        print("✓ File name captured correctly")
    else:
        print(f"✗ Expected 'test_call_path_simple.py' in path, got: {path}")
    
    if "level_1" in path and "level_2" in path and "level_3" in path:
        print("✓ Full call chain captured")
    else:
        print(f"✗ Expected 'level_1->level_2->level_3' in path")
    
    if "->" in path:
        print("✓ Chain separator present")
    else:
        print("✗ Expected '->' separator in path")


if __name__ == "__main__":
    main()