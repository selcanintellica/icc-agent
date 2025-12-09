"""
Read SQL job parameter extraction prompt.
"""


class ReadSQLPrompt:
    """Prompt for read_sql job parameter extraction."""
    
    TEMPLATE = """Extract params for read_sql job.

CRITICAL RULES:
1. If "Last question" is asking for parameter X and user provides an answer, extract it as parameter X
2. IGNORE "ok", "okay", "yes", "no", "sure" UNLESS they are answering a yes/no question
3. Do NOT invent or assume parameter values
4. Return action="ASK" if any params missing (question will be auto-generated)

Required params:
- name: Job name (any string the user provides)
- execute_query: Save results to DB? (yes=true, no=false)
- write_count: Track row count? (yes=true, no=false)

{execute_query_hint}

{write_count_hint}

IMPORTANT: Match the user's answer to the last question asked. Do NOT skip parameters or make assumptions.

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""
    
    def get_prompt(self, execute_query: bool = False, write_count: bool = False) -> str:
        """Get the read_sql prompt with conditional hints."""
        execute_query_hint = ""
        if execute_query:
            execute_query_hint = """IF execute_query=true, ALSO need:
- result_schema (string): Schema to write query results
- table_name (string): Table name to store query results
- drop_before_create (boolean): Drop table before creating? (yes=true, no=false)"""
        
        write_count_hint = ""
        if write_count:
            write_count_hint = """IF write_count=true, ALSO need:
- write_count_connection (string): Connection for row count (default: same as query connection)
- write_count_schema (string): Schema for row count table
- write_count_table (string): Table name to store row count"""
        
        return self.TEMPLATE.format(execute_query_hint=execute_query_hint, write_count_hint=write_count_hint)
