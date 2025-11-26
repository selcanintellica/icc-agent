from src.models.query import QueryPayload
from src.models.natural_language import SendEmailLLMRequest, ReadSqlLLMRequest
from src.utils.connections import get_connection_id

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

        connection_name = data.variables[0].connection
        connection_id = get_connection_id(connection_name) or connection_name
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
        from loguru import logger

        connection_name = data.variables[0].connection
        connection_id = get_connection_id(connection_name) or connection_name
        logger.info(f"[QueryBuilder] Connection name: '{connection_name}' -> Connection ID: '{connection_id}'")

        sql = data.variables[0].query
        folder_id = ""

        payload = QueryPayload(connectionId=connection_id, sql=sql, folderId=folder_id)
        logger.info(f"[QueryBuilder] Built QueryPayload: connectionId='{payload.connectionId}', sql='{sql[:100]}...', folderId='{folder_id}'")

        return payload