"""
SQL generation agent - converts natural language to SQL queries.
Uses a small LLM focused only on SQL generation.
"""
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger(__name__)


class SQLSpec(BaseModel):
    """SQL specification from natural language."""
    sql: str
    reasoning: str = ""


SQL_GENERATION_PROMPT = """You are a SQL query generator. Convert natural language requests into SQL queries.

DATABASE SCHEMA:

Table: customers
Columns:
  - customer_id (INT, Primary Key)
  - first_name (VARCHAR)
  - last_name (VARCHAR)
  - email (VARCHAR)
  - phone (VARCHAR)
  - country (VARCHAR)
  - city (VARCHAR)
  - address (VARCHAR)
  - created_date (DATE)

Table: orders
Columns:
  - order_id (INT, Primary Key)
  - customer_id (INT, Foreign Key → customers.customer_id)
  - order_date (DATE)
  - total_amount (DECIMAL)
  - status (VARCHAR) -- values: 'pending', 'completed', 'cancelled'
  - shipping_address (VARCHAR)

Table: products
Columns:
  - product_id (INT, Primary Key)
  - product_name (VARCHAR)
  - category (VARCHAR)
  - price (DECIMAL)
  - stock_quantity (INT)
  - supplier (VARCHAR)

Table: order_items
Columns:
  - order_item_id (INT, Primary Key)
  - order_id (INT, Foreign Key → orders.order_id)
  - product_id (INT, Foreign Key → products.product_id)
  - quantity (INT)
  - unit_price (DECIMAL)

Rules:
- Generate valid SQL queries using the schema above
- Use proper table and column names from the schema
- Use JOINs when querying related tables
- Be conservative - if unclear, use simple SELECT queries
- Only output the SQL query, no explanations unless asked

Examples:
User: "get customers from USA"
SQL: SELECT * FROM customers WHERE country = 'USA'

User: "first 10 orders from today"
SQL: SELECT * FROM orders WHERE order_date = CURRENT_DATE LIMIT 10

User: "show customer names with their total order amounts"
SQL: SELECT c.first_name, c.last_name, SUM(o.total_amount) as total_spent FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_id, c.first_name, c.last_name

Now generate SQL for the user's request. Respond with JSON: {"sql": "YOUR_SQL_HERE", "reasoning": "brief explanation"}
"""


class SQLAgent:
    """Agent that generates SQL from natural language."""
    
    def __init__(self):
        self.llm = ChatOllama(
            model=os.getenv("SQL_MODEL_NAME", "qwen2.5-coder:7b"),
            temperature=0.1,  # Low temperature for consistent SQL generation
            base_url="http://localhost:11434",
        )
    
    def generate_sql(self, user_input: str) -> SQLSpec:
        """
        Generate SQL query from natural language input.
        
        Args:
            user_input: Natural language description of desired query
            
        Returns:
            SQLSpec with generated SQL and reasoning
        """
        logger.info(f"🔮 SQL Agent: Generating SQL from: '{user_input}'")
        
        try:
            messages = [
                SystemMessage(content=SQL_GENERATION_PROMPT),
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


def call_sql_agent(user_input: str) -> SQLSpec:
    """
    Call the SQL generation agent.
    
    Args:
        user_input: Natural language query description
        
    Returns:
        SQLSpec with generated SQL
    """
    return sql_agent.generate_sql(user_input)
