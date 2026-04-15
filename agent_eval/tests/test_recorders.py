"""
Tests for recorders module
"""

import pytest

from agent_eval.recorders import ExecutionRecorder, ExecutionRecord, create_recorder
from agent_eval.models import AgentExecution


def test_execution_record_creation():
    """Test creating an execution record"""
    record = ExecutionRecord(query="Test query")

    assert record.query == "Test query"
    assert record.execution_id is not None
    assert len(record.steps_detail) == 0


def test_execution_record_add_step():
    """Test adding steps to record"""
    record = ExecutionRecord(query="Test query")
    record.start()

    step = record.add_step("Step 1", {"meta": "data"})

    assert len(record.steps_detail) == 1
    assert step.step == 1
    assert step.description == "Step 1"


def test_execution_record_add_tool_call():
    """Test adding tool calls to record"""
    record = ExecutionRecord(query="Test query")
    record.start()
    record.add_step("Step 1")

    tool_call = record.add_tool_call(
        tool_name="test_tool",
        arguments={"arg": "value"},
        result="result",
        duration_ms=100.0
    )

    assert tool_call.name == "test_tool"
    assert tool_call.input == {"arg": "value"}
    assert tool_call.time == 100.0


def test_execution_record_to_agent_execution():
    """Test converting record to AgentExecution"""
    record = ExecutionRecord(query="Test query")
    record.start()
    record.add_step("Step 1")
    record.add_tool_call("tool1")
    record.set_output("Final output")
    record.end(success=True)

    execution = record.to_agent_execution()

    assert isinstance(execution, AgentExecution)
    assert execution.query == "Test query"
    assert execution.final_output == "Final output"
    assert execution.success is True
    assert execution.tool_call_count == 1


def test_recorder_start_end_recording():
    """Test starting and ending recording"""
    recorder = ExecutionRecorder()

    recorder.start_recording("Test query")
    recorder.record_step("Step 1")
    execution = recorder.end_recording(success=True, final_output="Done")

    assert isinstance(execution, AgentExecution)
    assert execution.query == "Test query"
    assert execution.success is True


def test_recorder_no_active_session():
    """Test error when no active session"""
    recorder = ExecutionRecorder()

    with pytest.raises(RuntimeError):
        recorder.record_step("Step 1")


def test_recorder_get_history():
    """Test getting execution history"""
    recorder = ExecutionRecorder()

    recorder.start_recording("Query 1")
    recorder.end_recording(success=True)

    recorder.start_recording("Query 2")
    recorder.end_recording(success=True)

    history = recorder.get_execution_history()
    assert len(history) == 2


def test_recorder_clear_history():
    """Test clearing execution history"""
    recorder = ExecutionRecorder()

    recorder.start_recording("Query")
    recorder.end_recording(success=True)

    assert len(recorder.get_execution_history()) == 1

    recorder.clear_history()

    assert len(recorder.get_execution_history()) == 0


def test_create_recorder():
    """Test create_recorder factory function"""
    recorder = create_recorder(auto_save=False)

    assert isinstance(recorder, ExecutionRecorder)
    assert recorder.auto_save is False


def test_recorder_context_manager():
    """Test recorder as context manager"""
    recorder = ExecutionRecorder()

    with recorder.record("Test query") as record:
        record.add_step("Step 1")
        record.set_output("Result")

    history = recorder.get_execution_history()
    assert len(history) == 1
    assert history[0].query == "Test query"


def test_recorder_context_manager_exception():
    """Test recorder context manager with exception"""
    recorder = ExecutionRecorder()

    with pytest.raises(ValueError):
        with recorder.record("Test query"):
            raise ValueError("Test error")

    history = recorder.get_execution_history()
    assert len(history) == 1
    assert history[0].success is False
    assert history[0].has_error is True
