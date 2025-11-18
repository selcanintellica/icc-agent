"""
SQL generation agent - converts natural language to SQL queries.
Uses a small LLM focused only on SQL generation.
Dynamically loads table schemas from API.
"""
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
import json
import logging
from typing import List, Optional
from src.utils.table_api_client import fetch_table_definitions

logger = logging.getLogger(__name__)


class SQLSpec(BaseModel):
    """SQL specification from natural language."""
    sql: str
    reasoning: str = ""


SQL_GENERATION_PROMPT_TEMPLATE = """You are a SQL query generator. Convert natural language requests into SQL queries.

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


class SQLAgent:
    """Agent that generates SQL from natural language using dynamic schema loading."""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=os.getenv("SQL_MODEL_NAME", "qwen2.5-coder:7b"),
            temperature=0.1,  # Low temperature for consistent SQL generation
            base_url="http://localhost:11434",
        )
    
    def generate_sql(
        self, 
        user_input: str, 
        connection: str = None,
        schema: str = None,
        selected_tables: List[str] = None
    ) -> SQLSpec:
        """
        Generate SQL query from natural language input using table definitions from files.
        
        Args:
            user_input: Natural language description of desired query
            connection: Database connection name
            schema: Database schema name
            selected_tables: List of table names to include in context
            
        Returns:
            SQLSpec with generated SQL and reasoning
        """
        logger.info(f"🔮 SQL Agent: Generating SQL from: '{user_input}'")
        logger.info(f"� Connection: {connection}, Schema: {schema}")
        logger.info(f"📊 Selected tables: {selected_tables}")
        
        try:
            # Fetch table definitions from API
            if connection and schema and selected_tables:
                logger.info(f"🌐 Fetching table definitions from API...")
                schema_definitions = fetch_table_definitions(connection, schema, selected_tables)
                
                if not schema_definitions or schema_definitions.strip() == "":
                    logger.warning("⚠️ No schema definitions fetched from API, using fallback")
                    schema_definitions = "ERROR: No table definitions found. Using default behavior."
            else:
                logger.warning("⚠️ Missing connection/schema/tables, cannot fetch definitions")
                schema_definitions = "ERROR: Connection, schema, and tables must be provided."
            
            # Build prompt with loaded schema definitions
            prompt = SQL_GENERATION_PROMPT_TEMPLATE.format(schema_definitions=schema_definitions)
            
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content=user_input)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            logger.info(f"📝 SQL Agent raw response: {content[:200]}...")
            
            # Try to parse as JSON first
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
            
        except Exception as e:
            logger.error(f"❌ SQL Agent error: {str(e)}")
            # Fallback - try to extract any SQL-like content
            return SQLSpec(
                sql="SELECT * FROM customers LIMIT 10",
                reasoning=f"Error occurred: {str(e)}. Using fallback query."
            )


# Global instance
sql_agent = SQLAgent()


def call_sql_agent(
    user_input: str, 
    connection: str = None,
    schema: str = None,
    selected_tables: List[str] = None
) -> SQLSpec:
    """
    Call the SQL generation agent.
    
    Args:
        user_input: Natural language query description
        connection: Database connection name
        schema: Database schema name
        selected_tables: List of table names to include in context
        
    Returns:
        SQLSpec with generated SQL
    """
    return sql_agent.generate_sql(
        user_input, 
        connection=connection,
        schema=schema,
        selected_tables=selected_tables
    )
