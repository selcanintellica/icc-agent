from src.utils.config import API_CONFIG
from src.models.query import QueryPayload, QueryResponse
from src.models.save_job_response import APIResponse
from src.repositories.base_repository import BaseRepository


class QueryRepository(BaseRepository):

    # Although this method called get, it actually sends a POST request with the query payload
    @staticmethod
    async def get_column_names(self, data: QueryPayload) -> APIResponse[QueryResponse]:
        """
        Get column names by analyzing a SQL query.
        
        Args:
            data: QueryPayload with connection and SQL query
            
        Returns:
            APIResponse[QueryResponse]: Response containing column names
        """
        # Need to override base_url for query endpoint - use full URL
        endpoint = API_CONFIG['query_api_base_url']
        response = await self.post_request(endpoint, data, QueryResponse)
        return response

