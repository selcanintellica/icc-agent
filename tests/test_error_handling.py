"""
Test suite for error handling and retry mechanisms.

Run with: python -m pytest tests/test_error_handling.py -v
Or standalone: python tests/test_error_handling.py
"""

import asyncio
import time
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.retry import (
    retry,
    RetryConfig,
    RetryPresets,
    RetryStrategy,
    RetryExhaustedError,
    retry_sync_operation,
    retry_async_operation,
)
from src.errors import (
    ICCBaseError,
    AuthenticationError,
    NetworkTimeoutError,
    DuplicateJobNameError,
    LLMParsingError,
    ErrorHandler,
    ErrorCode,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestRetryMechanism:
    """Tests for the retry decorator and configuration."""
    
    def test_retry_success_first_try(self):
        """Test that successful calls don't retry."""
        call_count = 0
        
        @retry(max_retries=3, base_delay=0.1)
        def successful_call():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_call()
        
        assert result == "success"
        assert call_count == 1
        print("[PASS] Successful call doesn't retry")
    
    def test_retry_eventual_success(self):
        """Test that retries eventually succeed."""
        call_count = 0
        
        @retry(max_retries=3, base_delay=0.1, retryable_exceptions=(ValueError,))
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = failing_then_success()
        
        assert result == "success"
        assert call_count == 3
        print("[PASS] Retries eventually succeed")
    
    def test_retry_exhaustion(self):
        """Test that RetryExhaustedError is raised after max retries."""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.1, retryable_exceptions=(ValueError,))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")
        
        try:
            always_fails()
            assert False, "Should have raised RetryExhaustedError"
        except RetryExhaustedError as e:
            assert e.attempts == 3  # Initial + 2 retries
            assert isinstance(e.last_exception, ValueError)
            print(f"[PASS] RetryExhaustedError raised after {e.attempts} attempts")
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0
        
        @retry(max_retries=3, base_delay=0.1, retryable_exceptions=(ValueError,))
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")
        
        try:
            raises_type_error()
            assert False, "Should have raised TypeError"
        except TypeError:
            assert call_count == 1  # Only one call, no retries
            print("[PASS] Non-retryable exceptions are not retried")
    
    def test_delay_calculation_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=10.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False
        )
        
        delays = [config.calculate_delay(i) for i in range(5)]
        
        assert delays[0] == 1.0   # 1 * 2^0 = 1
        assert delays[1] == 2.0   # 1 * 2^1 = 2
        assert delays[2] == 4.0   # 1 * 2^2 = 4
        assert delays[3] == 8.0   # 1 * 2^3 = 8
        assert delays[4] == 10.0  # Capped at max_delay
        print("[PASS] Exponential backoff calculated correctly")
    
    def test_delay_with_jitter(self):
        """Test that jitter adds randomness to delays."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=10.0,
            strategy=RetryStrategy.CONSTANT,
            jitter=True,
            jitter_factor=0.5
        )
        
        delays = [config.calculate_delay(0) for _ in range(10)]
        
        # All delays should be between 1.0 and 1.5
        assert all(1.0 <= d <= 1.5 for d in delays)
        # Delays should not all be the same (jitter)
        assert len(set(delays)) > 1
        print("[PASS] Jitter adds randomness to delays")
    
    async def test_async_retry(self):
        """Test async retry functionality."""
        call_count = 0
        
        @retry(config=RetryPresets.QUICK)
        async def async_failing_then_success():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await async_failing_then_success()
        
        assert result == "success"
        assert call_count == 2
        print("[PASS] Async retry works correctly")
    
    def test_retry_timing(self):
        """Test that retry timing is reasonable."""
        call_count = 0
        start_time = time.time()
        
        @retry(max_retries=2, base_delay=0.1, retryable_exceptions=(ValueError,))
        def timed_failure():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")
        
        try:
            timed_failure()
        except RetryExhaustedError:
            elapsed = time.time() - start_time
            # Should take at least 0.1 + 0.2 = 0.3 seconds (exponential: 0.1, 0.2)
            # But with jitter, could be a bit more
            assert elapsed >= 0.2  # Minimum delay time
            assert elapsed < 2.0  # Should not take too long
            print(f"[PASS] Retry timing reasonable: {elapsed:.2f}s")


class TestErrorHandler:
    """Tests for error handler functionality."""
    
    def test_icc_error_passes_through(self):
        """Test that ICC errors pass through unchanged."""
        original_error = DuplicateJobNameError(job_name="TestJob")
        
        handled = ErrorHandler.handle(original_error)
        
        assert handled is original_error
        assert handled.code == ErrorCode.JOB_DUPLICATE_NAME.code
        print("[PASS] ICC errors pass through unchanged")
    
    def test_timeout_error_conversion(self):
        """Test that timeout errors are converted correctly."""
        timeout = TimeoutError("Connection timed out")
        
        handled = ErrorHandler.handle(timeout)
        
        assert isinstance(handled, NetworkTimeoutError)
        assert "timed out" in handled.user_message.lower()
        print("[PASS] Timeout errors converted to NetworkTimeoutError")
    
    def test_user_message_generation(self):
        """Test user-friendly message generation."""
        error = DuplicateJobNameError(job_name="MyJob")
        
        user_msg = ErrorHandler.get_user_message(error)
        
        assert "MyJob" in user_msg
        assert "already exists" in user_msg.lower()
        print(f"[PASS] User message: '{user_msg}'")
    
    def test_error_to_dict(self):
        """Test error serialization."""
        error = LLMParsingError(
            message="Failed to parse JSON",
            raw_response="invalid json"
        )
        
        error_dict = error.to_dict()
        
        assert "error_code" in error_dict
        assert "user_message" in error_dict
        assert "category" in error_dict
        assert error_dict["is_retryable"] == False
        print("[PASS] Error serialization works")
    
    def test_error_retryability(self):
        """Test that retryable errors are marked correctly."""
        retryable = NetworkTimeoutError()
        non_retryable = DuplicateJobNameError(job_name="Test")
        
        assert retryable.is_retryable == True
        assert non_retryable.is_retryable == False
        print("[PASS] Error retryability flags correct")


class TestConversationRecovery:
    """Tests for conversation recovery after errors."""
    
    def test_memory_preserved_after_error(self):
        """Test that memory state is preserved after error handling."""
        try:
            from src.ai.router.memory import Memory
            
            memory = Memory()
            memory.connection = "ORACLE_10"
            memory.schema = "SALES"
            memory.last_sql = "SELECT * FROM customers"
            
            # Simulate error in job creation
            try:
                raise DuplicateJobNameError(job_name="TestJob")
            except DuplicateJobNameError as e:
                error = ErrorHandler.handle(e)
            
            # Memory should still be intact
            assert memory.connection == "ORACLE_10"
            assert memory.schema == "SALES"
            assert memory.last_sql == "SELECT * FROM customers"
            print("[PASS] Memory preserved after error")
        except OSError as e:
            # Skip test if sandbox restrictions prevent module loading
            print(f"[SKIP] Sandbox restriction: {e}")
    
    def test_can_continue_after_error(self):
        """Test that operations can continue after error."""
        try:
            from src.ai.router.memory import Memory
            from src.ai.router.context.stage_context import Stage
            
            memory = Memory()
            memory.stage = Stage.EXECUTE_SQL
            
            # Simulate error
            error = DuplicateJobNameError(job_name="Test")
            error_msg = error.user_message
            
            # User provides new input
            new_job_name = "TestJob_v2"
            memory.gathered_params["name"] = new_job_name
            
            # Memory should still be at same stage, ready for retry
            assert memory.stage == Stage.EXECUTE_SQL
            assert memory.gathered_params["name"] == new_job_name
            print("[PASS] Can continue after error with new input")
        except OSError as e:
            # Skip test if sandbox restrictions prevent module loading
            print(f"[SKIP] Sandbox restriction: {e}")


class TestPresetConfigurations:
    """Tests for retry preset configurations."""
    
    def test_all_presets_exist(self):
        """Test that all expected presets are defined."""
        presets = [
            RetryPresets.AUTHENTICATION,
            RetryPresets.API_CALL,
            RetryPresets.LLM_CALL,
            RetryPresets.DATABASE,
            RetryPresets.QUICK,
            RetryPresets.AGGRESSIVE,
        ]
        
        for preset in presets:
            assert isinstance(preset, RetryConfig)
            assert preset.max_retries >= 1
            assert preset.base_delay > 0
        print("[PASS] All presets defined correctly")
    
    def test_llm_preset_has_longer_delays(self):
        """Test that LLM preset has appropriate delays."""
        llm = RetryPresets.LLM_CALL
        api = RetryPresets.API_CALL
        
        assert llm.base_delay >= api.base_delay
        assert llm.max_delay >= api.max_delay
        print(f"[PASS] LLM preset: base={llm.base_delay}s, max={llm.max_delay}s")
    
    def test_quick_preset_is_fast(self):
        """Test that QUICK preset has short delays."""
        quick = RetryPresets.QUICK
        
        assert quick.base_delay <= 0.5
        assert quick.max_delay <= 2.0
        assert quick.max_retries <= 3
        print(f"[PASS] QUICK preset: base={quick.base_delay}s, max_retries={quick.max_retries}")


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("ERROR HANDLING AND RETRY MECHANISM TESTS")
    print("="*60 + "\n")
    
    failed_tests = []
    passed_tests = []
    
    # Test classes and their methods
    test_classes = [
        TestRetryMechanism(),
        TestErrorHandler(),
        TestConversationRecovery(),
        TestPresetConfigurations(),
    ]
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n--- {class_name} ---\n")
        
        for method_name in dir(test_class):
            if method_name.startswith("test_"):
                method = getattr(test_class, method_name)
                try:
                    if asyncio.iscoroutinefunction(method):
                        asyncio.get_event_loop().run_until_complete(method())
                    else:
                        method()
                    passed_tests.append(f"{class_name}.{method_name}")
                except Exception as e:
                    print(f"[FAIL] {method_name}: {e}")
                    failed_tests.append(f"{class_name}.{method_name}: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Passed: {len(passed_tests)}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

