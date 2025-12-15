"""Compare SQL job parameter extraction prompt."""


class CompareSQLPrompt:
    """Prompt for compare_sql job parameter extraction."""

    TEMPLATE = """Extract params for compare_sql job.

CRITICAL RULES:
1. If "Last question" is asking for parameter X and user provides an answer, extract it as parameter X
2. IGNORE "ok", "okay", "yes", "no", "sure" UNLESS answering a yes/no question
3. Do NOT invent or assume parameter values
4. Return action="ASK" if any params missing (question will be auto-generated)
5. Key columns and mapped columns are ALREADY set from UI mapping (do NOT ask for them)

Required params:
1. schemas: Schema name for comparison results (UI shows dropdown)
2. table_name: Table name to save comparison results
3. job_name: Name for this comparison job (for ICC job list)

CONTEXT: User has already:
- Generated two SQL queries (first_sql, second_sql)
- Mapped columns via UI (first_table_keys, second_table_keys, first_table_columns, second_table_columns)
- Selected reporting type (reporting)

IMPORTANT: Match the user's answer to the last question asked. Do NOT skip parameters or make assumptions.

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""

    def get_prompt(self) -> str:
        """Get the compare_sql prompt."""
        return self.TEMPLATE