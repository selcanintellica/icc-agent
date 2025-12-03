"""
Configuration module for ICC application.

Loads configuration from environment variables with sensible defaults.
Uses standard dotenv patterns - override=True means .env takes precedence.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
# override=True means .env values take precedence over system environment
load_dotenv(override=True)

# API Configuration
API_CONFIG = {
    "api_base_url": os.getenv("API_BASE_URL", "https://127.0.0.1:8082/job/save"),
    "query_api_base_url": os.getenv("QUERY_API_BASE_URL", "https://127.0.0.1:8082/utility/query"),
    "timeout": float(os.getenv("API_TIMEOUT", "60.0")),
}

# Authentication Configuration (Basic Auth + Custom Token)
AUTH_CONFIG = {
    "token_endpoint": os.getenv("TOKEN_ENDPOINT", "https://127.0.0.1:8082/token/gettoken"),
    # Base64 encoded username:password (default: admin:admin = YWRtaW46YWRtaW4=)
    # Generate at https://www.base64encode.org/
    "userpass": os.getenv("AUTH_USERPASS", "YWRtaW46YWRtaW4="),
}