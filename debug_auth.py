#!/usr/bin/env python3
"""
Debug authentication flow
"""

import requests
import json
from datetime import datetime, timezone, timedelta

def test_auth_debug():
    base_url = "https://ticketmaster-70.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Test with the manual token we created
    token = "session_admin_manual"
    
    print(f"Testing authentication with token: {token}")
    
    # Test auth/me endpoint
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(f"{api_url}/auth/me", headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            # Let's also test without Bearer prefix
            headers2 = {
                'Authorization': token,
                'Content-Type': 'application/json'
            }
            response2 = requests.get(f"{api_url}/auth/me", headers=headers2, timeout=30)
            print(f"Without Bearer - Status Code: {response2.status_code}")
            print(f"Without Bearer - Response: {response2.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_auth_debug()