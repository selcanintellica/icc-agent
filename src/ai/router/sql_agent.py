"""
Refactored SQL Agent with Dependency Injection and Error Handling.

This module provides SQL generation following SOLID principles with:
- Structured error handling
- Retry logic for LLM calls
- User-friendly error messages
"""

import os
import json
import logging
from typing import List, Optional

from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from src.utils.table_api_client import fetch_table_definitions
from src.utils.retry import retry, RetryPresets, RetryExhaustedError
from src.errors import (
    LLMError,
    LLMTimeoutError,
    LLMParsingError,
    LLMUnavailableError,
    InvalidSQLError,
    ValidationError,
    ErrorCode,
    ErrorHandler,
)

logger = logging.getLogger(__name__)


class SQLSpec(BaseModel):
    """SQL specification from natural language."""
    sql: str
    reasoning: str = ""
    error: Optional[str] = None  # For error cases


class SQLAgentConfig:
    """Configuration for SQL Agent following SRP."""
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.1,
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0
    ):
        self.model_name = model_name or os.getenv("SQL_MODEL_NAME", "qwen2.5-coder:7b")
        self.temperature = temperature
        self.base_url = base_url
        self.timeout = timeout


class SQLPromptBuilder:
    """
    Builds SQL generation prompts.
    
    Following Single Responsibility Principle - only responsible for prompt building.
    """
    
    TEMPLATE = """You are a SQL query generator. Convert natural language requests into SQL queries.

You have access to the following database tables with their complete definitions:

{schema_definitions}

IMPORTANT RULES:
- Generate valid SQL queries using ONLY the tables and columns defined above
- Use proper table and column names exactly as shown in the schema
- Pay attention to data types and constraints
- Use JOINs when querying related tables (check Foreign Keys section)
- Be conservative - if unclear, use simple SELECT queries
- Qualify table names with schema if provided (e.g., SALES.customers)
- Only use tables that are listed in the schema above
- Follow the example queries provided for each table as guidance

RESPONSE FORMAT:
Respond with JSON only: {{"sql": "YOUR_SQL_HERE", "reasoning": "brief explanation"}}

Examples of good responses:
{{"sql": "SELECT * FROM customers WHERE country = 'USA'", "reasoning": "Filtering customers by country column"}}
{{"sql": "SELECT c.first_name, c.last_name, SUM(o.total_amount) as total FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.first_name, c.last_name", "reasoning": "Joining customers with orders to calculate total per customer"}}

Now generate SQL for the user's request below:
"""
    
    def build_prompt(self, schema_definitions: str) -> str:
        """
        Build the SQL generation prompt with schema definitions.
        
        Args:
            schema_definitions: Schema definitions string
            
        Returns:
            str: Formatted prompt
        """
        return self.TEMPLATE.format(schema_definitions=schema_definitions)


class SchemaFetcher:
    """
    Fetches schema definitions from API.
    
    Following Single Responsibility Principle - only responsible for schema fetching.
    """
    
    @staticmethod
    def fetch_schemas(
        connection: str,
        schema: str,
        selected_tables: List[str]
    ) -> str:
        """
        Fetch table definitions from API.
        
        Args:
            connection: Database connection name
            schema: Database schema name
            selected_tables: List of table names
            
        Returns:
            str: Schema definitions or error message
        """
        if not connection or not schema or not selected_tables:
            logger.warning("Missing connection/schema/tables, cannot fetch definitions")
            return "ERROR: Connection, schema, and tables must be provided."
        
        logger.info("Fetching table definitions from API...")
        
        try:
            schema_definitions = fetch_table_definitions(connection, schema, selected_tables)
            
            if not schema_definitions or schema_definitions.strip() == "":
                logger.warning("No schema definitions fetched from API")
                return "ERROR: No table definitions found. Using default behavior."
            
            return schema_definitions
            
        except Exception as e:
            logger.error(f"Error fetching schema definitions: {e}")
            return f"ERROR: Failed to fetch schema definitions: {str(e)}"


