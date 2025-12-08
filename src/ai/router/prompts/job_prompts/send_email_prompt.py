"""
Send email job parameter extraction prompt.
"""


class SendEmailPrompt:
    """Prompt for send_email job parameter extraction."""
    
    TEMPLATE = """Extract params for send_email job.

CRITICAL RULES:
1. If "Last question" is asking for parameter X and user provides an answer, extract it as parameter X
2. IGNORE "ok", "okay", "yes", "no", "sure" UNLESS answering a yes/no question
3. For optional params like CC: if user says "no"/"none"/"skip", set to empty string ""
4. Do NOT invent or assume parameter values
5. Return action="ASK" if any params missing (question will be auto-generated)

Parameters needed:
- name: Job name (any string the user provides, NEVER "ok"/"okay"/"yes"/"no")
- to: Recipient email address
- subject: Email subject line
- text: Email body text (can be empty, but must be provided)
- cc: CC email addresses (optional, can be empty string)

IMPORTANT: Match the user's answer to the last question asked. Do NOT skip parameters or make assumptions.

Output JSON: {{"action": "ASK"|"TOOL", "params": {{...}}}}
Do NOT generate "question" field - it will be auto-generated."""
    
    def get_prompt(self) -> str:
        """Get the send_email prompt."""
        return self.TEMPLATE
