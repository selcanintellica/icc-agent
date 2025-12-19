from pydantic import BaseModel
from typing import Optional, List

class QueryPayload(BaseModel):
    """
    Models the payload for a SQL execution request.
    """
    connectionId: str
    sql: str
    folderId: Optional[str] = None


class DataObjectSimplified(BaseModel):
    # This matches the list of column names: ["EMPLOYEE_ID", "FIRST_NAME", ...]
    columns: List[str]

class QueryResponse(BaseModel):
    """
    Models the response from a SQL execution request. (Only simplified column data included)
    """
    object: DataObjectSimplified





