"""
Example of using LLM-as-Judge for evaluation
"""

from agent_eval import AgentEvaluator, EvaluationConfig
from agent_eval.models import (
    AgentExecution,
    ExpectedResult,
    LLMConfig,
    StorageConfig,
    StorageType,
)


def example_llm_judge():
    """Example using LLM-as-Judge for evaluation"""

    # Configure with LLM
    config = EvaluationConfig(
        llm_config=LLMConfig(
            api_key="your-api-key-here",  # Replace with actual API key
            base_url="https://api.openai.com/v1",  # Optional: for custom endpoints
            model="gpt-4",
            temperature=0.0,
            max_tokens=500,
            timeout=30.0
        ),
        use_code_scorer=True,
        use_llm_scorer=True,  # Enable LLM-as-Judge
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="llm_judge_evaluations.json"
        )
    )

    evaluator = AgentEvaluator(config)

    # Create execution
    query = "Explain the theory of relativity in simple terms"

    execution = AgentExecution(
        execution_id="relativity-001",
        query=query,
        final_output="""
The theory of relativity, developed by Albert Einstein, consists of two parts:

1. Special Relativity (1905): Shows that space and time are connected and that 
   the speed of light is constant for all observers. It leads to famous effects 
   like time dilation (moving clocks tick slower) and length contraction.

2. General Relativity (1915): Describes gravity not as a force, but as the 
   curvature of spacetime caused by mass and energy. Massive objects like stars 
   and planets warp the fabric of spacetime, and this curvature affects how 
   other objects move.

Think of it like a bowling ball on a trampoline - the ball creates a dip, 
and smaller balls roll toward it not because of a "force," but because of 
the shape of the surface.
        """.strip(),
        success=True,
        total_duration_ms=2500.0
    )

    expected = ExpectedResult(
        expected_output="""
Einstein's theory of relativity explains that:
- Space and time are interconnected
- The speed of light is constant
- Gravity is the curvature of spacetime
- Massive objects warp spacetime
        """.strip()
    )

    # Evaluate with LLM judge
    result = evaluator.evaluate(execution, expected)

    print("=" * 60)
    print("LLM-as-Judge Evaluation Results")
    print("=" * 60)
    print(f"Query: {query}")
    print(f"\nOverall Score: {result.overall_score:.2f}")
    print("\nMetric Scores:")
    for metric in result.metric_scores:
        print(f"  {metric.metric_name}: {metric.score:.2f}")

    print("\nScorer Results:")
    for scorer_result in result.scorer_results:
        print(f"  Scorer: {scorer_result.get('scorer_name', 'Unknown')}")
        print(f"  Score: {scorer_result.get('score', 0):.2f}")
        print(f"  Passed: {scorer_result.get('passed', False)}")
        details = scorer_result.get('details', {})
        if 'reasoning' in details:
            print(f"  Reasoning: {details['reasoning']}")

    return result


def example_auto_expected_generation():
    """Example of automatically generating expected results with LLM"""

    config = EvaluationConfig(
        llm_config=LLMConfig(
            api_key="your-api-key-here",
            model="gpt-4",
            temperature=0.0
        ),
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="auto_expected_evaluations.json"
        )
    )

    evaluator = AgentEvaluator(config)

    # Generate expected result automatically
    query = "What are the main causes of climate change?"

    print("=" * 60)
    print("Auto-Generated Expected Result")
    print("=" * 60)
    print(f"Query: {query}")

    try:
        expected = evaluator.generate_expected_result(
            query=query,
            context="Focus on human activities and natural factors",
            available_tools=["web_search", "scientific_database", "calculator"]
        )

        print(f"\nExpected Output:\n{expected.expected_output}")
        print(f"\nExpected Steps: {expected.expected_steps}")
        print(f"Expected Tool Calls: {expected.expected_tool_calls}")
        print(f"Expected Tool Count: {expected.expected_tool_count}")
        print(f"Expected Duration: {expected.expected_duration_ms}ms")

        # Now simulate an agent execution
        with evaluator.create_recording_context(query):
            evaluator.record_step("Analyze query about climate change")
            evaluator.record_tool_call(
                "web_search",
                {"query": "main causes of climate change"},
                duration_ms=800.0
            )
            evaluator.record_step("Synthesize information")

        # Evaluate with auto-generated expected result
        result = evaluator.evaluate(expected=expected)

        print(f"\nEvaluation Score: {result.overall_score:.2f}")

        return result

    except Exception as e:
        print(f"Error: {e}")
        print("Note: This example requires a valid LLM API key")
        return None


def example_hybrid_scoring():
    """Example of hybrid scoring (code-based + LLM)"""

    config = EvaluationConfig(
        llm_config=LLMConfig(
            api_key="your-api-key-here",
            model="gpt-4",
            temperature=0.0
        ),
        use_code_scorer=True,
        use_llm_scorer=True,
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="hybrid_evaluations.json"
        )
    )

    evaluator = AgentEvaluator(config)

    # Create execution with specific tool sequence
    execution = AgentExecution(
        execution_id="hybrid-001",
        query="Calculate the area of a circle with radius 5",
        final_output="The area of a circle with radius 5 is 78.54 square units.",
        success=True,
        total_duration_ms=300.0
    )

    expected = ExpectedResult(
        expected_output="The area is 78.54 square units.",
        expected_tool_calls=["calculator", "geometry_formula"],
        expected_tool_count=2
    )

    result = evaluator.evaluate(execution, expected)

    print("=" * 60)
    print("Hybrid Scoring Results")
    print("=" * 60)
    print(f"Overall Score: {result.overall_score:.2f}")

    # Show both scorer results
    for scorer_result in result.scorer_results:
        print(f"\n{scorer_result.get('scorer_name', 'Unknown')}:")
        print(f"  Score: {scorer_result.get('score', 0):.2f}")
        details = scorer_result.get('details', {})
        if 'code_scorer' in details and 'llm_scorer' in details:
            print(f"  Code Scorer: {details['code_scorer']['score']:.2f}")
            print(f"  LLM Scorer: {details['llm_scorer']['score']:.2f}")
            print(f"  Weights: Code={details['weights']['code']}, LLM={details['weights']['llm']}")

    return result


if __name__ == "__main__":
    print("Running LLM-as-Judge examples...\n")

    # Note: These examples require a valid LLM API key
    # They will fail gracefully if no API key is provided

    try:
        example_llm_judge()
    except Exception as e:
        print(f"LLM Judge example skipped: {e}")

    print("\n")

    try:
        example_auto_expected_generation()
    except Exception as e:
        print(f"Auto expected generation example skipped: {e}")

    print("\n")

    try:
        example_hybrid_scoring()
    except Exception as e:
        print(f"Hybrid scoring example skipped: {e}")

    print("\nAll examples completed!")
