from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar

T = TypeVar("T")


class JobResponse(BaseModel):
    """
    Models the response body containing a single object ID and error fields.
    This represents the actual API response format from the job endpoints.
    """
    object_id: str = Field(alias="object", description="The unique identifier for the created/processed object.")
    # These fields are usually nullable in API responses
    errorCode: Optional[str] = Field(None, description="The error code, if an operation failed.")
    errorMessage: Optional[str] = Field(None, description="A detailed message describing the error, if any.")


class APIResponse(BaseModel, Generic[T]):
    """
    Generic API response wrapper that can contain any data type.
    Provides a standardized way to handle successful and error responses.
    """
    success: bool = Field(description="Whether the operation was successful")
    data: Optional[T] = Field(None, description="The response data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    status_code: int = Field(description="HTTP status code")
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def success_response(cls, data: T, status_code: int = 200) -> "APIResponse[T]":
        """Create a successful response"""
        return cls(success=True, data=data, error=None, status_code=status_code)
    
    @classmethod
    def error_response(cls, error: str, status_code: int = 500) -> "APIResponse[None]":
        """Create an error response"""
        return cls(success=False, data=None, error=error, status_code=status_code)

