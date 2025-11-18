from typing import Optional, Dict, Any, TypeVar, List
from httpx import AsyncClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from src.models.save_job_response import  APIResponse
from src.utils.config import API_CONFIG

from loguru import logger

T = TypeVar("T", bound=BaseModel)


class BaseRepository:
    """Base service class for handling API operations"""

    HTTP_METHOD_PUT = "put"
    HTTP_METHOD_DELETE = "delete"
    HTTP_METHOD_POST = "post"
    HTTP_METHOD_GET = "get"

    HTTP_STATUS_CODE_CREATED = 201
    HTTP_STATUS_CODE_OK = 200
    HTTP_STATUS_CODE_NO_CONTENT = 204
    HTTP_STATUS_CODE_GET = 201

    INTERNAL_SERVER_ERROR_STATUS_CODE = 500
    BAD_REQUEST_STATUS_CODE = 400

    def __init__(self, client: AsyncClient):
        self.client = client
        self.base_url = API_CONFIG["api_base_url"]

    async def _make_request(
        self,
        method: str,
        endpoint: str = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to the API. If full_url is provided, it is used directly."""

        # If endpoint is a full URL (starts with http), use it as-is, otherwise concatenate
        if endpoint and endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self.base_url}{endpoint if endpoint else ''}"
        logger.debug(f"Making {method.upper()} request to {url}")

        if method.lower() == "post":
            response = await self.client.post(url, json=data, params=params)
        elif method.lower() == "get":
            response = await self.client.get(url, params=params)
        else:
            raise NotImplementedError(f"Method {method.upper()} is not implemented")

        result = response.json()

        if response.status_code >= self.BAD_REQUEST_STATUS_CODE:
            error_msg = f"API request failed - Status: {response.status_code}, Response: {result}"
            logger.error(error_msg)
            raise HTTPException(status_code=response.status_code, detail=result)

        logger.debug(f"API request successful - Status: {response.status_code}")
        return result

    # post request
    async def post_request(self, endpoint: str, data: BaseModel, response_model: type[T]) -> APIResponse[T]:
        """Send a POST request to the given endpoint with the provided data."""
        logger.debug(f"Sending POST request to {endpoint}")
        try:
            result = await self._make_request(method=self.HTTP_METHOD_POST, endpoint=endpoint, data=data.model_dump(exclude_none=True, by_alias=True))
            response = APIResponse.success_response(data=response_model(**result), status_code=self.HTTP_STATUS_CODE_CREATED)
            logger.debug(f"POST request successful at {endpoint}")
            return response
        except HTTPException as e:
            logger.error(f"HTTP error while sending POST request to {endpoint} - Status: {e.status_code}, Detail: {e.detail}")
            return APIResponse.error_response(error=str(e.detail), status_code=e.status_code)
        except Exception as e:
            logger.error(f"Unexpected error while sending POST request to {endpoint} - {type(e).__name__}: {str(e)}", exc_info=True)
            return APIResponse.error_response(error=str(e), status_code=self.INTERNAL_SERVER_ERROR_STATUS_CODE)


