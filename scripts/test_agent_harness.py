#!/usr/bin/env python3
"""
Test agent-based harness execution.

This tests the new agent executor without running full evaluations.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skilleval.utils.agent_executor import AgentExecutorSync, TraceAnalyzer


def test_executor_available():
    """Test that executor can be initialized."""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set")
        print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        return False

    try:
        executor = AgentExecutorSync()
        available = executor.check_available()

        if available:
            print("✅ Agent executor initialized successfully")
            print(f"   Using API key: {os.getenv('ANTHROPIC_API_KEY')[:10]}...")
            return True
        else:
            print("❌ Agent executor not available")
            return False

    except Exception as e:
        print(f"❌ Error initializing executor: {e}")
        return False


def test_simple_execution():
    """Test simple agent execution."""

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⏭️  Skipping execution test (no API key)")
        return None

    print("\n🧪 Testing simple agent execution...")
    print("   Prompt: 'Create a file called hello.txt with Hello World'")

    try:
        executor = AgentExecutorSync()

        # Create temp workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)

            eval_case = {
                "prompt": "Create a file called hello.txt with the content 'Hello World'",
                "files": [],
            }

            # Run baseline (no skill)
            print("\n   Running baseline (no skill)...")
            result = executor.execute_baseline(
                skill_path=Path("."),  # Dummy path
                eval_case=eval_case,
                workspace=workspace / "test1",
            )

            print(f"   ✅ Baseline complete:")
            print(f"      Turns: {result.get('turn_count', 0)}")
            print(f"      Tokens: {result.get('total_tokens', 0)}")
            print(f"      Success: {result.get('success', False)}")
            print(f"      Duration: {result.get('duration_seconds', 0):.2f}s")

            # Check if file was created
            hello_file = workspace / "test1" / "baseline" / "hello.txt"
            if hello_file.exists():
                content = hello_file.read_text()
                print(f"      ✅ File created: {content.strip()}")
            else:
                print(f"      ⚠️  File not found at {hello_file}")

        return True

    except Exception as e:
        print(f"   ❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trace_analyzer():
    """Test trace analyzer."""

    print("\n🧪 Testing trace analyzer...")

    analyzer = TraceAnalyzer()

    # Test with no file
    result = analyzer.analyze_trace(Path("nonexistent.json"))
    assert result["total_tokens"] == 0
    print("   ✅ Handles missing files")

    # Test unbounded planning detection
    trace_data = {"turn_count": 60, "total_tokens": 10000}
    unbounded = analyzer.detect_unbounded_planning(trace_data)
    assert unbounded == True
    print("   ✅ Detects unbounded planning (60 turns)")

    # Test context rot detection
    trace_data = {"turn_count": 10, "total_tokens": 150000}
    context_rot = analyzer.detect_context_rot(trace_data)
    assert context_rot == True
    print("   ✅ Detects context overflow (150K tokens)")

    # Test cost calculation
    trace_data = {"total_tokens": 10000}
    cost = analyzer.calculate_cost(trace_data)
    assert cost > 0
    print(f"   ✅ Calculates cost: ${cost:.4f} for 10K tokens")

    return True


def main():
    """Run all tests."""

    print("=" * 70)
    print("AGENT-BASED HARNESS EXECUTION TESTS")
    print("=" * 70)

    results = []

    # Test 1: Executor available
    print("\n1. Testing executor initialization...")
    results.append(("Initialization", test_executor_available()))

    # Test 2: Trace analyzer
    print("\n2. Testing trace analyzer...")
    results.append(("Trace Analyzer", test_trace_analyzer()))

    # Test 3: Simple execution (requires API key)
    if os.getenv("ANTHROPIC_API_KEY"):
        print("\n3. Testing agent execution...")
        results.append(("Agent Execution", test_simple_execution()))
    else:
        print("\n3. Skipping agent execution (ANTHROPIC_API_KEY not set)")
        results.append(("Agent Execution", None))

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

    if failed > 0:
        print("\n❌ Some tests failed")
        return 1
    elif passed > 0:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n⚠️  All tests skipped (set ANTHROPIC_API_KEY to run)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
