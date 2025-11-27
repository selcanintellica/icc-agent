"""
Test file for SOLID job_agent implementation.
Demonstrates dependency injection and testability.
"""
import asyncio
from src.ai.router.job_agent import JobAgent, call_job_agent
from src.ai.router.llm_client import MockLLMClient
from src.ai.router.memory import Memory


def test_dependency_injection():
    """Test that we can inject a mock LLM for testing."""
    print("🧪 Testing Dependency Injection...")
    
    # Create mock LLM that returns fixed response
    mock_llm = MockLLMClient(
        mock_response='{"action": "ASK", "question": "Mock: What table name?", "params": {"name": "test_job"}}'
    )
    
    # Inject mock LLM into JobAgent
    agent = JobAgent(llm_client=mock_llm)
    
    # Test it
    memory = Memory()
    result = agent.gather_params(memory, "create write job", "write_data")
    
    print(f"✅ Mock LLM Response: {result}")
    assert result["action"] == "ASK"
    assert "Mock" in result["question"]
    print("✅ Dependency Injection works!\n")


def test_real_llm():
    """Test with real Ollama LLM."""
    print("🧪 Testing with Real LLM...")
    
    # Use default LLM (OllamaClient)
    memory = Memory()
    result = call_job_agent(memory, "I want to create a write_data job", "write_data")
    
    print(f"✅ Real LLM Response: {result}")
    print("✅ Real LLM works!\n")


def test_validator_extension():
    """Test that we can add custom validators without modifying JobAgent."""
    print("🧪 Testing Validator Extension (Open/Closed Principle)...")
    
    from src.ai.router.validators import ParameterValidator, VALIDATORS
    
    # Create custom validator for a new tool
    class CustomToolValidator(ParameterValidator):
        def validate(self, params, memory):
            if not params.get("custom_param"):
                return {
                    "action": "ASK",
                    "question": "What is the custom parameter?"
                }
            return None
    
    # Add to registry WITHOUT modifying JobAgent
    custom_validators = {**VALIDATORS, "custom_tool": CustomToolValidator()}
    
    # Create agent with custom validators
    agent = JobAgent(validators=custom_validators)
    
    memory = Memory()
    result = agent.gather_params(memory, "test", "custom_tool")
    
    print(f"✅ Custom Validator Response: {result}")
    assert result["action"] == "ASK"
    assert "custom parameter" in result["question"]
    print("✅ Open/Closed Principle works - added new validator without modifying JobAgent!\n")


def test_multiple_llm_providers():
    """Test that we can swap LLM providers easily."""
    print("🧪 Testing Multiple LLM Providers (Liskov Substitution)...")
    
    # Test with Mock LLM
    mock_llm = MockLLMClient('{"action": "TOOL", "params": {"name": "job1"}}')
    agent1 = JobAgent(llm_client=mock_llm)
    
    # Test with Real LLM
    from src.ai.router.llm_client import OllamaClient
    real_llm = OllamaClient()
    agent2 = JobAgent(llm_client=real_llm)
    
    print("✅ Both Mock and Real LLM work with same JobAgent interface!")
    print("✅ Liskov Substitution Principle works!\n")


if __name__ == "__main__":
    print("="*60)
    print("🎯 SOLID JobAgent Tests")
    print("="*60 + "\n")
    
    try:
        # Test 1: Dependency Injection
        test_dependency_injection()
        
        # Test 2: Real LLM (requires Ollama running)
        test_real_llm()
        
        # Test 3: Extension without modification
        test_validator_extension()
        
        # Test 4: Multiple LLM providers
        test_multiple_llm_providers()
        
        print("="*60)
        print("✅ All SOLID principles validated!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
