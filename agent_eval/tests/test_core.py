"""
Tests for core module
"""

import pytest

from agent_eval.core import AgentEvaluator, create_evaluator, quick_evaluate
from agent_eval.models import (
    AgentExecution,
    EvaluationConfig,
    ExpectedResult,
    StorageConfig,
    StorageType,
)


def test_agent_evaluator_creation():
    """Test creating an agent evaluator"""
    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    assert evaluator.config is not None
    assert evaluator.recorder is not None


def test_agent_evaluator_evaluate():
    """Test evaluating an execution"""
    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    execution = AgentExecution(
        execution_id="test-001",
        query="What is 2+2?",
        final_output="4",
        success=True
    )

    expected = ExpectedResult(expected_output="4")

    result = evaluator.evaluate(execution, expected, save_result=False)

    assert result is not None
    assert result.execution_id == "test-001"
    assert 0.0 <= result.overall_score <= 1.0
    assert len(result.metric_scores) > 0


def test_agent_evaluator_batch_evaluate():
    """Test batch evaluation"""
    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    executions = [
        AgentExecution(
            execution_id=f"test-{i}",
            query=f"Query {i}",
            final_output=f"Output {i}",
            success=True
        )
        for i in range(3)
    ]

    expected_results = [
        ExpectedResult(expected_output=f"Output {i}")
        for i in range(3)
    ]

    results = evaluator.batch_evaluate(executions, expected_results, save_results=False)

    assert len(results) == 3
    for result in results:
        assert 0.0 <= result.overall_score <= 1.0


def test_agent_evaluator_get_evaluation_summary():
    """Test getting evaluation summary"""
    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    executions = [
        AgentExecution(
            execution_id=f"test-{i}",
            query=f"Query {i}",
            final_output=f"Output {i}",
            success=True
        )
        for i in range(3)
    ]

    expected_results = [
        ExpectedResult(expected_output=f"Output {i}")
        for i in range(3)
    ]

    results = evaluator.batch_evaluate(executions, expected_results, save_results=False)
    summary = evaluator.get_evaluation_summary(results)

    assert summary["total_evaluations"] == 3
    assert "overall_score" in summary
    assert "average" in summary["overall_score"]


def test_create_evaluator():
    """Test create_evaluator convenience function"""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "evaluations.json")
        evaluator = create_evaluator(storage_type="json", file_path=file_path)

        assert isinstance(evaluator, AgentEvaluator)


def test_quick_evaluate():
    """Test quick_evaluate convenience function"""
    execution = AgentExecution(
        execution_id="test-001",
        query="What is 2+2?",
        final_output="4",
        success=True
    )

    expected = ExpectedResult(expected_output="4")

    result = quick_evaluate(execution, expected)

    assert result is not None
    assert 0.0 <= result.overall_score <= 1.0


def test_agent_evaluator_recording():
    """Test recording with evaluator"""
    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    evaluator.start_recording("Test query")
    evaluator.record_step("Step 1")
    evaluator.record_tool_call("tool1", {"arg": "value"})
    execution = evaluator.end_recording(success=True, final_output="Done")

    assert execution.query == "Test query"
    assert execution.success is True
    assert execution.tool_call_count == 1


def test_agent_evaluator_context_manager():
    """Test using evaluator with context manager"""
    config = EvaluationConfig(auto_record=False)
    evaluator = AgentEvaluator(config)

    with evaluator.create_recording_context("Test query"):
        evaluator.record_step("Step 1")

    history = evaluator.get_execution_history()
    assert len(history) == 1
    assert history[0].query == "Test query"


def test_agent_evaluator_metrics_weights():
    """Test custom metric weights"""
    config = EvaluationConfig(
        auto_record=False,
        correctness_weight=0.5,
        solve_rate_weight=0.5,
        enable_step_ratio=False,
        enable_tool_call_ratio=False,
        enable_latency_ratio=False
    )
    evaluator = AgentEvaluator(config)

    execution = AgentExecution(
        execution_id="test-001",
        query="Test",
        final_output="Correct",
        success=True
    )

    expected = ExpectedResult(expected_output="Correct")
    result = evaluator.evaluate(execution, expected, save_result=False)

    # Should only have 2 metrics enabled
    enabled_metrics = [m.metric_name for m in result.metric_scores]
    assert "Correctness" in enabled_metrics
    assert "SolveRate" in enabled_metrics
    assert "StepRatio" not in enabled_metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
