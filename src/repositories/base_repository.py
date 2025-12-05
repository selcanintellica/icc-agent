"""
Base repository with structured error handling.

Provides common functionality for API operations with proper error handling,
logging, and retry support.
"""

import logging
from typing import Optional, Dict, Any, TypeVar, Type

from httpx import AsyncClient, HTTPStatusError, TimeoutException, ConnectError
from pydantic import BaseModel

from src.models.save_job_response import APIResponse
from src.utils.config import API_CONFIG
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
    ErrorHandler,
)
from src.utils.retry import retry, RetryPresets, RetryExhaustedError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseRepository:
    """
    Base repository class for handling API operations with structured error handling.
    
    Provides:
    - Automatic retry for transient failures
    - Structured error responses
    - Consistent logging
    - HTTP error classification
    """

    HTTP_METHOD_PUT = "put"
    HTTP_METHOD_DELETE = "delete"
    HTTP_METHOD_POST = "post"
    HTTP_METHOD_GET = "get"

    HTTP_STATUS_CODE_CREATED = 201
    HTTP_STATUS_CODE_OK = 200
    HTTP_STATUS_CODE_NO_CONTENT = 204

    INTERNAL_SERVER_ERROR_STATUS_CODE = 500
    BAD_REQUEST_STATUS_CODE = 400
    UNAUTHORIZED_STATUS_CODE = 401
    FORBIDDEN_STATUS_CODE = 403
    NOT_FOUND_STATUS_CODE = 404
    CONFLICT_STATUS_CODE = 409
    TIMEOUT_STATUS_CODE = 408

    def __init__(self, client: AsyncClient):
        """
        Initialize repository with HTTP client.
        
        Args:
            client: Async HTTP client with authentication configured
        """
        self.client = client
        self.base_url = API_CONFIG["api_base_url"]

    async def _make_request(
        self,
        method: str,
        endpoint: str = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to the API with error handling.
        
        Args:
            method: HTTP method (get, post, put, delete)
            endpoint: API endpoint (appended to base_url)
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            HTTPError: For HTTP errors
            NetworkTimeoutError: For timeout errors
            APIUnavailableError: For connection errors
            AuthenticationError: For auth errors (401, 403)
        """
        # Build URL
        if endpoint and endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self.base_url}{endpoint if endpoint else ''}"
        
        logger.debug(f"Making {method.upper()} request to {url}")
        logger.info(f"[BaseRepository] Request payload: {self._truncate_for_log(data)}")

        try:
            if method.lower() == "post":
                response = await self.client.post(url, json=data, params=params)
            elif method.lower() == "get":
                response = await self.client.get(url, params=params)
            elif method.lower() == "put":
                response = await self.client.put(url, json=data, params=params)
            elif method.lower() == "delete":
                response = await self.client.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Parse response
            result = response.json()
            
            # Check for HTTP errors
            if response.status_code >= self.BAD_REQUEST_STATUS_CODE:
                raise self._create_http_error(response.status_code, result, url)
            
            logger.debug(f"API request successful - Status: {response.status_code}")
            return result
            
        except TimeoutException as e:
            logger.error(f"Request timeout for {url}: {str(e)}")
            raise NetworkTimeoutError(
                message=f"Request to {url} timed out",
                user_message="The server is taking too long to respond. Please try again.",
                cause=e
            )
            
        except ConnectError as e:
            logger.error(f"Connection error for {url}: {str(e)}")
            raise APIUnavailableError(
                message=f"Could not connect to {url}",
                user_message="Unable to connect to the server. Please check your connection and try again.",
                cause=e
            )
            
        except HTTPStatusError as e:
            logger.error(f"HTTP error for {url}: {e.response.status_code}")
            raise self._create_http_error(
                e.response.status_code,
                self._safe_json_parse(e.response),
                url,
                cause=e
            )
            
        except ICCBaseError:
            # Re-raise ICC errors as-is
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error in API request to {url}: {type(e).__name__}: {str(e)}")
            raise HTTPError(
                message=f"Unexpected error in API request: {str(e)}",
                user_message="An unexpected error occurred. Please try again.",
                cause=e
            )

    def _create_http_error(
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
            cause: Original exception
            
        Returns:
            Appropriate ICCBaseError subclass
        """
        # Extract error message from response
        error_msg = self._extract_error_message(response_body)
        
        # Check for specific error patterns
        if self._is_duplicate_name_error(error_msg):
            job_name = self._extract_job_name(response_body, error_msg)
            return DuplicateJobNameError(
                job_name=job_name,
                message=error_msg,
                cause=cause
            )
        
        # Map status codes to errors
        if status_code == self.UNAUTHORIZED_STATUS_CODE:
            return AuthenticationError(
                error_code=ErrorCode.AUTH_FAILED,
                message=f"Unauthorized: {error_msg}",
                user_message="Authentication failed. Please refresh and try again.",
                details={"url": url, "status_code": status_code},
                cause=cause
            )
        
        if status_code == self.FORBIDDEN_STATUS_CODE:
            return AuthenticationError(
                error_code=ErrorCode.AUTH_FAILED,
                message=f"Forbidden: {error_msg}",
                user_message="You don't have permission to perform this action.",
                details={"url": url, "status_code": status_code},
                cause=cause
            )
        
        if status_code == self.NOT_FOUND_STATUS_CODE:
            return HTTPError(
                message=f"Resource not found: {error_msg}",
                user_message="The requested resource was not found.",
                status_code=status_code,
                cause=cause
            )
        
        if status_code == self.CONFLICT_STATUS_CODE:
            return JobCreationFailedError(
                message=f"Conflict: {error_msg}",
                user_message="There was a conflict with existing data. Please try with different values.",
                details={"url": url, "status_code": status_code},
                cause=cause
            )
        
        if status_code == self.TIMEOUT_STATUS_CODE:
            return NetworkTimeoutError(
                message=f"Request timeout: {error_msg}",
                user_message="The request timed out. Please try again.",
                cause=cause
            )
        
        if status_code >= 500:
            return APIUnavailableError(
                message=f"Server error ({status_code}): {error_msg}",
                user_message="The server encountered an error. Please try again later.",
                details={"url": url, "status_code": status_code},
                cause=cause
            )
        
        # Default HTTP error
        return HTTPError(
            message=f"HTTP {status_code}: {error_msg}",
            user_message="The request failed. Please try again.",
            status_code=status_code,
            response_body=str(response_body)[:500] if response_body else None,
            cause=cause
        )

    def _extract_error_message(self, response_body: Any) -> str:
        """Extract error message from API response."""
        if isinstance(response_body, dict):
            # Try common error message fields
            for field in ["message", "error", "detail", "msg", "errorMessage"]:
                if field in response_body:
                    value = response_body[field]
                    if isinstance(value, str):
                        return value
                    elif isinstance(value, dict) and "message" in value:
                        return value["message"]
            return str(response_body)
        return str(response_body) if response_body else "Unknown error"

    def _is_duplicate_name_error(self, error_msg: str) -> bool:
        """Check if error indicates duplicate name."""
        error_lower = error_msg.lower()
        indicators = ["same name", "already exists", "duplicate", "name conflict"]
        return any(ind in error_lower for ind in indicators)

    def _extract_job_name(self, response_body: Any, error_msg: str) -> str:
        """Try to extract job name from error."""
        if isinstance(response_body, dict):
            for field in ["name", "jobName", "job_name"]:
                if field in response_body:
                    return str(response_body[field])
        # Try to extract from error message
        if "'" in error_msg:
            parts = error_msg.split("'")
            if len(parts) >= 2:
                return parts[1]
        return "unknown"

    def _safe_json_parse(self, response) -> Any:
        """Safely parse JSON response."""
        try:
            return response.json()
        except Exception:
            return response.text if hasattr(response, "text") else str(response)

    def _truncate_for_log(self, data: Any, max_length: int = 500) -> str:
        """Truncate data for logging."""
        if data is None:
            return "None"
        text = str(data)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    async def post_request(
        self,
        endpoint: str,
        data: BaseModel,
        response_model: Type[T]
    ) -> APIResponse[T]:
        """
        Send a POST request with structured error handling.
        
        Args:
            endpoint: API endpoint
            data: Request payload (Pydantic model)
            response_model: Expected response model type
            
        Returns:
            APIResponse with success or error information
        """
        logger.debug(f"Sending POST request to {endpoint}")
        
        try:
            result = await self._make_request(
                method=self.HTTP_METHOD_POST,
                endpoint=endpoint,
                data=data.model_dump(exclude_none=True, by_alias=True)
            )
            
            response = APIResponse.success_response(
                data=response_model(**result),
                status_code=self.HTTP_STATUS_CODE_CREATED
            )
            logger.debug(f"POST request successful at {endpoint}")
            return response
            
        except DuplicateJobNameError:
            # Re-raise to let handlers deal with it and enable retry with new name
            raise
            
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            return APIResponse.error_response(
                error=e.user_message,
                status_code=self.UNAUTHORIZED_STATUS_CODE
            )
            
        except NetworkTimeoutError as e:
            logger.error(f"Network timeout: {e}")
            return APIResponse.error_response(
                error=e.user_message,
                status_code=self.TIMEOUT_STATUS_CODE
            )
            
        except APIUnavailableError as e:
            logger.error(f"API unavailable: {e}")
            return APIResponse.error_response(
                error=e.user_message,
                status_code=self.INTERNAL_SERVER_ERROR_STATUS_CODE
            )
            
        except HTTPError as e:
            logger.error(f"HTTP error: {e}")
            status = e.details.get("status_code", self.BAD_REQUEST_STATUS_CODE) if e.details else self.BAD_REQUEST_STATUS_CODE
            return APIResponse.error_response(
                error=e.user_message,
                status_code=status
            )
            
        except ICCBaseError as e:
            logger.error(f"ICC error: {e}")
            return APIResponse.error_response(
                error=e.user_message,
                status_code=self.INTERNAL_SERVER_ERROR_STATUS_CODE
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in POST to {endpoint}: {type(e).__name__}: {str(e)}", exc_info=True)
            # Convert to ICC error for consistent handling
            icc_error = ErrorHandler.handle(e, {"endpoint": endpoint})
            return APIResponse.error_response(
                error=icc_error.user_message,
                status_code=self.INTERNAL_SERVER_ERROR_STATUS_CODE
            )

    async def get_request(
        self,
        endpoint: str,
        response_model: Type[T],
        params: Optional[Dict[str, Any]] = None
    ) -> APIResponse[T]:
        """
        Send a GET request with structured error handling.
        
        Args:
            endpoint: API endpoint
            response_model: Expected response model type
            params: Query parameters
            
        Returns:
            APIResponse with success or error information
        """
        logger.debug(f"Sending GET request to {endpoint}")
        
        try:
            result = await self._make_request(
                method=self.HTTP_METHOD_GET,
                endpoint=endpoint,
                params=params
            )
            
            response = APIResponse.success_response(
                data=response_model(**result),
                status_code=self.HTTP_STATUS_CODE_OK
            )
            logger.debug(f"GET request successful at {endpoint}")
            return response
            
        except ICCBaseError as e:
            logger.error(f"ICC error in GET: {e}")
            return APIResponse.error_response(
                error=e.user_message,
                status_code=self.INTERNAL_SERVER_ERROR_STATUS_CODE
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in GET to {endpoint}: {type(e).__name__}: {str(e)}", exc_info=True)
            icc_error = ErrorHandler.handle(e, {"endpoint": endpoint})
            return APIResponse.error_response(
                error=icc_error.user_message,
                status_code=self.INTERNAL_SERVER_ERROR_STATUS_CODE
            )
