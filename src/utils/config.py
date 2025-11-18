import os

API_CONFIG = {
    "api_base_url": os.getenv("API_BASE_URL", "https://172.16.22.13:8084/job/save"),
    "query_api_base_url": os.getenv("QUERY_API_BASE_URL", "https://172.16.22.13:8084/utility/query"),
    "timeout": 30.0,
}

# Authentication configuration (Keycloak or similar)
AUTH_CONFIG = {
    "token_endpoint": os.getenv("TOKEN_ENDPOINT", "https://172.16.22.13:8084/auth/realms/your-realm/protocol/openid-connect/token"),
    "grant_type": os.getenv("GRANT_TYPE", "password"),
    "client_id": os.getenv("CLIENT_ID", "your-client-id"),
    "client_secret": os.getenv("CLIENT_SECRET", ""),  # Optional
    "username": os.getenv("AUTH_USERNAME", ""),
    "password": os.getenv("AUTH_PASSWORD", ""),
}