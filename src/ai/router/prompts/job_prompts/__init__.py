"""
Job-specific prompts for parameter extraction.

This package contains prompt classes for different job types.
"""

from .write_data_prompt import WriteDataPrompt
from .read_sql_prompt import ReadSQLPrompt
from .send_email_prompt import SendEmailPrompt
from .compare_sql_prompt import CompareSQLPrompt

__all__ = [
    "WriteDataPrompt",
    "ReadSQLPrompt",
    "SendEmailPrompt",
    "CompareSQLPrompt",
]
