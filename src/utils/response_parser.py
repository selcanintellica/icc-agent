"""
Response parsing utilities.

Extracts response parsing logic from BaseRepository following Single Responsibility Principle.
"""

from typing import Any


class ResponseParser:
    """
    Utility class for parsing API responses and extracting information.

    Separates parsing concerns from HTTP communication and error handling.
    """

    def extract_error_message(self, response_body: Any) -> str:
        """
        Extract error message from API response.

        Args:
            response_body: Raw response body (dict, str, or other)

        Returns:
            Extracted error message string
        """
        if isinstance(response_body, dict):
            # Try common error message fields in order of preference
            for field in ["message", "error", "detail", "msg", "errorMessage"]:
                if field in response_body:
                    value = response_body[field]
                    if isinstance(value, str):
                        return value
                    elif isinstance(value, dict) and "message" in value:
                        return value["message"]
            return str(response_body)
        return str(response_body) if response_body else "Unknown error"

    def is_duplicate_name_error(self, error_msg: str) -> bool:
        """
        Check if error message indicates a duplicate name conflict.

        Args:
            error_msg: Error message to check

        Returns:
            True if error indicates duplicate name
        """
        error_lower = error_msg.lower()
        indicators = [
            "same name",
            "already exists",
            "duplicate",
            "name conflict",
            "name already in use"
        ]
        return any(indicator in error_lower for indicator in indicators)

    def extract_job_name(self, response_body: Any, error_msg: str) -> str:
        """
        Try to extract job name from error response.

        Args:
            response_body: Response body (may contain job name)
            error_msg: Error message (may contain job name in quotes)

        Returns:
            Extracted job name or "unknown"
        """
        # Try to extract from response body fields
        if isinstance(response_body, dict):
            for field in ["name", "jobName", "job_name"]:
                if field in response_body:
                    return str(response_body[field])

        # Try to extract from error message (usually in quotes)
        if "'" in error_msg:
            parts = error_msg.split("'")
            if len(parts) >= 2:
                return parts[1]
        elif '"' in error_msg:
            parts = error_msg.split('"')
            if len(parts) >= 2:
                return parts[1]

        return "unknown"

    def safe_json_parse(self, response) -> Any:
        """
        Safely parse JSON response, falling back to text on failure.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON dict, response text, or string representation
        """
        try:
            return response.json()
        except Exception:
            return response.text if hasattr(response, "text") else str(response)

    def truncate_for_log(self, data: Any, max_length: int = 500) -> str:
        """
        Truncate data for logging to avoid excessive log sizes.

        Args:
            data: Data to truncate
            max_length: Maximum length before truncation

        Returns:
            Truncated string representation
        """
        if data is None:
            return "None"
        text = str(data)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
