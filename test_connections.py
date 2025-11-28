"""Test connection and schema fetching using new ICC API client"""
import asyncio
import logging
from src.utils.connection_api_client import ICCAPIClient
from src.utils.auth import authenticate

logging.basicConfig(level=logging.INFO)

async def test():
    print("\n🔌 Testing ICC API Client...\n")
    
    # Authenticate
    auth_result = await authenticate()
    if auth_result:
        userpass, token = auth_result
        headers = {'Authorization': f'Basic {userpass}', 'TokenKey': token}
        print(f"✅ Authentication successful\n")
    else:
        headers = None
        print(f"⚠️ Authentication failed, trying without auth\n")
    
    # Create client
    client = ICCAPIClient(auth_headers=headers)
    
    # Test 1: Fetch connections
    try:
        print("\n📋 Test 1: Fetching connections...")
        conns = await client.fetch_connections()
        print(f"✅ Fetched {len(conns)} connections:\n")
        for name, info in list(conns.items())[:10]:
            print(f"  • {name} ({info.get('db_type', 'Unknown')}) - ID: {info.get('id')}")
        
        # Test 2: Fetch schemas for first connection
        if conns:
            first_name = list(conns.keys())[0]
            first_id = conns[first_name]['id']
            print(f"\n📋 Test 2: Fetching schemas for {first_name} (ID: {first_id})...")
            schemas = await client.fetch_schemas(first_id)
            print(f"✅ Fetched {len(schemas)} schemas")
            print(f"  First 15: {schemas[:15]}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
