"""
Simple demo of agent-eval library
This example demonstrates basic usage without requiring API keys
"""

from agent_eval import AgentEvaluator, EvaluationConfig, StorageConfig, StorageType
from agent_eval.models import AgentExecution, ExpectedResult


def demo_basic_evaluation():
    """Demo basic evaluation without LLM"""
    print("=" * 60)
    print("Demo 1: Basic Evaluation (Code-based only)")
    print("=" * 60)

    # Create evaluator with code-based scoring only
    config = EvaluationConfig(
        use_code_scorer=True,
        use_llm_scorer=False,
        auto_record=False
    )
    evaluator = AgentEvaluator(config)

    # Create a sample execution
    execution = AgentExecution(
        execution_id="demo-001",
        query="What is the capital of France?",
        final_output="The capital of France is Paris.",
        success=True,
        total_duration_ms=1200.0,
        steps=[
            {
                "step_number": 1,
                "description": "Analyze query",
                "tool_calls": []
            },
            {
                "step_number": 2,
                "description": "Retrieve information",
                "tool_calls": [
                    {"tool_name": "search_tool", "duration_ms": 500.0}
                ]
            }
        ]
    )

    # Define expected result
    expected = ExpectedResult(
        expected_output="Paris",
        expected_steps=["Analyze query", "Retrieve information"],
        expected_tool_count=1,
        expected_duration_ms=1000.0
    )

    # Evaluate
    result = evaluator.evaluate(execution, expected, save_result=False)

    # Print results
    print(f"Query: {result.query}")
    print(f"Overall Score: {result.overall_score:.2%}")
    print("\nMetric Scores:")
    for metric in result.metric_scores:
        print(f"  - {metric.metric_name}: {metric.score:.2%}")
        if metric.details:
            print(f"    Details: {metric.details}")
    print()


def demo_execution_recording():
    """Demo execution recording"""
    print("=" * 60)
    print("Demo 2: Execution Recording")
    print("=" * 60)

    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    # Record execution manually
    evaluator.start_recording("Calculate 15 * 23")
    evaluator.record_step("Parse mathematical expression")
    evaluator.record_tool_call("calculator", {"operation": "multiply", "a": 15, "b": 23})
    evaluator.record_step("Perform calculation")
    execution = evaluator.end_recording(
        success=True,
        final_output="345"
    )

    print(f"Recorded Execution ID: {execution.execution_id}")
    print(f"Query: {execution.query}")
    print(f"Steps: {len(execution.steps)}")
    print(f"Tool Calls: {execution.total_tool_calls}")
    print(f"Duration: {execution.total_duration_ms:.2f} ms")
    print(f"Success: {execution.success}")
    print()


def demo_context_manager():
    """Demo using context manager for recording"""
    print("=" * 60)
    print("Demo 3: Context Manager Recording")
    print("=" * 60)

    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    # Use context manager for automatic recording
    with evaluator.create_recording_context("Translate 'hello' to French") as record:
        evaluator.record_step("Detect source language")
        evaluator.record_step("Translate to target language")
        evaluator.record_tool_call("translator", {"text": "hello", "target": "french"})
        # Final output will be set automatically when exiting context

    history = evaluator.get_execution_history()
    if history:
        last_execution = history[-1]
        print(f"Execution ID: {last_execution.execution_id}")
        print(f"Query: {last_execution.query}")
        print(f"Steps: {len(last_execution.steps)}")
        print(f"Success: {last_execution.success}")
    print()


def demo_storage():
    """Demo saving to different storage formats"""
    print("=" * 60)
    print("Demo 4: Storage Options")
    print("=" * 60)

    import tempfile
    import os

    with tempfile.TemporaryDirectory() as temp_dir:
        # JSON Storage
        json_path = os.path.join(temp_dir, "evaluations.json")
        config = EvaluationConfig(
            storage_config=StorageConfig(
                storage_type=StorageType.JSON,
                file_path=json_path
            ),
            auto_record=False
        )
        evaluator = AgentEvaluator(config)

        execution = AgentExecution(
            execution_id="storage-demo",
            query="Test query",
            final_output="Test output",
            success=True
        )
        expected = ExpectedResult(expected_output="Test output")

        result = evaluator.evaluate(execution, expected, save_result=True)

        print(f"Saved evaluation to JSON: {json_path}")
        print(f"Evaluation ID: {result.evaluation_id}")

        # Retrieve from storage
        stored = evaluator.get_stored_evaluations()
        print(f"Retrieved {len(stored)} evaluation(s) from storage")
    print()


def demo_batch_evaluation():
    """Demo batch evaluation"""
    print("=" * 60)
    print("Demo 5: Batch Evaluation")
    print("=" * 60)

    config = EvaluationConfig(
        use_code_scorer=True,
        use_llm_scorer=False,
        auto_record=False
    )
    evaluator = AgentEvaluator(config)

    # Create multiple executions
    executions = [
        AgentExecution(
            execution_id=f"batch-{i}",
            query=f"Query {i}",
            final_output=f"Output {i}",
            success=True,
            total_duration_ms=1000.0 + i * 100
        )
        for i in range(5)
    ]

    expected_results = [
        ExpectedResult(
            expected_output=f"Output {i}",
            expected_duration_ms=1000.0
        )
        for i in range(5)
    ]

    # Batch evaluate
    results = evaluator.batch_evaluate(
        executions,
        expected_results,
        save_results=False
    )

    # Get summary
    summary = evaluator.get_evaluation_summary(results)

    print(f"Total Evaluations: {summary['total_evaluations']}")
    print(f"Average Overall Score: {summary['overall_score']['average']:.2%}")
    print(f"Score Range: {summary['overall_score']['min']:.2%} - {summary['overall_score']['max']:.2%}")
    print("\nMetric Averages:")
    for metric_name, avg_data in summary['metric_averages'].items():
        print(f"  - {metric_name}: {avg_data['average']:.2%}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Agent Eval Library - Simple Demo")
    print("=" * 60 + "\n")

    demo_basic_evaluation()
    demo_execution_recording()
    demo_context_manager()
    demo_storage()
    demo_batch_evaluation()

    print("=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)
