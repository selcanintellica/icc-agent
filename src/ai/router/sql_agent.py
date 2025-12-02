"""
Refactored SQL Agent with Dependency Injection.

This module provides SQL generation following SOLID principles:
- Single Responsibility: Only responsible for SQL generation
- Open/Closed: Easy to extend with new features
- Liskov Substitution: Can be replaced with mock for testing
- Interface Segregation: Clean interfaces
- Dependency Inversion: Depends on abstractions
"""

import os
import json
import logging
from typing import List, Optional
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from src.utils.table_api_client import fetch_table_definitions

logger = logging.getLogger(__name__)


class SQLSpec(BaseModel):
    """SQL specification from natural language."""
    sql: str
    reasoning: str = ""


class SQLAgentConfig:
    """Configuration for SQL Agent following SRP."""
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = 0.1,
        base_url: str = "http://localhost:11434"
    ):
        self.model_name = model_name or os.getenv("SQL_MODEL_NAME", "qwen2.5-coder:7b")
        self.temperature = temperature
        self.base_url = base_url


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
            logger.warning("⚠️ Missing connection/schema/tables, cannot fetch definitions")
            return "ERROR: Connection, schema, and tables must be provided."
        
        logger.info(f"🌐 Fetching table definitions from API...")
        schema_definitions = fetch_table_definitions(connection, schema, selected_tables)
        
        if not schema_definitions or schema_definitions.strip() == "":
            logger.warning("⚠️ No schema definitions fetched from API")
            return "ERROR: No table definitions found. Using default behavior."
        
        return schema_definitions


class SQLParser:
    """
    Parses SQL from LLM responses.
    
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
        """
        logger.info(f"📝 SQL Agent raw response: {content[:200]}...")
        
        try:
            # Clean up markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            sql = parsed.get("sql", "")
            reasoning = parsed.get("reasoning", "")
        except json.JSONDecodeError:
            # If not JSON, assume entire response is SQL
            logger.warning("⚠️ SQL Agent: Could not parse JSON, using raw response as SQL")
            sql = content
            reasoning = "Direct SQL output"
        
        # Clean SQL
        sql = sql.strip().rstrip(";")
        
        logger.info(f"✅ SQL Agent: Generated SQL: {sql}")
        
        return SQLSpec(sql=sql, reasoning=reasoning)


class SQLAgent:
    """
    Agent that generates SQL from natural language.
    
    Refactored following SOLID principles with dependency injection.
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
        logger.info(f"🔮 SQL Agent: Generating SQL from: '{user_input}'")
        logger.info(f"🔌 Connection: {connection}, Schema: {schema}")
        logger.info(f"📊 Selected tables: {selected_tables}")
        
        try:
            # Fetch schema definitions
            schema_definitions = self.schema_fetcher.fetch_schemas(
                connection, schema, selected_tables
            )
            
            # Build prompt
            prompt = self.prompt_builder.build_prompt(schema_definitions)
            
            # Generate SQL
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse response
            return self.parser.parse_response(response.content.strip())
        
        except Exception as e:
            logger.error(f"❌ SQL Agent error: {str(e)}")
            # Fallback
            return SQLSpec(
                sql="SELECT * FROM customers LIMIT 10",
                reasoning=f"Error occurred: {str(e)}. Using fallback query."
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
