"""
Authentication utilities for API access.
"""
from typing import Optional, Tuple
import httpx
from src.utils.config import AUTH_CONFIG
from loguru import logger


async def authenticate() -> Optional[Tuple[str, str]]:
    """
    Authenticate using Basic Auth and get custom token.
    
    This follows the authentication pattern:
    1. Use Basic Auth header with base64-encoded credentials
    2. POST to /token/gettoken to get a custom token
    3. Return both userpass and token for use in API calls
    
    Returns:
        Optional[Tuple[str, str]]: (userpass, token) if authentication succeeds, None otherwise
            - userpass: Base64-encoded username:password for Authorization header
            - token: Custom token for TokenKey header
    """
    userpass = AUTH_CONFIG.get("userpass")
    
    if not userpass:
        logger.warning("⚠️ No authentication credentials configured. API calls may fail.")
        return None
    
    headers = {
        "Authorization": f"Basic {userpass}",
        "Content-Type": "application/json"
    }

    try:
        logger.debug(f"🔐 Attempting authentication to: {AUTH_CONFIG['token_endpoint']}")
        logger.debug(f"🔐 Using userpass: {userpass[:20]}...")
        
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:  # verify=False for self-signed certs
            response = await client.post(AUTH_CONFIG["token_endpoint"], headers=headers)
            
            logger.debug(f"🔐 Auth response status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                logger.debug(f"🔐 Auth response data: {response_data}")
                token = response_data.get("token")
                
                if token:
                    logger.info("✅ Authentication successful")
                    return (userpass, token)
                else:
                    logger.error(f"❌ No token in response: {response.text}")
                    return None
            else:
                logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Authentication error: {type(e).__name__}: {str(e)}")
        logger.exception("Full authentication error traceback:")
        return None
