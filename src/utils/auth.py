"""
Authentication utilities for API access.
"""
from typing import Optional
import httpx
from src.utils.config import AUTH_CONFIG
from loguru import logger


async def authenticate() -> Optional[str]:
    """
    Authenticate with Keycloak/OAuth and return access token.
    
    Returns:
        Optional[str]: Access token if authentication succeeds, None otherwise
    """
    if not AUTH_CONFIG["username"] or not AUTH_CONFIG["password"]:
        logger.warning("⚠️ No authentication credentials configured. API calls may fail.")
        return None
    
    data = {
        "grant_type": AUTH_CONFIG["grant_type"],
        "client_id": AUTH_CONFIG["client_id"],
        "username": AUTH_CONFIG["username"],
        "password": AUTH_CONFIG["password"],
    }

    if AUTH_CONFIG["client_secret"]:
        data["client_secret"] = AUTH_CONFIG["client_secret"]

    try:
        async with httpx.AsyncClient(verify=False) as client:  # verify=False for self-signed certs
            response = await client.post(AUTH_CONFIG["token_endpoint"], data=data)
            
            if response.status_code == 200:
                token = response.json().get("access_token")
                logger.info("✅ Authentication successful")
                return token
            else:
                logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"❌ Authentication error: {str(e)}")
        return None
