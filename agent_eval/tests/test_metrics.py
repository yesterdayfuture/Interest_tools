"""
Tests for metrics module
"""

import pytest

from agent_eval.metrics import (
    Correctness,
    LatencyRatio,
    MetricCalculator,
    SolveRate,
    StepRatio,
    ToolCallRatio,
)
from agent_eval.models import AgentExecution, ExpectedResult, StepDetail, ToolCallDetail


def test_correctness_exact_match():
    """Test correctness with exact match"""
    execution = AgentExecution(
        execution_id="test-001",
        query="What is 2+2?",
        final_output="4",
        success=True
    )
    expected = ExpectedResult(expected_output="4")

    metric = Correctness()
    result = metric.calculate(execution, expected)

    assert result.score == 1.0
    assert result.metric_name == "Correctness"


def test_correctness_partial_match():
    """Test correctness with partial match using n-gram similarity"""
    execution = AgentExecution(
        execution_id="test-002",
        query="What is the capital of France?",
        final_output="The capital of France is Paris, a beautiful city.",
        success=True
    )
    # Use a more semantically similar expected output for n-gram matching
    expected = ExpectedResult(
        expected_output="The capital city of France is Paris, which is beautiful."
    )

    metric = Correctness()
    result = metric.calculate(execution, expected)

    # N-gram similarity should detect high semantic similarity
    assert 0.4 <= result.score <= 1.0
    assert result.details['match_type'] in ['high_similarity', 'partial', 'exact']
    # Verify n-gram details are included
    assert 'ngram_details' in result.details
    assert '1-gram' in result.details['ngram_details']['ngram_scores']


def test_correctness_no_expected():
    """Test correctness when no expected output provided"""
    execution = AgentExecution(
        execution_id="test-003",
        query="What is 2+2?",
        final_output="4",
        success=True
    )

    metric = Correctness()
    result = metric.calculate(execution, None)

    assert result.score == 0.5


def test_step_ratio_optimal():
    """Test step ratio with optimal steps"""
    execution = AgentExecution(
        execution_id="test-004",
        query="Test query",
        steps_detail=[
            StepDetail(step=1, description="Step 1"),
            StepDetail(step=2, description="Step 2"),
            StepDetail(step=3, description="Step 3")
        ],
        step_count=3
    )
    expected = ExpectedResult(expected_steps=["step1", "step2", "step3"])

    metric = StepRatio()
    result = metric.calculate(execution, expected)

    assert result.score == 1.0


def test_step_ratio_too_many_steps():
    """Test step ratio with too many steps"""
    execution = AgentExecution(
        execution_id="test-005",
        query="Test query",
        steps_detail=[StepDetail(step=i, description=f"Step {i}") for i in range(1, 7)],
        step_count=6
    )
    expected = ExpectedResult(expected_steps=["step1", "step2", "step3"])

    metric = StepRatio()
    result = metric.calculate(execution, expected)

    assert result.score < 1.0


def test_tool_call_ratio_optimal():
    """Test tool call ratio with optimal count"""
    execution = AgentExecution(
        execution_id="test-006",
        query="Test query",
        tool_calls_detail=[
            ToolCallDetail(name="tool1"),
            ToolCallDetail(name="tool2")
        ],
        tool_call_count=2
    )
    expected = ExpectedResult(expected_tool_count=2)

    metric = ToolCallRatio()
    result = metric.calculate(execution, expected)

    assert result.score == 1.0


def test_solve_rate_success():
    """Test solve rate with successful execution"""
    execution = AgentExecution(
        execution_id="test-007",
        query="Test query",
        final_output="Success result",
        success=True
    )
    expected = ExpectedResult(expected_output="Success result")

    metric = SolveRate()
    result = metric.calculate(execution, expected)

    assert result.score == 1.0


def test_solve_rate_failure():
    """Test solve rate with failed execution"""
    execution = AgentExecution(
        execution_id="test-008",
        query="Test query",
        success=False,
        has_error=True,
        error_message="Something went wrong"
    )

    metric = SolveRate()
    result = metric.calculate(execution, None)

    assert result.score == 0.0


def test_latency_ratio_optimal():
    """Test latency ratio with optimal duration"""
    execution = AgentExecution(
        execution_id="test-009",
        query="Test query",
        total_duration_ms=1000.0
    )
    expected = ExpectedResult(expected_duration_ms=1000.0)

    metric = LatencyRatio()
    result = metric.calculate(execution, expected)

    assert result.score == 1.0


def test_latency_ratio_slow():
    """Test latency ratio with slow execution"""
    execution = AgentExecution(
        execution_id="test-010",
        query="Test query",
        total_duration_ms=3000.0
    )
    expected = ExpectedResult(expected_duration_ms=1000.0)

    metric = LatencyRatio()
    result = metric.calculate(execution, expected)

    assert result.score < 1.0


def test_metric_calculator_all_metrics():
    """Test metric calculator with all metrics enabled"""
    execution = AgentExecution(
        execution_id="test-011",
        query="Test query",
        final_output="Test output",
        success=True,
        total_duration_ms=1000.0,
        steps_detail=[StepDetail(step=1, description="Step 1")],
        step_count=1
    )
    expected = ExpectedResult(
        expected_output="Test output",
        expected_steps=["step1"],
        expected_duration_ms=1000.0
    )

    calculator = MetricCalculator()
    scores, overall = calculator.calculate_all(execution, expected)

    assert len(scores) == 5  # All 5 metrics
    assert 0.0 <= overall <= 1.0


def test_metric_calculator_custom_weights():
    """Test metric calculator with custom weights"""
    execution = AgentExecution(
        execution_id="test-012",
        query="Test query",
        final_output="Test",
        success=True,
        steps_detail=[StepDetail(step=1, description="Step 1")],
        step_count=1
    )
    expected = ExpectedResult(expected_output="Test")

    # Create calculator with custom weights
    calculator = MetricCalculator(weights={"Correctness": 0.5})

    scores, overall = calculator.calculate_all(execution, expected)

    correctness_score = next(s for s in scores if s.metric_name == "Correctness")
    assert correctness_score.weight == 0.5
