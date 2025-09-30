#!/usr/bin/env python3
"""
Test script to verify the service layer works correctly.
"""
import os
import sys

# Set environment variable for service layer
os.environ['USE_SERVICE_LAYER'] = 'true'

print("Testing service layer with USE_SERVICE_LAYER=true...")

try:
    import app
    print("SUCCESS: App imports successfully with service layer enabled")
except Exception as e:
    print(f"FAIL: App failed to import with service layer: {e}")
    sys.exit(1)