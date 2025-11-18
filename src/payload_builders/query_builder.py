from src.models.query import QueryPayload
from src.models.natural_language import SendEmailLLMRequest, ReadSqlLLMRequest

class QueryBuilder:
    """Repository for handling query-related operations"""

    @staticmethod
    async def build_send_email_query_payload(data: SendEmailLLMRequest) -> QueryPayload:
        """
        Create a QueryPayload instance.

        Args:
            data (SendEmailLLMRequest): The input data containing connection and query information.

        Returns:
            QueryPayload: An instance of QueryPayload with the provided parameters.
        """

        connection_id = data.variables[0].connection
        sql = data.variables[0].query
        folder_id = ""
        return QueryPayload(connectionId=connection_id, sql=sql, folderId=folder_id)


    @staticmethod
    async def build_read_sql_query_payload(data: ReadSqlLLMRequest) -> QueryPayload:
        """
        Create a QueryPayload instance.

        Args:
            data (ReadSqlLLMRequest): The input data containing connection and query information.

        Returns:
            QueryPayload: An instance of QueryPayload with the provided parameters.
        """

        connection_id = data.variables[0].connection
        sql = data.variables[0].query
        folder_id = ""
        return QueryPayload(connectionId=connection_id, sql=sql, folderId=folder_id)