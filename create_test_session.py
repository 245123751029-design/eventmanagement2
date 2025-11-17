#!/usr/bin/env python3
"""
Create test session using the exact same format as the backend
"""

from datetime import datetime, timezone, timedelta
import subprocess

def create_test_session():
    # Create datetime objects like the backend does
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)
    
    # Convert to ISO format like the backend does
    now_iso = now.isoformat()
    expires_at_iso = expires_at.isoformat()
    
    user_id = "test-admin-backend-format"
    session_token = "session_admin_backend_format"
    email = "test.admin.backend@example.com"
    
    print(f"Creating session with:")
    print(f"  created_at: {now_iso}")
    print(f"  expires_at: {expires_at_iso}")
    
    mongo_commands = f"""
    use test_database;
    db.users.deleteMany({{}});
    db.user_sessions.deleteMany({{}});
    db.users.insertOne({{
        id: "{user_id}",
        email: "{email}",
        name: "Test Admin User",
        picture: "https://via.placeholder.com/150",
        role: "admin",
        created_at: "{now_iso}"
    }});
    db.user_sessions.insertOne({{
        user_id: "{user_id}",
        session_token: "{session_token}",
        expires_at: "{expires_at_iso}",
        created_at: "{now_iso}"
    }});
    """
    
    try:
        result = subprocess.run(
            ['mongosh', '--eval', mongo_commands],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Test session created successfully")
            return session_token
        else:
            print(f"❌ Session creation failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Session creation error: {str(e)}")
        return None

if __name__ == "__main__":
    token = create_test_session()
    if token:
        print(f"Test token: {token}")
        
        # Test the token
        import requests
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get("https://ticketmaster-70.preview.emergentagent.com/api/auth/me", headers=headers)
        print(f"Auth test - Status: {response.status_code}, Response: {response.text}")