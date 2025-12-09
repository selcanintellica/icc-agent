"""
Simple diagnostic test for the message endpoint.
This will show the actual error message from the backend.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

print("Testing message endpoint...")
print("="*60)

try:
    # Create a session first
    print("\n1. Creating session...")
    session_response = requests.post(
        f"{BASE_URL}/api/chat/sessions",
        json={},
        timeout=10
    )
    
    if session_response.status_code != 200:
        print(f"❌ Failed to create session: {session_response.status_code}")
        print(f"Response: {session_response.text}")
        exit(1)
    
    session_data = session_response.json()
    session_id = session_data['session_id']
    print(f"✓ Session created: {session_id[:8]}...")
    
    # Try to send a message
    print("\n2. Sending message...")
    message_response = requests.post(
        f"{BASE_URL}/api/chat/message",
        json={
            "session_id": session_id,
            "message": "help"
        },
        timeout=30
    )
    
    print(f"\nStatus Code: {message_response.status_code}")
    print(f"Response Headers: {dict(message_response.headers)}")
    print(f"\nResponse Body:")
    print("="*60)
    
    try:
        response_data = message_response.json()
        print(json.dumps(response_data, indent=2))
    except:
        print(message_response.text)
    
    if message_response.status_code == 200:
        print("\n✓ Message endpoint works!")
    else:
        print(f"\n❌ Message endpoint returned error: {message_response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to backend. Is it running on port 8000?")
except requests.exceptions.Timeout:
    print("❌ Request timed out (>30s)")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
