"""
HTTP status code enumeration.

Provides type-safe HTTP status codes following Open/Closed Principle.
New status codes can be added without modifying existing code.
"""

from enum import IntEnum


class HTTPStatus(IntEnum):
    """
    HTTP status code enumeration.

    Using IntEnum allows direct integer comparison while providing
    named constants for better code readability.
    """

    # Success codes (2xx)
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204

    # Client error codes (4xx)
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422

    # Server error codes (5xx)
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

    @classmethod
    def is_success(cls, status_code: int) -> bool:
        """Check if status code indicates success (2xx)."""
        return 200 <= status_code < 300

    @classmethod
    def is_client_error(cls, status_code: int) -> bool:
        """Check if status code indicates client error (4xx)."""
        return 400 <= status_code < 500

    @classmethod
    def is_server_error(cls, status_code: int) -> bool:
        """Check if status code indicates server error (5xx)."""
        return 500 <= status_code < 600

    @classmethod
    def is_error(cls, status_code: int) -> bool:
        """Check if status code indicates any error (4xx or 5xx)."""
        return status_code >= 400


class HTTPMethod:
    """HTTP method constants."""
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    PATCH = "patch"
    HEAD = "head"
    OPTIONS = "options"
