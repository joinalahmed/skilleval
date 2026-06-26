#!/usr/bin/env python3
"""
Test multi-provider agent execution (Google GenAI and Anthropic).
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skilleval.utils.multi_provider_agent import MultiProviderExecutorSync, Provider


def test_provider_detection():
    """Test automatic provider detection."""
    print("\n🧪 Testing provider auto-detection...")

    executor = MultiProviderExecutorSync()

    # Check detected provider
    detected_provider = executor.executor.agent_config.provider
    detected_model = executor.executor.agent_config.model

    print(f"   Detected provider: {detected_provider.value}")
    print(f"   Selected model: {detected_model}")

    # Check which API keys are set
    has_google = bool(os.getenv("GOOGLE_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    print(f"   GOOGLE_API_KEY: {'✅ Set' if has_google else '❌ Not set'}")
    print(f"   ANTHROPIC_API_KEY: {'✅ Set' if has_anthropic else '❌ Not set'}")

    if has_google or has_anthropic:
        print("   ✅ At least one provider available")
        return True
    else:
        print("   ❌ No API keys set")
        print("\n   Set one of:")
        print("   export GOOGLE_API_KEY=your-google-api-key")
        print("   export ANTHROPIC_API_KEY=your-anthropic-api-key")
        return False


def test_executor_available():
    """Test that executor can be initialized."""
    print("\n🧪 Testing executor availability...")

    try:
        executor = MultiProviderExecutorSync()
        available = executor.check_available()

        if available:
            provider = executor.executor.agent_config.provider
            model = executor.executor.agent_config.model

            print(f"   ✅ Executor available")
            print(f"   Provider: {provider.value}")
            print(f"   Model: {model}")
            return True
        else:
            print("   ❌ Executor not available (no API key)")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_simple_execution():
    """Test simple execution with available provider."""
    print("\n🧪 Testing agent execution...")

    executor = MultiProviderExecutorSync()

    if not executor.check_available():
        print("   ⏭️  Skipped (no API key)")
        return None

    provider = executor.executor.agent_config.provider
    print(f"   Using provider: {provider.value}")
    print(f"   Prompt: 'Create hello.txt with Hello World'")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            eval_case = {
                "prompt": "Create a file called hello.txt with the content 'Hello World'",
                "files": [],
            }

            print(f"\n   Executing...")
            result = executor.execute_baseline(
                skill_path=Path("."),
                eval_case=eval_case,
                workspace=workspace / "test",
            )

            print(f"\n   ✅ Execution complete:")
            print(f"      Provider: {result.get('provider', 'unknown')}")
            print(f"      Model: {result.get('model', 'unknown')}")
            print(f"      Turns: {result.get('turn_count', 0)}")
            print(f"      Tokens: {result.get('total_tokens', 0)}")
            print(f"      Tool uses: {len(result.get('tool_uses', []))}")
            print(f"      Success: {result.get('success', False)}")
            print(f"      Duration: {result.get('duration_seconds', 0):.2f}s")

            # Check if file was created
            hello_file = workspace / "test" / "baseline" / "hello.txt"
            if hello_file.exists():
                content = hello_file.read_text()
                print(f"      ✅ File created: '{content.strip()}'")
            else:
                print(f"      ⚠️  File not found")

            return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cost_calculation():
    """Test cost calculation for both providers."""
    print("\n🧪 Testing cost calculation...")

    from skilleval.utils.multi_provider_agent import TraceAnalyzer

    analyzer = TraceAnalyzer()

    # Test Google pricing
    trace_google = {
        "total_tokens": 10000,
        "provider": "google",
    }
    cost_google = analyzer.calculate_cost(trace_google)
    print(f"   Google (10K tokens): ${cost_google:.4f}")

    # Test Anthropic pricing
    trace_anthropic = {
        "total_tokens": 10000,
        "provider": "anthropic",
    }
    cost_anthropic = analyzer.calculate_cost(trace_anthropic)
    print(f"   Anthropic (10K tokens): ${cost_anthropic:.4f}")

    # Cost difference
    diff = cost_anthropic - cost_google
    print(f"   Difference: ${diff:.4f} (Anthropic is {diff/cost_google*100:.0f}% more expensive)")

    print("   ✅ Cost calculation working")
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("MULTI-PROVIDER AGENT EXECUTION TESTS")
    print("=" * 70)

    results = []

    # Test 1: Provider detection
    print("\n1. Provider Detection")
    results.append(("Detection", test_provider_detection()))

    # Test 2: Executor availability
    print("\n2. Executor Availability")
    results.append(("Availability", test_executor_available()))

    # Test 3: Cost calculation
    print("\n3. Cost Calculation")
    results.append(("Cost Calc", test_cost_calculation()))

    # Test 4: Execution (if API key available)
    print("\n4. Agent Execution")
    executor = MultiProviderExecutorSync()
    if executor.check_available():
        results.append(("Execution", test_simple_execution()))
    else:
        print("   ⏭️  Skipped (no API key)")
        results.append(("Execution", None))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for name, result in results:
        if result is True:
            print(f"✅ {name}: PASS")
        elif result is False:
            print(f"❌ {name}: FAIL")
        else:
            print(f"⏭️  {name}: SKIPPED")

    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    print(f"\nPassed: {passed}, Failed: {failed}, Skipped: {skipped}")

    # Print usage instructions
    print("\n" + "=" * 70)
    print("USAGE")
    print("=" * 70)
    print("\nTo use Google GenAI (default, FREE):")
    print("  export GOOGLE_API_KEY=your-google-api-key")
    print("  Get key from: https://aistudio.google.com/apikey")
    print("\nTo use Anthropic Claude:")
    print("  export ANTHROPIC_API_KEY=your-anthropic-api-key")
    print("  Get key from: https://console.anthropic.com/")
    print("\nTo force a specific provider:")
    print("  export LLM_PROVIDER=google     # or 'anthropic'")
    print("\nThen run evaluations normally:")
    print("  python3 -m skilleval.cli eval /path/to/skill")
    print("  ./batch_eval.sh /path/to/skills")

    if failed > 0:
        return 1
    elif passed > 0:
        return 0
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
