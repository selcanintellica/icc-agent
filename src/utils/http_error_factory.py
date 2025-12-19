"""
HTTP Error Factory with Strategy Pattern.

Creates appropriate ICC error types based on HTTP status codes using strategy pattern.
Follows Open/Closed Principle - new error types can be added without modifying existing code.
"""

import logging
from typing import Dict, Callable, Optional, Any

from src.utils.http_status import HTTPStatus
from src.utils.response_parser import ResponseParser
from src.errors import (
    ICCBaseError,
    HTTPError,
    NetworkTimeoutError,
    APIUnavailableError,
    AuthenticationError,
    ValidationError,
    JobCreationFailedError,
    DuplicateJobNameError,
    ErrorCode,
)

logger = logging.getLogger(__name__)


class HTTPErrorFactory:
    """
    Factory for creating ICC errors from HTTP responses using strategy pattern.

    Uses a dictionary of status code -> error creation strategy for O(1) lookup
    instead of long if-elif chains. Follows Open/Closed Principle.
    """

    def __init__(self, response_parser: Optional[ResponseParser] = None):
        """
        Initialize error factory with response parser.

        Args:
            response_parser: Parser for extracting info from responses (injected dependency)
        """
        self.response_parser = response_parser or ResponseParser()
        self._error_strategies: Dict[int, Callable] = self._build_error_strategies()

    def _build_error_strategies(self) -> Dict[int, Callable]:
        """
        Build mapping of status codes to error creation strategies.

        Returns:
            Dict mapping status codes to error creation functions
        """
        return {
            HTTPStatus.UNAUTHORIZED: self._create_unauthorized_error,
            HTTPStatus.FORBIDDEN: self._create_forbidden_error,
            HTTPStatus.NOT_FOUND: self._create_not_found_error,
            HTTPStatus.CONFLICT: self._create_conflict_error,
            HTTPStatus.REQUEST_TIMEOUT: self._create_timeout_error,
        }

    def create_error(
        self,
        status_code: int,
        response_body: Any,
        url: str,
        cause: Optional[Exception] = None
    ) -> ICCBaseError:
        """
        Create appropriate ICC error based on HTTP status code.

        Args:
            status_code: HTTP status code
            response_body: Response body (may be dict or str)
            url: Request URL
            cause: Original exception (if any)

        Returns:
            Appropriate ICCBaseError subclass
        """
        # Extract error message from response
        error_msg = self.response_parser.extract_error_message(response_body)

        # Check for specific error patterns (e.g., duplicate job name)
        if self._is_duplicate_name_error(error_msg):
            job_name = self.response_parser.extract_job_name(response_body, error_msg)
            return DuplicateJobNameError(
                job_name=job_name,
                message=error_msg,
                cause=cause
            )

        # Use strategy pattern for status code mapping
        error_strategy = self._error_strategies.get(status_code)
        if error_strategy:
            return error_strategy(error_msg, url, response_body, cause)

        # Handle ranges (5xx server errors)
        if HTTPStatus.is_server_error(status_code):
            return self._create_server_error(error_msg, url, status_code, response_body, cause)

        # Default HTTP error
        return self._create_default_http_error(error_msg, status_code, response_body, cause)

    def _is_duplicate_name_error(self, error_msg: str) -> bool:
        """Check if error indicates duplicate name."""
        return self.response_parser.is_duplicate_name_error(error_msg)

    # Error creation strategies

    def _create_unauthorized_error(
        self,
        error_msg: str,
        url: str,
        response_body: Any,
        cause: Optional[Exception]
    ) -> AuthenticationError:
        """Create unauthorized (401) error."""
        return AuthenticationError(
            error_code=ErrorCode.AUTH_FAILED,
            message=f"Unauthorized: {error_msg}",
            user_message="Authentication failed. Please refresh and try again.",
            details={"url": url, "status_code": HTTPStatus.UNAUTHORIZED},
            cause=cause
        )

    def _create_forbidden_error(
        self,
        error_msg: str,
        url: str,
        response_body: Any,
        cause: Optional[Exception]
    ) -> AuthenticationError:
        """Create forbidden (403) error."""
        return AuthenticationError(
            error_code=ErrorCode.AUTH_FAILED,
            message=f"Forbidden: {error_msg}",
            user_message="You don't have permission to perform this action.",
            details={"url": url, "status_code": HTTPStatus.FORBIDDEN},
            cause=cause
        )

    def _create_not_found_error(
        self,
        error_msg: str,
        url: str,
        response_body: Any,
        cause: Optional[Exception]
    ) -> HTTPError:
        """Create not found (404) error."""
        return HTTPError(
            message=f"Resource not found: {error_msg}",
            user_message="The requested resource was not found.",
            status_code=HTTPStatus.NOT_FOUND,
            cause=cause
        )

    def _create_conflict_error(
        self,
        error_msg: str,
        url: str,
        response_body: Any,
        cause: Optional[Exception]
    ) -> JobCreationFailedError:
        """Create conflict (409) error."""
        return JobCreationFailedError(
            message=f"Conflict: {error_msg}",
            user_message="There was a conflict with existing data. Please try with different values.",
            details={"url": url, "status_code": HTTPStatus.CONFLICT},
            cause=cause
        )

    def _create_timeout_error(
        self,
        error_msg: str,
        url: str,
        response_body: Any,
        cause: Optional[Exception]
    ) -> NetworkTimeoutError:
        """Create timeout (408) error."""
        return NetworkTimeoutError(
            message=f"Request timeout: {error_msg}",
            user_message="The request timed out. Please try again.",
            cause=cause
        )

    def _create_server_error(
        self,
        error_msg: str,
        url: str,
        status_code: int,
        response_body: Any,
        cause: Optional[Exception]
    ) -> APIUnavailableError:
        """Create server error (5xx) error."""
        return APIUnavailableError(
            message=f"Server error ({status_code}): {error_msg}",
            user_message="The server encountered an error. Please try again later.",
            details={"url": url, "status_code": status_code},
            cause=cause
        )

    def _create_default_http_error(
        self,
        error_msg: str,
        status_code: int,
        response_body: Any,
        cause: Optional[Exception]
    ) -> HTTPError:
        """Create generic HTTP error for unmapped status codes."""
        return HTTPError(
            message=f"HTTP {status_code}: {error_msg}",
            user_message="The request failed. Please try again.",
            status_code=status_code,
            response_body=str(response_body)[:500] if response_body else None,
            cause=cause
        )
