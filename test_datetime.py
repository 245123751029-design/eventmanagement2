#!/usr/bin/env python3
"""
Test datetime format compatibility
"""

from datetime import datetime, timezone, timedelta

# Test the exact format the backend uses
now = datetime.now(timezone.utc)
expires_at = now + timedelta(days=7)

# Convert to ISO format like the backend does
now_iso = now.isoformat()
expires_at_iso = expires_at.isoformat()

print(f"Current time: {now}")
print(f"Current time ISO: {now_iso}")
print(f"Expires at: {expires_at}")
print(f"Expires at ISO: {expires_at_iso}")

# Test parsing back
try:
    parsed_expires = datetime.fromisoformat(expires_at_iso)
    print(f"Parsed expires: {parsed_expires}")
    print(f"Is future: {parsed_expires > datetime.now(timezone.utc)}")
except Exception as e:
    print(f"Error parsing: {e}")

# Test with the format we stored in DB
test_format = "2025-11-24T14:56:33.964183+00:00"
try:
    parsed_test = datetime.fromisoformat(test_format)
    print(f"Parsed test format: {parsed_test}")
    print(f"Test is future: {parsed_test > datetime.now(timezone.utc)}")
except Exception as e:
    print(f"Error parsing test format: {e}")