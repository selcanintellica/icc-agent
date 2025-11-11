from pydantic import BaseModel, Field
from typing import Optional


class APIResponse(BaseModel):
    """
    Models the response body containing a single object ID and error fields.
    """
    object_id: str = Field(alias="object", description="The unique identifier for the created/processed object.")
    # These fields are usually nullable in API responses
    errorCode: Optional[str] = Field(None, description="The error code, if an operation failed.")
    errorMessage: Optional[str] = Field(None, description="A detailed message describing the error, if any.")

