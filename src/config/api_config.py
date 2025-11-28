"""API and authentication configuration."""
import os
from dotenv import load_dotenv

# Load .env file FIRST, and override system environment variables
load_dotenv(override=True)

# TEMPORARY FIX: Directly set the values from .env, ignoring system environment variables
# Read .env values directly
from pathlib import Path
env_file = Path(__file__).parent.parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

API_CONFIG = {
    "api_base_url": os.getenv("API_BASE_URL", "https://127.0.0.1:8082/job/save"),
    "query_api_base_url": os.getenv("QUERY_API_BASE_URL", "https://127.0.0.1:8082/utility/query"),
    "timeout": 30.0,
}

# Authentication configuration (Basic Auth + Custom Token)
AUTH_CONFIG = {
    "token_endpoint": os.getenv("TOKEN_ENDPOINT", "https://127.0.0.1:8082/token/gettoken"),
    # Base64 encoded username:password (default: admin:admin = YWRtaW46YWRtaW4=)
    # Generate at https://www.base64encode.org/
    "userpass": os.getenv("AUTH_USERPASS", "YWRtaW46YWRtaW4="),
}

# ICC API configuration (connections and schemas)
ICC_API_CONFIG = {
    "base_url": os.getenv("ICC_API_BASE_URL", "https://172.16.22.13:8084"),
    "connection_list_url": os.getenv("ICC_CONNECTION_LIST_URL", "https://172.16.22.13:8084/connection/list"),
    "schema_endpoint_template": "/utility/connection/{connection_id}",  # Format with connection_id
    "timeout": 30.0,
}

# Table Definitions API configuration
TABLE_API_CONFIG = {
    "base_url": os.getenv("TABLE_API_BASE_URL", "http://localhost:8000/api/tables"),
    "timeout": int(os.getenv("TABLE_API_TIMEOUT", "10")),
    "use_mock": os.getenv("TABLE_API_MOCK", "false").lower() in ("true", "1", "yes"),
}
