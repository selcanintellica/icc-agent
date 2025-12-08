"""
SQL generation prompt builder.
"""


class SQLGenerationPrompt:
    """Builder for SQL generation prompts."""
    
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
    
    @staticmethod
    def build(schema_definitions: str) -> str:
        """
        Build SQL generation prompt with schema definitions.
        
        Args:
            schema_definitions: Complete schema definitions
            
        Returns:
            Formatted prompt string
        """
        return SQLGenerationPrompt.TEMPLATE.format(schema_definitions=schema_definitions)
