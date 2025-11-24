"""Test authentication to ICC API"""
import httpx
import asyncio

async def test_auth():
    print("Testing authentication to: https://172.16.22.13:8084/token/gettoken")
    print("Using credentials: admin:admin (YWRtaW46YWRtaW4=)")
    print("-" * 60)
    
    headers = {
        "Authorization": "Basic YWRtaW46YWRtaW4=",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.post(
                "https://172.16.22.13:8084/token/gettoken",
                headers=headers
            )
            
            print(f"✅ Status Code: {response.status_code}")
            print(f"📄 Response Headers: {dict(response.headers)}")
            print(f"📦 Response Body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n🎉 SUCCESS!")
                print(f"Token: {data.get('token', 'NOT FOUND')}")
                return data.get('token')
            else:
                print(f"\n❌ Authentication failed with status {response.status_code}")
                return None
                
    except httpx.ConnectError as e:
        print(f"❌ Connection Error: Cannot reach server")
        print(f"   Details: {str(e)}")
        print(f"\n💡 Possible issues:")
        print(f"   - Server is not running at 172.16.22.13:8084")
        print(f"   - Firewall is blocking the connection")
        print(f"   - Network is not accessible")
    except httpx.TimeoutException as e:
        print(f"❌ Timeout Error: Server did not respond in time")
        print(f"   Details: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}")
        print(f"   Details: {str(e)}")
    
    return None

if __name__ == "__main__":
    token = asyncio.run(test_auth())
    
    if token:
        print(f"\n✅ You can use this token in your API calls!")
        print(f"   Authorization: Basic YWRtaW46YWRtaW4=")
        print(f"   TokenKey: {token}")
