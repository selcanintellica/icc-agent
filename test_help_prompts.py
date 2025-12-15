"""Test script to verify help prompts for each stage."""

import sys
from src.ai.router.memory import Memory
from src.ai.router.context.stage_context import Stage
from src.ai.router.utils.help_handler import HelpHandler
from src.ai.router.prompts.router_conversation_prompt import RouterConversationPrompt

def test_stage_help_prompt(stage: Stage, connection="TEST_CONN", schema="TEST_SCHEMA"):
    """Test help prompt generation for a stage."""
    print(f"\n{'='*80}")
    print(f"Testing Stage: {stage.value}")
    print(f"{'='*80}")
    
    # Create memory
    memory = Memory()
    memory.stage = stage
    memory.connection = connection
    memory.schema = schema
    memory.selected_tables = ["table1", "table2"]
    
    # Create help handler
    help_handler = HelpHandler()
    
    # Get stage description
    stage_desc = help_handler._get_stage_description(stage.value)
    print(f"\nStage Description: {stage_desc}")
    
    # Build stage help text
    stage_help_text = f"You are currently {stage_desc}."
    
    # Build prompt
    prompt = RouterConversationPrompt.build_stage_context(
        stage_value=stage.value,
        connection=connection,
        schema=schema,
        selected_tables=["table1", "table2"],
        user_input="help",
        stage_specific_help=stage_help_text
    )
    
    print(f"\nGenerated Prompt:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)
    print(f"Prompt Length: {len(prompt)} chars")
    
def test_param_gathering_help():
    """Test parameter gathering help prompt."""
    print(f"\n{'='*80}")
    print(f"Testing Parameter Gathering Help")
    print(f"{'='*80}")
    
    prompt = RouterConversationPrompt.build_param_gathering_context(
        current_tool="read_sql",
        last_question="What connection do you want to use?",
        gathered_params={"schema": "TEST_SCHEMA"},
        connection="TEST_CONN",
        schema="TEST_SCHEMA",
        selected_tables=["table1", "table2"],
        user_input="what are my options?"
    )
    
    print(f"\nGenerated Prompt:")
    print("-" * 80)
    print(prompt)
    print("-" * 80)
    print(f"Prompt Length: {len(prompt)} chars")

if __name__ == "__main__":
    # Test a few key stages
    test_stages = [
        Stage.START,
        Stage.ASK_JOB_TYPE,
        Stage.ASK_SQL_METHOD,
        Stage.EXECUTE_SQL,
        Stage.ASK_SECOND_SQL_METHOD,
        Stage.NEED_SECOND_USER_SQL,
        Stage.EXECUTE_COMPARE_SQL,
    ]
    
    for stage in test_stages:
        test_stage_help_prompt(stage)
    
    # Test parameter gathering
    test_param_gathering_help()
    
    print(f"\n{'='*80}")
    print("All tests completed!")
    print(f"{'='*80}")
