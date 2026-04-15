"""
Tests for storages module
"""

import os
import tempfile

import pytest

from agent_eval.models import AgentExecution, EvaluationResult, StorageConfig, StorageType
from agent_eval.storages import JSONStorage, CSVStorage, SQLiteStorage, create_storage


def test_json_storage_save_and_get_execution():
    """Test saving and retrieving execution from JSON storage"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        config = StorageConfig(storage_type=StorageType.JSON, file_path=temp_path)
        storage = JSONStorage(config)

        execution = AgentExecution(
            execution_id="test-001",
            query="Test query",
            final_output="Test output",
            success=True
        )

        storage.save_execution(execution)
        retrieved = storage.get_execution("test-001")

        assert retrieved is not None
        assert retrieved.execution_id == "test-001"
        assert retrieved.query == "Test query"
    finally:
        os.unlink(temp_path)


def test_json_storage_save_and_get_evaluation():
    """Test saving and retrieving evaluation from JSON storage"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        config = StorageConfig(storage_type=StorageType.JSON, file_path=temp_path)
        storage = JSONStorage(config)

        execution = AgentExecution(
            execution_id="test-001",
            query="Test query",
            success=True
        )
        storage.save_execution(execution)

        evaluation = EvaluationResult(
            evaluation_id="eval-001",
            execution_id="test-001",
            query="Test query",
            overall_score=0.85,
            agent_execution=execution
        )

        storage.save_evaluation(evaluation)
        retrieved = storage.get_evaluation("eval-001")

        assert retrieved is not None
        assert retrieved.evaluation_id == "eval-001"
        assert retrieved.overall_score == 0.85
    finally:
        os.unlink(temp_path)


def test_json_storage_list_executions():
    """Test listing executions from JSON storage"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = f.name

    try:
        config = StorageConfig(storage_type=StorageType.JSON, file_path=temp_path)
        storage = JSONStorage(config)

        for i in range(3):
            execution = AgentExecution(
                execution_id=f"test-{i}",
                query=f"Query {i}",
                success=True
            )
            storage.save_execution(execution)

        executions = storage.list_executions(limit=10)

        assert len(executions) == 3
    finally:
        os.unlink(temp_path)


def test_csv_storage_save_and_get_execution():
    """Test saving and retrieving execution from CSV storage"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, "executions.csv")

        config = StorageConfig(storage_type=StorageType.CSV, file_path=temp_path)
        storage = CSVStorage(config)

        execution = AgentExecution(
            execution_id="test-001",
            query="Test query",
            final_output="Test output",
            success=True
        )

        storage.save_execution(execution)
        retrieved = storage.get_execution("test-001")

        assert retrieved is not None
        assert retrieved.execution_id == "test-001"


def test_sqlite_storage_save_and_get_execution():
    """Test saving and retrieving execution from SQLite storage"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, "test.db")

        config = StorageConfig(storage_type=StorageType.SQLITE, file_path=temp_path)
        storage = SQLiteStorage(config)

        execution = AgentExecution(
            execution_id="test-001",
            query="Test query",
            final_output="Test output",
            success=True
        )

        storage.save_execution(execution)
        retrieved = storage.get_execution("test-001")

        assert retrieved is not None
        assert retrieved.execution_id == "test-001"
        assert retrieved.query == "Test query"


def test_sqlite_storage_list_evaluations():
    """Test listing evaluations from SQLite storage"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, "test.db")

        config = StorageConfig(storage_type=StorageType.SQLITE, file_path=temp_path)
        storage = SQLiteStorage(config)

        execution = AgentExecution(
            execution_id="test-001",
            query="Test query",
            success=True
        )
        storage.save_execution(execution)

        for i in range(3):
            evaluation = EvaluationResult(
                evaluation_id=f"eval-{i}",
                execution_id="test-001",
                query="Test query",
                overall_score=0.8 + i * 0.05,
                agent_execution=execution
            )
            storage.save_evaluation(evaluation)

        evaluations = storage.list_evaluations(limit=10)

        assert len(evaluations) == 3


def test_create_storage_factory():
    """Test storage factory function"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test JSON
        json_path = os.path.join(temp_dir, "test.json")
        config = StorageConfig(storage_type=StorageType.JSON, file_path=json_path)
        storage = create_storage(config)
        assert isinstance(storage, JSONStorage)

        # Test CSV
        csv_path = os.path.join(temp_dir, "test.csv")
        config = StorageConfig(storage_type=StorageType.CSV, file_path=csv_path)
        storage = create_storage(config)
        assert isinstance(storage, CSVStorage)

        # Test SQLite
        sqlite_path = os.path.join(temp_dir, "test.db")
        config = StorageConfig(storage_type=StorageType.SQLITE, file_path=sqlite_path)
        storage = create_storage(config)
        assert isinstance(storage, SQLiteStorage)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
