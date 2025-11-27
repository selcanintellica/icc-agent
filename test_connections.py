"""Test connection fetching"""
import asyncio
import logging
from src.utils.fetch_connections import fetch_and_map_connections
from src.utils.auth import authenticate

logging.basicConfig(level=logging.INFO)

async def test():
    print("\n🔌 Testing connection fetch...\n")
    
    # Authenticate
    auth_result = await authenticate()
    if auth_result:
        userpass, token = auth_result
        headers = {'Authorization': f'Basic {userpass}', 'TokenKey': token}
        print(f"✅ Authentication successful\n")
    else:
        headers = None
        print(f"⚠️ Authentication failed, trying without auth\n")
    
    # Fetch connections
    try:
        conns = await fetch_and_map_connections(auth_headers=headers)
        print(f"\n✅ Fetched {len(conns)} connections:\n")
        for name, info in list(conns.items())[:10]:
            print(f"  • {name} ({info.get('db_type', 'Unknown')})")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
