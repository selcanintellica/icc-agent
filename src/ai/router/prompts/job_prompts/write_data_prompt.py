"""
Write data job parameter extraction prompt.
"""


class WriteDataPrompt:
    """Prompt for write_data job parameter extraction."""
    
    TEMPLATE = """Extract params for write_data job.

CRITICAL RULES:
1. If "Last question" is asking for parameter X and user provides an answer, extract it as parameter X
   - Be flexible with typos and abbreviations (e.g., "drp" → "drop", "trunc" → "truncate")
   - Match the intent even if spelling is imperfect
2. IGNORE "ok", "okay", "yes", "no", "sure" UNLESS answering a yes/no question
3. Do NOT invent or assume parameter values
4. Return action="ASK" if any params missing (question will be auto-generated)

Required params:
1. name: Job name (any string the user provides)
2. table: Target table name
3. connection: Database connection (UI shows dropdown)
4. schemas: Schema name (system fetches after connection)
5. drop_or_truncate: "drop", "truncate", or "none" (accept typos: "drp"="drop", "trunc"="truncate", variations like "clear"="truncate", "append"="none")
6. write_count: Track row count? (yes=true, no=false)

{write_count_hint}

IMPORTANT: Match the user's answer to the last question asked. Do NOT skip parameters or make assumptions.

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""
    
    def get_prompt(self, connections: str = "", write_count: bool = False) -> str:
        """Get the write_data prompt with conditional hints."""
        write_count_hint = ""
        if write_count:
            write_count_hint = """IF write_count=true, ALSO need:
- write_count_connection: Connection for row count (can be different from main)
- write_count_schema: Schema for row count table
- write_count_table: Table name to store row count"""
        return self.TEMPLATE.format(write_count_hint=write_count_hint)
