"""
Basic usage example for agent-eval
"""

from agent_eval import AgentEvaluator, EvaluationConfig
from agent_eval.models import (
    AgentExecution,
    ExpectedResult,
    StorageConfig,
    StorageType,
)


def example_basic_evaluation():
    """Example of basic evaluation workflow"""

    # Create evaluator with JSON storage
    config = EvaluationConfig(
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="evaluations.json"
        )
    )
    evaluator = AgentEvaluator(config)

    # Simulate agent execution with recording
    query = "What is the capital of France?"

    with evaluator.create_recording_context(query):
        # Step 1: Analyze query
        evaluator.record_step("Analyze user query", {"intent": "factual_question"})

        # Step 2: Retrieve information (simulated tool call)
        evaluator.record_tool_call(
            tool_name="knowledge_base",
            arguments={"query": "capital of France"},
            result={"answer": "Paris"},
            duration_ms=150.0
        )

        # Step 3: Format response
        evaluator.record_step("Format response")

    # Define expected result
    expected = ExpectedResult(
        expected_output="The capital of France is Paris.",
        expected_steps=[
            "Analyze user query",
            "Retrieve information from knowledge base",
            "Format response"
        ],
        expected_tool_calls=["knowledge_base"],
        expected_tool_count=1,
        expected_duration_ms=500.0
    )

    # Evaluate
    result = evaluator.evaluate(expected=expected)

    # Print results
    print("=" * 50)
    print("Evaluation Results")
    print("=" * 50)
    print(f"Query: {result.query}")
    print(f"Overall Score: {result.overall_score:.2f}")
    print("\nMetric Scores:")
    for metric in result.metric_scores:
        print(f"  {metric.metric_name}: {metric.score:.2f} (weight: {metric.weight})")
        print(f"    Details: {metric.details}")

    return result


def example_manual_recording():
    """Example of manual recording without context manager"""

    evaluator = AgentEvaluator(EvaluationConfig(auto_record=False))

    # Start recording manually
    evaluator.start_recording("Calculate 15% of 200")

    # Record steps
    evaluator.record_step("Parse mathematical expression")
    evaluator.record_tool_call(
        tool_name="calculator",
        arguments={"operation": "percentage", "value": 200, "percentage": 15},
        result=30.0,
        duration_ms=50.0
    )
    evaluator.record_step("Format result")

    # End recording
    execution = evaluator.end_recording(
        success=True,
        final_output="15% of 200 is 30."
    )

    # Evaluate
    expected = ExpectedResult(
        expected_output="15% of 200 is 30.",
        expected_steps=["Parse expression", "Calculate", "Format"],
        expected_tool_calls=["calculator"],
        expected_tool_count=1
    )

    result = evaluator.evaluate(execution, expected)

    print("\n" + "=" * 50)
    print("Manual Recording Results")
    print("=" * 50)
    print(f"Overall Score: {result.overall_score:.2f}")

    return result


def example_quick_evaluation():
    """Example of quick evaluation without storage"""

    from agent_eval.core import quick_evaluate

    # Create execution manually
    execution = AgentExecution(
        execution_id="test-001",
        query="What is 2 + 2?",
        final_output="2 + 2 = 4",
        success=True,
        total_duration_ms=100.0
    )

    expected = ExpectedResult(
        expected_output="2 + 2 = 4",
        expected_steps=["Calculate"],
        expected_tool_count=0
    )

    # Quick evaluate
    result = quick_evaluate(execution, expected)

    print("\n" + "=" * 50)
    print("Quick Evaluation Results")
    print("=" * 50)
    print(f"Score: {result.overall_score:.2f}")

    return result


def example_with_different_storage():
    """Example using different storage backends"""

    # SQLite storage
    sqlite_config = EvaluationConfig(
        storage_config=StorageConfig(
            storage_type=StorageType.SQLITE,
            file_path="evaluations.db"
        )
    )

    evaluator = AgentEvaluator(sqlite_config)

    # Record and evaluate
    with evaluator.create_recording_context("Test query"):
        evaluator.record_step("Step 1")
        evaluator.record_tool_call("test_tool")

    result = evaluator.evaluate()

    print("\n" + "=" * 50)
    print("SQLite Storage Results")
    print("=" * 50)
    print(f"Score: {result.overall_score:.2f}")

    # Retrieve stored evaluations
    stored = evaluator.get_stored_evaluations(limit=10)
    print(f"Stored evaluations: {len(stored)}")

    return result


if __name__ == "__main__":
    print("Running basic usage examples...\n")

    # Run examples
    example_basic_evaluation()
    example_manual_recording()
    example_quick_evaluation()
    example_with_different_storage()

    print("\n" + "=" * 50)
    print("All examples completed!")
    print("=" * 50)