class SQLParser:
    """
    Parses SQL from LLM responses with error handling.
    
    Following Single Responsibility Principle - only responsible for parsing.
    """
    
    @staticmethod
    def parse_response(content: str) -> SQLSpec:
        """
        Parse SQL from LLM response content.
        
        Args:
            content: Raw LLM response
            
        Returns:
            SQLSpec: Parsed SQL specification
            
        Raises:
            LLMParsingError: If response cannot be parsed
        """
        logger.info(f"SQL Agent raw response: {content[:200]}...")
        
        if not content or not content.strip():
            raise LLMParsingError(
                message="Empty response from LLM",
                user_message="The AI returned an empty response. Please try rephrasing your request.",
                raw_response=content
            )
        
        try:
            # Clean up markdown code blocks if present
            cleaned = content
            if "```json" in content:
                cleaned = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                cleaned = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(cleaned)
            sql = parsed.get("sql", "")
            reasoning = parsed.get("reasoning", "")
            
            if not sql:
                raise LLMParsingError(
                    message="No SQL found in LLM response",
                    user_message="The AI couldn't generate a SQL query. Please try a different request.",
                    raw_response=content
                )
            
        except json.JSONDecodeError as e:
            # If not JSON, check if entire response is SQL
            logger.warning(f"SQL Agent: Could not parse JSON: {e}, checking for raw SQL")
            
            # Check if response looks like SQL
            sql_keywords = ["select", "insert", "update", "delete", "create", "drop", "alter"]
            content_lower = content.lower().strip()
            
            if any(content_lower.startswith(kw) for kw in sql_keywords):
                sql = content.strip()
                reasoning = "Direct SQL output (non-JSON response)"
            else:
                raise LLMParsingError(
                    message=f"Could not parse LLM response as JSON or SQL: {e}",
                    user_message="The AI response couldn't be understood. Please try rephrasing your request.",
                    raw_response=content[:300],
                    cause=e
                )
        
        # Clean SQL
        sql = sql.strip().rstrip(";")
        
        # Basic SQL validation
        if not SQLParser._is_valid_sql(sql):
            raise InvalidSQLError(
                sql=sql,
                message=f"Generated SQL appears invalid: {sql[:100]}",
                user_message="The generated SQL query appears to be invalid. Please try a different request."
            )
        
        logger.info(f"SQL Agent: Generated SQL: {sql}")
        
        return SQLSpec(sql=sql, reasoning=reasoning)
    
    @staticmethod
    def _is_valid_sql(sql: str) -> bool:
        """Basic SQL validation."""
        if not sql:
            return False
        
        sql_lower = sql.lower().strip()
        valid_starts = ["select", "insert", "update", "delete", "create", "drop", "alter", "with"]
        
        return any(sql_lower.startswith(kw) for kw in valid_starts)


