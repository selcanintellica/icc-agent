"""
Simple test script for the staged router.
Run this to test the router flow before using the web interface.
"""
import asyncio
import logging
from src.ai.router import handle_turn, Memory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_conversation():
    """Test a full conversation flow."""
    memory = Memory()
    
    print("\n" + "="*60)
    print("🧪 TESTING STAGED ROUTER")
    print("="*60 + "\n")
    
    # Turn 1: Initial greeting
    print("USER: Hi")
    memory, response = await handle_turn(memory, "Hi")
    print(f"AGENT: {response}\n")
    
    # Turn 2: Provide SQL query
    print("USER: get customers from USA")
    memory, response = await handle_turn(memory, "get customers from USA")
    print(f"AGENT: {response}\n")
    
    # Turn 3: Confirm execution
    print("USER: yes, run it")
    memory, response = await handle_turn(memory, "yes, run it")
    print(f"AGENT: {response}\n")
    
    # Turn 4: Provide connection (if asked)
    if "connection" in response.lower():
        print("USER: oracle_prod")
        memory, response = await handle_turn(memory, "oracle_prod")
        print(f"AGENT: {response}\n")
    
    # Turn 5: Say done
    print("USER: done")
    memory, response = await handle_turn(memory, "done")
    print(f"AGENT: {response}\n")
    
    print("="*60)
    print("✅ Test completed!")
    print(f"Final stage: {memory.stage.value}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_conversation())
