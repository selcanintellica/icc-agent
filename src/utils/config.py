import os

API_CONFIG = {
    "api_base_url": os.getenv("API_BASE_URL", "https://172.16.22.13:8084/job/save"),
    "timeout": 30.0,
}