class SQLAgent:
    """
    Agent that generates SQL from natural language with error handling.
    
    Refactored following SOLID principles with:
    - Dependency injection
    - Retry logic for LLM calls
    - Structured error handling
    """
    
    def __init__(
        self,
        config: Optional[SQLAgentConfig] = None,
        prompt_builder: Optional[SQLPromptBuilder] = None,
        schema_fetcher: Optional[SchemaFetcher] = None,
        parser: Optional[SQLParser] = None
    ):
        """
        Initialize SQLAgent with dependency injection.
        
        Args:
            config: Configuration for the agent
            prompt_builder: Builder for SQL prompts
            schema_fetcher: Fetcher for schema definitions
            parser: Parser for SQL responses
        """
        self.config = config or SQLAgentConfig()
        self.prompt_builder = prompt_builder or SQLPromptBuilder()
        self.schema_fetcher = schema_fetcher or SchemaFetcher()
        self.parser = parser or SQLParser()
        
        self.llm = ChatOllama(
            model=self.config.model_name,
            temperature=self.config.temperature,
            base_url=self.config.base_url,
            keep_alive="3600s",  # Keep model loaded for 1 hour
            num_predict=2048,  # SQL queries can be longer than parameter extraction
        )
    
    def generate_sql(
        self,
        user_input: str,
        connection: str = None,
        schema: str = None,
        selected_tables: List[str] = None
    ) -> SQLSpec:
        """
        Generate SQL query from natural language input.
        
        Args:
            user_input: Natural language description of desired query
            connection: Database connection name
            schema: Database schema name
            selected_tables: List of table names to include in context
            
        Returns:
            SQLSpec: Generated SQL with reasoning
        """
        logger.info(f"SQL Agent: Generating SQL from: '{user_input}'")
        logger.info(f"Connection: {connection}, Schema: {schema}")
        logger.info(f"Selected tables: {selected_tables}")
        
        # Validate input
        if not user_input or not user_input.strip():
            return SQLSpec(
                sql="",
                reasoning="",
                error="Please provide a description of what data you want to query."
            )
        
        try:
            # Fetch schema definitions
            schema_definitions = self.schema_fetcher.fetch_schemas(
                connection, schema, selected_tables
            )
            
            # Check for schema fetch errors
            if schema_definitions.startswith("ERROR:"):
                logger.warning(f"Schema fetch issue: {schema_definitions}")
                # Continue with limited context
            
            # Build prompt
            prompt = self.prompt_builder.build_prompt(schema_definitions)
            
            # Generate SQL with retry
            return self._generate_with_retry(prompt, user_input)
            
        except LLMTimeoutError as e:
            logger.error(f"LLM timeout: {e}")
            return SQLSpec(
                sql="SELECT * FROM customers LIMIT 10",
                reasoning=f"Timeout occurred. Using fallback query.",
                error=e.user_message
            )
            
        except LLMParsingError as e:
            logger.error(f"LLM parsing error: {e}")
            return SQLSpec(
                sql="SELECT * FROM customers LIMIT 10",
                reasoning=f"Could not parse response. Using fallback query.",
                error=e.user_message
            )
            
        except LLMUnavailableError as e:
            logger.error(f"LLM unavailable: {e}")
            return SQLSpec(
                sql="SELECT * FROM customers LIMIT 10",
                reasoning=f"AI service unavailable. Using fallback query.",
                error=e.user_message
            )
            
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            return SQLSpec(
                sql="SELECT * FROM customers LIMIT 10",
                reasoning=f"Error occurred: {e.user_message}. Using fallback query.",
                error=e.user_message
            )
            
        except Exception as e:
            logger.error(f"SQL Agent unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
            # Convert to ICC error
            icc_error = ErrorHandler.handle(e, {"user_input": user_input[:100]})
            return SQLSpec(
                sql="SELECT * FROM customers LIMIT 10",
                reasoning=f"Error occurred: {str(e)}. Using fallback query.",
                error=icc_error.user_message
            )
    
    @retry(config=RetryPresets.LLM_CALL)
    def _generate_with_retry(self, prompt: str, user_input: str) -> SQLSpec:
        """Generate SQL with automatic retry on failure."""
        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            
            response = self.llm.invoke(messages)
            
            if not response or not response.content:
                raise LLMParsingError(
                    message="Empty response from LLM",
                    user_message="The AI returned an empty response. Please try again."
                )
            
            # Parse response
            return self.parser.parse_response(response.content.strip())
            
        except TimeoutError as e:
            raise LLMTimeoutError(
                message=f"LLM request timed out: {e}",
                user_message="The AI is taking too long. Please try a simpler request.",
                timeout_seconds=self.config.timeout,
                cause=e
            )
        except ConnectionError as e:
            raise LLMUnavailableError(
                message=f"Could not connect to LLM: {e}",
                user_message="The AI assistant is currently unavailable. Please try again later.",
                model_name=self.config.model_name,
                cause=e
            )
        except (LLMError, InvalidSQLError):
            # Re-raise ICC errors as-is
            raise
        except Exception as e:
            # Check if it's a connection-related error
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                raise LLMTimeoutError(
                    message=f"LLM timeout: {e}",
                    user_message="The AI is taking too long. Please try again.",
                    cause=e
                )
            if "connection" in error_str or "connect" in error_str:
                raise LLMUnavailableError(
                    message=f"LLM connection error: {e}",
                    user_message="Unable to connect to the AI service. Please try again.",
                    cause=e
                )
            # Wrap unknown errors
            raise LLMError(
                error_code=ErrorCode.LLM_INVALID_RESPONSE,
                message=f"Unexpected LLM error: {e}",
                user_message="The AI encountered an unexpected error. Please try again.",
                cause=e
            )


# Factory function for creating SQLAgent instances
def create_sql_agent(
    config: Optional[SQLAgentConfig] = None,
    prompt_builder: Optional[SQLPromptBuilder] = None,
    schema_fetcher: Optional[SchemaFetcher] = None,
    parser: Optional[SQLParser] = None
) -> SQLAgent:
    """
    Factory function to create a SQLAgent instance.
    
    Args:
        config: Optional configuration
        prompt_builder: Optional prompt builder
        schema_fetcher: Optional schema fetcher
        parser: Optional SQL parser
        
    Returns:
        SQLAgent: Configured SQL agent instance
    """
    return SQLAgent(
        config=config,
        prompt_builder=prompt_builder,
        schema_fetcher=schema_fetcher,
        parser=parser
    )


# Create default instance for backward compatibility
_default_sql_agent = create_sql_agent()


def call_sql_agent(
    user_input: str,
    connection: str = None,
    schema: str = None,
    selected_tables: List[str] = None
) -> SQLSpec:
    """
    Call the SQL generation agent (backward compatibility function).
    
    Args:
        user_input: Natural language query description
        connection: Database connection name
        schema: Database schema name
        selected_tables: List of table names to include in context
        
    Returns:
        SQLSpec: Generated SQL with reasoning
    """
    return _default_sql_agent.generate_sql(
        user_input,
        connection=connection,
        schema=schema,
        selected_tables=selected_tables
    )
