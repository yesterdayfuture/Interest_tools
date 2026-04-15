"""
存储后端模块 - 用于保存执行记录和评估数据

本模块提供多种存储后端实现，支持不同的使用场景：
- JSONStorage: JSON文件存储，适合开发测试和小规模数据
- CSVStorage: CSV文件存储，适合数据分析和表格处理
- SQLiteStorage: SQLite数据库存储，适合单机应用和中等规模数据
- PostgresStorage: PostgreSQL数据库存储，适合生产环境和大规模数据

所有存储后端继承自BaseStorage，提供统一的接口

作者: AgentEval Team
创建日期: 2024
"""

import csv
import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_eval.models import (
    AgentExecution,
    EvaluationResult,
    ExpectedResult,
    StorageConfig,
    StorageType,
    StepDetail,
    ToolCallDetail,
)
from agent_eval.generators import GeneratedExpectedExecution

# 尝试导入PostgreSQL驱动，如果不可用则设置为None
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    psycopg2 = None
    RealDictCursor = None
    POSTGRES_AVAILABLE = False


class BaseStorage(ABC):
    """
    存储后端抽象基类

    所有存储后端必须继承此类并实现以下方法：
    - save_execution: 保存执行记录
    - save_evaluation: 保存评估结果
    - get_execution: 根据ID获取执行记录
    - get_evaluation: 根据ID获取评估结果
    - list_executions: 列出最近的执行记录
    - list_evaluations: 列出最近的评估结果
    - save_expected_execution: 保存预期执行（理想答案）
    - get_expected_execution: 根据查询获取预期执行
    - list_expected_executions: 列出最近的预期执行

    设计原则：
    - 统一的接口设计，便于切换存储后端
    - 支持执行记录、评估结果、预期执行三类数据
    - 所有方法都应该是线程安全的（由子类实现保证）
    """

    def __init__(self, config: StorageConfig):
        """
        初始化存储后端

        参数:
            config: 存储配置，包含存储类型、连接信息等
        """
        self.config = config

    @abstractmethod
    def save_execution(self, execution: AgentExecution) -> str:
        """
        保存执行记录

        参数:
            execution: 智能体执行记录对象

        返回:
            str: 执行记录的唯一标识符
        """
        pass

    @abstractmethod
    def save_evaluation(self, evaluation: EvaluationResult) -> str:
        """
        保存评估结果

        参数:
            evaluation: 评估结果对象

        返回:
            str: 评估结果的唯一标识符
        """
        pass

    @abstractmethod
    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """
        根据ID获取执行记录

        参数:
            execution_id: 执行记录ID

        返回:
            Optional[AgentExecution]: 执行记录对象，如果不存在则返回None
        """
        pass

    @abstractmethod
    def get_evaluation(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """
        根据ID获取评估结果

        参数:
            evaluation_id: 评估结果ID

        返回:
            Optional[EvaluationResult]: 评估结果对象，如果不存在则返回None
        """
        pass

    @abstractmethod
    def list_executions(self, limit: int = 100) -> List[AgentExecution]:
        """
        列出最近的执行记录

        参数:
            limit: 返回记录数量上限（默认100）

        返回:
            List[AgentExecution]: 执行记录列表，按时间倒序排列
        """
        pass

    @abstractmethod
    def list_evaluations(self, limit: int = 100) -> List[EvaluationResult]:
        """
        列出最近的评估结果

        参数:
            limit: 返回记录数量上限（默认100）

        返回:
            List[EvaluationResult]: 评估结果列表，按时间倒序排列
        """
        pass

    @abstractmethod
    def save_expected_execution(self, expected: GeneratedExpectedExecution) -> str:
        """
        保存预期执行（理想答案）

        参数:
            expected: 预期执行对象

        返回:
            str: 预期执行的唯一标识符
        """
        pass

    @abstractmethod
    def get_expected_execution(self, query: str) -> Optional[GeneratedExpectedExecution]:
        """
        根据查询获取预期执行

        参数:
            query: 用户查询字符串

        返回:
            Optional[GeneratedExpectedExecution]: 预期执行对象，如果不存在则返回None
        """
        pass

    @abstractmethod
    def list_expected_executions(self, limit: int = 100) -> List[GeneratedExpectedExecution]:
        """
        列出最近的预期执行

        参数:
            limit: 返回记录数量上限（默认100）

        返回:
            List[GeneratedExpectedExecution]: 预期执行列表，按时间倒序排列
        """
        pass


class JSONStorage(BaseStorage):
    """JSON file-based storage - optimized for new data model"""

    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.file_path = Path(config.file_path or "agent_eval_data.json")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load existing data from file"""
        if self.file_path.exists() and self.file_path.stat().st_size > 0:
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"executions": [], "evaluations": []}
        return {"executions": [], "evaluations": []}

    def _save_data(self):
        """Save data to file"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)

    def save_execution(self, execution: AgentExecution) -> str:
        """Save an execution record using the new data model"""
        execution_dict = execution.to_storage_dict()
        
        # Check if execution already exists
        existing_idx = None
        for idx, ex in enumerate(self._data["executions"]):
            if ex["execution_id"] == execution.execution_id:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            self._data["executions"][existing_idx] = execution_dict
        else:
            self._data["executions"].append(execution_dict)
        
        self._save_data()
        return execution.execution_id

    def save_evaluation(self, evaluation: EvaluationResult) -> str:
        """Save an evaluation result"""
        evaluation_dict = evaluation.model_dump()
        self._data["evaluations"].append(evaluation_dict)
        self._save_data()
        return evaluation.evaluation_id

    def save_expected_execution(self, expected: GeneratedExpectedExecution) -> str:
        """Save an expected execution (ideal answer) to SQLite"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create expected_executions table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expected_executions (
                    query TEXT PRIMARY KEY,
                    expected_output TEXT,
                    steps_detail_json TEXT,
                    tool_calls_detail_json TEXT,
                    step_count INTEGER DEFAULT 0,
                    tool_call_count INTEGER DEFAULT 0,
                    expected_duration_ms REAL,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO expected_executions (
                    query, expected_output, steps_detail_json, tool_calls_detail_json,
                    step_count, tool_call_count, expected_duration_ms, reasoning, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                expected.query,
                expected.expected_output,
                json.dumps([s.model_dump() for s in expected.steps_detail], ensure_ascii=False),
                json.dumps([t.model_dump() for t in expected.tool_calls_detail], ensure_ascii=False),
                expected.step_count,
                expected.tool_call_count,
                expected.expected_duration_ms,
                expected.reasoning,
                json.dumps(expected.metadata, ensure_ascii=False)
            ))
            conn.commit()
        return expected.query

    def get_expected_execution(self, query: str) -> Optional[GeneratedExpectedExecution]:
        """Retrieve an expected execution by query from SQLite"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expected_executions WHERE query = ?", (query,))
            row = cursor.fetchone()
            if row:
                return self._row_to_expected_execution(row)
        return None

    def list_expected_executions(self, limit: int = 100) -> List[GeneratedExpectedExecution]:
        """List recent expected executions from SQLite"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM expected_executions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_expected_execution(row) for row in rows]

    def _row_to_expected_execution(self, row) -> GeneratedExpectedExecution:
        """Convert database row to GeneratedExpectedExecution"""
        steps_detail = [StepDetail(**s) for s in json.loads(row[2] or '[]')]
        tool_calls_detail = [ToolCallDetail(**t) for t in json.loads(row[3] or '[]')]
        
        metadata = {}
        try:
            if row[9]:
                metadata = json.loads(row[9])
        except (json.JSONDecodeError, IndexError):
            metadata = {}
        
        return GeneratedExpectedExecution(
            query=row[0],
            expected_output=row[1] or '',
            steps_detail=steps_detail,
            tool_calls_detail=tool_calls_detail,
            step_count=row[4] or 0,
            tool_call_count=row[5] or 0,
            expected_duration_ms=row[6],
            reasoning=row[7],
            metadata=metadata
        )

    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """Retrieve an execution by ID"""
        for ex in self._data["executions"]:
            if ex["execution_id"] == execution_id:
                return self._dict_to_execution(ex)
        return None

    def get_evaluation(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """Retrieve an evaluation by ID"""
        for ev in self._data["evaluations"]:
            if ev["evaluation_id"] == evaluation_id:
                return EvaluationResult(**ev)
        return None

    def list_executions(self, limit: int = 100) -> List[AgentExecution]:
        """List recent executions"""
        executions = self._data["executions"][-limit:]
        return [self._dict_to_execution(ex) for ex in executions]

    def list_evaluations(self, limit: int = 100) -> List[EvaluationResult]:
        """List recent evaluations"""
        evaluations = self._data["evaluations"][-limit:]
        return [EvaluationResult(**ev) for ev in evaluations]

    def save_expected_execution(self, expected: GeneratedExpectedExecution) -> str:
        """Save an expected execution (ideal answer)"""
        if "expected_executions" not in self._data:
            self._data["expected_executions"] = []
        
        expected_dict = expected.model_dump()
        
        # Check if already exists (by query)
        existing_idx = None
        for idx, ex in enumerate(self._data["expected_executions"]):
            if ex["query"] == expected.query:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            self._data["expected_executions"][existing_idx] = expected_dict
        else:
            self._data["expected_executions"].append(expected_dict)
        
        self._save_data()
        return expected.query

    def get_expected_execution(self, query: str) -> Optional[GeneratedExpectedExecution]:
        """Retrieve an expected execution by query"""
        if "expected_executions" not in self._data:
            return None
        
        for ex in self._data["expected_executions"]:
            if ex["query"] == query:
                return GeneratedExpectedExecution.from_dict(ex)
        return None

    def list_expected_executions(self, limit: int = 100) -> List[GeneratedExpectedExecution]:
        """List recent expected executions"""
        if "expected_executions" not in self._data:
            return []
        
        expected_list = self._data["expected_executions"][-limit:]
        return [GeneratedExpectedExecution.from_dict(ex) for ex in expected_list]

    def _dict_to_execution(self, data: Dict) -> AgentExecution:
        """Convert dictionary to AgentExecution with proper type handling"""
        # Parse step details
        steps_detail = []
        for step_data in data.get("steps_detail", []):
            steps_detail.append(StepDetail(**step_data))
        
        # Parse tool call details
        tool_calls_detail = []
        for tool_data in data.get("tool_calls_detail", []):
            tool_calls_detail.append(ToolCallDetail(**tool_data))
        
        # Parse timestamps
        start_time = None
        if data.get("start_time"):
            try:
                start_time = datetime.fromisoformat(data["start_time"])
            except:
                pass
        
        end_time = None
        if data.get("end_time"):
            try:
                end_time = datetime.fromisoformat(data["end_time"])
            except:
                pass
        
        created_at = datetime.now()
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except:
                pass
        
        return AgentExecution(
            execution_id=data["execution_id"],
            query=data["query"],
            steps_summary=data.get("steps_summary", ""),
            steps_detail=steps_detail,
            tool_call_count=data.get("tool_call_count", 0),
            tool_calls_detail=tool_calls_detail,
            step_count=data.get("step_count", 0),
            final_output=data.get("final_output"),
            success=data.get("success", False),
            has_error=data.get("has_error", False),
            error_message=data.get("error_message"),
            total_duration_ms=data.get("total_duration_ms"),
            start_time=start_time,
            end_time=end_time,
            metadata=data.get("metadata", {}),
            created_at=created_at
        )


class CSVStorage(BaseStorage):
    """CSV file-based storage - flattened format for new data model"""

    def __init__(self, config: StorageConfig):
        super().__init__(config)
        base_path = Path(config.file_path or "agent_eval_data")
        base_path.parent.mkdir(parents=True, exist_ok=True)
        self.executions_file = base_path.parent / f"{base_path.stem}_executions.csv"
        self.evaluations_file = base_path.parent / f"{base_path.stem}_evaluations.csv"
        self._init_files()

    def _init_files(self):
        """Initialize CSV files with headers"""
        if not self.executions_file.exists():
            with open(self.executions_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'execution_id', 'query', 'steps_summary', 'steps_detail_json',
                    'tool_call_count', 'tool_calls_detail_json', 'step_count',
                    'final_output', 'success', 'has_error', 'error_message',
                    'total_duration_ms', 'start_time', 'end_time', 'created_at', 'metadata_json'
                ])

        if not self.evaluations_file.exists():
            with open(self.evaluations_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'evaluation_id', 'execution_id', 'query', 'overall_score',
                    'metric_scores_json', 'created_at'
                ])

    def save_execution(self, execution: AgentExecution) -> str:
        """Save an execution record"""
        with open(self.executions_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                execution.execution_id,
                execution.query,
                execution.steps_summary,
                json.dumps([step.model_dump() for step in execution.steps_detail], ensure_ascii=False),
                execution.tool_call_count,
                json.dumps([tool.model_dump() for tool in execution.tool_calls_detail], ensure_ascii=False),
                execution.step_count,
                execution.final_output,
                execution.success,
                execution.has_error,
                execution.error_message,
                execution.total_duration_ms,
                execution.start_time.isoformat() if execution.start_time else '',
                execution.end_time.isoformat() if execution.end_time else '',
                execution.created_at.isoformat(),
                json.dumps(execution.metadata, ensure_ascii=False)
            ])
        return execution.execution_id

    def save_evaluation(self, evaluation: EvaluationResult) -> str:
        """Save an evaluation result"""
        with open(self.evaluations_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                evaluation.evaluation_id,
                evaluation.execution_id,
                evaluation.query,
                evaluation.overall_score,
                json.dumps([m.model_dump() for m in evaluation.metric_scores], ensure_ascii=False),
                evaluation.created_at.isoformat()
            ])
        return evaluation.evaluation_id

    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """Retrieve an execution by ID"""
        with open(self.executions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['execution_id'] == execution_id:
                    return self._row_to_execution(row)
        return None

    def get_evaluation(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """Retrieve an evaluation by ID"""
        with open(self.evaluations_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['evaluation_id'] == evaluation_id:
                    return EvaluationResult(**row)
        return None

    def list_executions(self, limit: int = 100) -> List[AgentExecution]:
        """List recent executions"""
        executions = []
        with open(self.executions_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                executions.append(self._row_to_execution(row))
        return executions[-limit:]

    def list_evaluations(self, limit: int = 100) -> List[EvaluationResult]:
        """List recent evaluations"""
        evaluations = []
        with open(self.evaluations_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                evaluations.append(EvaluationResult(**row))
        return evaluations[-limit:]

    def save_expected_execution(self, expected: GeneratedExpectedExecution) -> str:
        """Save an expected execution (ideal answer) to CSV"""
        expected_file = self.executions_file.parent / f"{self.executions_file.stem.replace('_executions', '')}_expected.csv"
        
        # Initialize file if not exists
        if not expected_file.exists():
            with open(expected_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'query', 'expected_output', 'steps_detail_json', 'tool_calls_detail_json',
                    'step_count', 'tool_call_count', 'expected_duration_ms', 'reasoning', 'metadata_json'
                ])
        
        with open(expected_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                expected.query,
                expected.expected_output,
                json.dumps([s.model_dump() for s in expected.steps_detail], ensure_ascii=False),
                json.dumps([t.model_dump() for t in expected.tool_calls_detail], ensure_ascii=False),
                expected.step_count,
                expected.tool_call_count,
                expected.expected_duration_ms,
                expected.reasoning,
                json.dumps(expected.metadata, ensure_ascii=False)
            ])
        return expected.query

    def get_expected_execution(self, query: str) -> Optional[GeneratedExpectedExecution]:
        """Retrieve an expected execution by query from CSV"""
        expected_file = self.executions_file.parent / f"{self.executions_file.stem.replace('_executions', '')}_expected.csv"
        
        if not expected_file.exists():
            return None
        
        with open(expected_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['query'] == query:
                    return self._row_to_expected_execution(row)
        return None

    def list_expected_executions(self, limit: int = 100) -> List[GeneratedExpectedExecution]:
        """List recent expected executions from CSV"""
        expected_file = self.executions_file.parent / f"{self.executions_file.stem.replace('_executions', '')}_expected.csv"
        
        if not expected_file.exists():
            return []
        
        expected_list = []
        with open(expected_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                expected_list.append(self._row_to_expected_execution(row))
        return expected_list[-limit:]

    def _row_to_execution(self, row: Dict) -> AgentExecution:
        """Convert CSV row to AgentExecution"""
        steps_detail = [StepDetail(**s) for s in json.loads(row['steps_detail_json'])]
        tool_calls_detail = [ToolCallDetail(**t) for t in json.loads(row['tool_calls_detail_json'])]
        
        return AgentExecution(
            execution_id=row['execution_id'],
            query=row['query'],
            steps_summary=row['steps_summary'],
            steps_detail=steps_detail,
            tool_call_count=int(row['tool_call_count']),
            tool_calls_detail=tool_calls_detail,
            step_count=int(row['step_count']),
            final_output=row['final_output'] or None,
            success=row['success'] == 'True',
            has_error=row['has_error'] == 'True',
            error_message=row['error_message'] or None,
            total_duration_ms=float(row['total_duration_ms']) if row['total_duration_ms'] else None,
            metadata=json.loads(row['metadata_json'])
        )

    def _row_to_expected_execution(self, row: Dict) -> GeneratedExpectedExecution:
        """Convert CSV row to GeneratedExpectedExecution"""
        steps_detail = [StepDetail(**s) for s in json.loads(row['steps_detail_json'])]
        tool_calls_detail = [ToolCallDetail(**t) for t in json.loads(row['tool_calls_detail_json'])]
        
        return GeneratedExpectedExecution(
            query=row['query'],
            expected_output=row['expected_output'],
            steps_detail=steps_detail,
            tool_calls_detail=tool_calls_detail,
            step_count=int(row['step_count']),
            tool_call_count=int(row['tool_call_count']),
            expected_duration_ms=float(row['expected_duration_ms']) if row['expected_duration_ms'] else None,
            reasoning=row['reasoning'],
            metadata=json.loads(row['metadata_json'])
        )


class SQLiteStorage(BaseStorage):
    """SQLite database storage - optimized for new data model"""

    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.db_path = config.file_path or "agent_eval.db"
        self._init_db()

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    steps_summary TEXT,
                    steps_detail_json TEXT,
                    tool_call_count INTEGER DEFAULT 0,
                    tool_calls_detail_json TEXT,
                    step_count INTEGER DEFAULT 0,
                    final_output TEXT,
                    success BOOLEAN DEFAULT 0,
                    has_error BOOLEAN DEFAULT 0,
                    error_message TEXT,
                    total_duration_ms REAL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT
                )
            """)
            
            # Evaluations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    execution_id TEXT,
                    query TEXT,
                    overall_score REAL,
                    metric_scores_json TEXT,
                    agent_execution_json TEXT,
                    expected_result_json TEXT,
                    scorer_results_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT,
                    FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
                )
            """)
            
            conn.commit()

    def save_execution(self, execution: AgentExecution) -> str:
        """Save an execution record"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO executions (
                    execution_id, query, steps_summary, steps_detail_json,
                    tool_call_count, tool_calls_detail_json, step_count,
                    final_output, success, has_error, error_message,
                    total_duration_ms, start_time, end_time, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.execution_id,
                execution.query,
                execution.steps_summary,
                json.dumps([s.model_dump() for s in execution.steps_detail], ensure_ascii=False),
                execution.tool_call_count,
                json.dumps([t.model_dump() for t in execution.tool_calls_detail], ensure_ascii=False),
                execution.step_count,
                execution.final_output,
                execution.success,
                execution.has_error,
                execution.error_message,
                execution.total_duration_ms,
                execution.start_time,
                execution.end_time,
                json.dumps(execution.metadata, ensure_ascii=False)
            ))
            conn.commit()
        return execution.execution_id

    def save_evaluation(self, evaluation: EvaluationResult) -> str:
        """Save an evaluation result"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO evaluations (
                    evaluation_id, execution_id, query, overall_score,
                    metric_scores_json, agent_execution_json, expected_result_json,
                    scorer_results_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evaluation.evaluation_id,
                evaluation.execution_id,
                evaluation.query,
                evaluation.overall_score,
                json.dumps([m.model_dump() for m in evaluation.metric_scores], ensure_ascii=False),
                json.dumps(evaluation.agent_execution.to_storage_dict(), ensure_ascii=False),
                json.dumps(evaluation.expected_result.model_dump() if evaluation.expected_result else {}, ensure_ascii=False),
                json.dumps(evaluation.scorer_results, ensure_ascii=False),
                json.dumps(evaluation.metadata, ensure_ascii=False)
            ))
            conn.commit()
        return evaluation.evaluation_id

    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """Retrieve an execution by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM executions WHERE execution_id = ?", (execution_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_execution(row)
        return None

    def get_evaluation(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """Retrieve an evaluation by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluations WHERE evaluation_id = ?", (evaluation_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_evaluation(row)
        return None

    def list_executions(self, limit: int = 100) -> List[AgentExecution]:
        """List recent executions"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM executions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_execution(row) for row in rows]

    def list_evaluations(self, limit: int = 100) -> List[EvaluationResult]:
        """List recent evaluations"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM evaluations ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_evaluation(row) for row in rows]

    def _row_to_execution(self, row) -> AgentExecution:
        """Convert database row to AgentExecution"""
        steps_detail = [StepDetail(**s) for s in json.loads(row[3] or '[]')]
        tool_calls_detail = [ToolCallDetail(**t) for t in json.loads(row[5] or '[]')]
        
        # Parse metadata from row[14] (metadata_json column)
        metadata = {}
        try:
            if row[14]:
                metadata = json.loads(row[14])
        except (json.JSONDecodeError, IndexError):
            metadata = {}
        
        return AgentExecution(
            execution_id=row[0],
            query=row[1],
            steps_summary=row[2] or '',
            steps_detail=steps_detail,
            tool_call_count=row[4] or 0,
            tool_calls_detail=tool_calls_detail,
            step_count=row[6] or 0,
            final_output=row[7],
            success=bool(row[8]),
            has_error=bool(row[9]),
            error_message=row[10],
            total_duration_ms=row[11],
            metadata=metadata
        )

    def _row_to_evaluation(self, row) -> EvaluationResult:
        """Convert database row to EvaluationResult"""
        return EvaluationResult(
            evaluation_id=row[0],
            execution_id=row[1],
            query=row[2],
            overall_score=row[3],
            metric_scores=[],
            agent_execution=AgentExecution(execution_id=row[1], query=row[2]),
            created_at=datetime.now()
        )


class PostgresStorage(BaseStorage):
    """
    PostgreSQL数据库存储后端

    适用于生产环境和大规模数据存储，支持高并发访问和复杂查询。
    使用连接池管理数据库连接，确保性能和可靠性。

    数据库表结构:
    - agent_executions: 存储智能体执行记录
    - evaluation_results: 存储评估结果
    - expected_executions: 存储预期执行（理想答案）

    特点:
    - 支持高并发读写
    - 支持事务处理
    - 支持复杂查询和索引
    - 适合大规模数据存储

    依赖:
    - psycopg2: PostgreSQL数据库驱动

    示例:
        >>> config = StorageConfig(
        ...     storage_type=StorageType.POSTGRES,
        ...     connection_string="postgresql://user:pass@localhost:5432/agent_eval"
        ... )
        >>> storage = PostgresStorage(config)
        >>> storage.save_execution(execution)
    """

    def __init__(self, config: StorageConfig):
        """
        初始化PostgreSQL存储后端

        参数:
            config: 存储配置，必须包含connection_string或数据库连接参数
                   connection_string格式: postgresql://user:password@host:port/dbname

        异常:
            ImportError: 如果psycopg2未安装
            ConnectionError: 如果无法连接到数据库
        """
        super().__init__(config)

        if not POSTGRES_AVAILABLE:
            raise ImportError(
                "使用PostgreSQL存储需要安装psycopg2。\n"
                "请运行: pip install psycopg2-binary"
            )

        # 获取连接参数
        self.connection_string = getattr(config, 'connection_string', None)
        self.host = getattr(config, 'host', 'localhost')
        self.port = getattr(config, 'port', 5432)
        self.database = getattr(config, 'database', 'agent_eval')
        self.user = getattr(config, 'user', None)
        self.password = getattr(config, 'password', None)

        # 初始化数据库连接和表结构
        self._init_database()

    def _get_connection(self):
        """
        获取数据库连接

        优先使用connection_string，如果没有则使用独立参数

        返回:
            psycopg2.connection: 数据库连接对象
        """
        if self.connection_string:
            return psycopg2.connect(self.connection_string)
        else:
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )

    def _init_database(self):
        """
        初始化数据库表结构

        创建所需的数据表（如果不存在）:
        - agent_executions: 执行记录表
        - evaluation_results: 评估结果表
        - expected_executions: 预期执行表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 创建执行记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    execution_id VARCHAR(255) PRIMARY KEY,
                    query TEXT NOT NULL,
                    steps_summary TEXT,
                    steps_detail_json TEXT,
                    tool_call_count INTEGER DEFAULT 0,
                    tool_calls_detail_json TEXT,
                    step_count INTEGER DEFAULT 0,
                    final_output TEXT,
                    success BOOLEAN DEFAULT FALSE,
                    has_error BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    total_duration_ms REAL,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建评估结果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_results (
                    evaluation_id VARCHAR(255) PRIMARY KEY,
                    execution_id VARCHAR(255) NOT NULL,
                    query TEXT NOT NULL,
                    overall_score REAL DEFAULT 0.0,
                    metric_scores_json TEXT,
                    scorer_results_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT
                )
            """)

            # 创建预期执行表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expected_executions (
                    query TEXT PRIMARY KEY,
                    expected_output TEXT,
                    steps_detail_json TEXT,
                    tool_calls_detail_json TEXT,
                    step_count INTEGER DEFAULT 0,
                    tool_call_count INTEGER DEFAULT 0,
                    expected_duration_ms REAL,
                    reasoning TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引以提高查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_created_at
                ON agent_executions (created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_evaluations_created_at
                ON evaluation_results (created_at DESC)
            """)

            conn.commit()

    def save_execution(self, execution: AgentExecution) -> str:
        """
        保存执行记录到PostgreSQL

        参数:
            execution: 智能体执行记录对象

        返回:
            str: 执行记录ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO agent_executions (
                    execution_id, query, steps_summary, steps_detail_json,
                    tool_call_count, tool_calls_detail_json, step_count,
                    final_output, success, has_error, error_message,
                    total_duration_ms, metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (execution_id) DO UPDATE SET
                    query = EXCLUDED.query,
                    steps_summary = EXCLUDED.steps_summary,
                    steps_detail_json = EXCLUDED.steps_detail_json,
                    tool_call_count = EXCLUDED.tool_call_count,
                    tool_calls_detail_json = EXCLUDED.tool_calls_detail_json,
                    step_count = EXCLUDED.step_count,
                    final_output = EXCLUDED.final_output,
                    success = EXCLUDED.success,
                    has_error = EXCLUDED.has_error,
                    error_message = EXCLUDED.error_message,
                    total_duration_ms = EXCLUDED.total_duration_ms,
                    metadata_json = EXCLUDED.metadata_json
            """, (
                execution.execution_id,
                execution.query,
                execution.steps_summary,
                json.dumps([s.model_dump() for s in execution.steps_detail], ensure_ascii=False),
                execution.tool_call_count,
                json.dumps([t.model_dump() for t in execution.tool_calls_detail], ensure_ascii=False),
                execution.step_count,
                execution.final_output,
                execution.success,
                execution.has_error,
                execution.error_message,
                execution.total_duration_ms,
                json.dumps(execution.metadata, ensure_ascii=False)
            ))

            conn.commit()
        return execution.execution_id

    def save_evaluation(self, evaluation: EvaluationResult) -> str:
        """
        保存评估结果到PostgreSQL

        参数:
            evaluation: 评估结果对象

        返回:
            str: 评估结果ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO evaluation_results (
                    evaluation_id, execution_id, query, overall_score,
                    metric_scores_json, scorer_results_json, metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (evaluation_id) DO UPDATE SET
                    execution_id = EXCLUDED.execution_id,
                    query = EXCLUDED.query,
                    overall_score = EXCLUDED.overall_score,
                    metric_scores_json = EXCLUDED.metric_scores_json,
                    scorer_results_json = EXCLUDED.scorer_results_json,
                    metadata_json = EXCLUDED.metadata_json
            """, (
                evaluation.evaluation_id,
                evaluation.execution_id,
                evaluation.query,
                evaluation.overall_score,
                json.dumps([s.model_dump() for s in evaluation.metric_scores], ensure_ascii=False),
                json.dumps(evaluation.scorer_results, ensure_ascii=False),
                json.dumps(evaluation.metadata, ensure_ascii=False)
            ))

            conn.commit()
        return evaluation.evaluation_id

    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """
        根据ID获取执行记录

        参数:
            execution_id: 执行记录ID

        返回:
            Optional[AgentExecution]: 执行记录对象，如果不存在则返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_executions WHERE execution_id = %s",
                (execution_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_execution(row)
        return None

    def get_evaluation(self, evaluation_id: str) -> Optional[EvaluationResult]:
        """
        根据ID获取评估结果

        参数:
            evaluation_id: 评估结果ID

        返回:
            Optional[EvaluationResult]: 评估结果对象，如果不存在则返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM evaluation_results WHERE evaluation_id = %s",
                (evaluation_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_evaluation(row)
        return None

    def list_executions(self, limit: int = 100) -> List[AgentExecution]:
        """
        列出最近的执行记录

        参数:
            limit: 返回记录数量上限（默认100）

        返回:
            List[AgentExecution]: 执行记录列表，按时间倒序排列
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_executions ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_execution(row) for row in rows]

    def list_evaluations(self, limit: int = 100) -> List[EvaluationResult]:
        """
        列出最近的评估结果

        参数:
            limit: 返回记录数量上限（默认100）

        返回:
            List[EvaluationResult]: 评估结果列表，按时间倒序排列
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM evaluation_results ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_evaluation(row) for row in rows]

    def save_expected_execution(self, expected: GeneratedExpectedExecution) -> str:
        """
        保存预期执行（理想答案）

        参数:
            expected: 预期执行对象

        返回:
            str: 查询字符串（作为主键）
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO expected_executions (
                    query, expected_output, steps_detail_json, tool_calls_detail_json,
                    step_count, tool_call_count, expected_duration_ms, reasoning, metadata_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (query) DO UPDATE SET
                    expected_output = EXCLUDED.expected_output,
                    steps_detail_json = EXCLUDED.steps_detail_json,
                    tool_calls_detail_json = EXCLUDED.tool_calls_detail_json,
                    step_count = EXCLUDED.step_count,
                    tool_call_count = EXCLUDED.tool_call_count,
                    expected_duration_ms = EXCLUDED.expected_duration_ms,
                    reasoning = EXCLUDED.reasoning,
                    metadata_json = EXCLUDED.metadata_json
            """, (
                expected.query,
                expected.expected_output,
                json.dumps([s.model_dump() for s in expected.steps_detail], ensure_ascii=False),
                json.dumps([t.model_dump() for t in expected.tool_calls_detail], ensure_ascii=False),
                expected.step_count,
                expected.tool_call_count,
                expected.expected_duration_ms,
                expected.reasoning,
                json.dumps(expected.metadata, ensure_ascii=False)
            ))

            conn.commit()
        return expected.query

    def get_expected_execution(self, query: str) -> Optional[GeneratedExpectedExecution]:
        """
        根据查询获取预期执行

        参数:
            query: 用户查询字符串

        返回:
            Optional[GeneratedExpectedExecution]: 预期执行对象，如果不存在则返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM expected_executions WHERE query = %s",
                (query,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_expected_execution(row)
        return None

    def list_expected_executions(self, limit: int = 100) -> List[GeneratedExpectedExecution]:
        """
        列出最近的预期执行

        参数:
            limit: 返回记录数量上限（默认100）

        返回:
            List[GeneratedExpectedExecution]: 预期执行列表，按时间倒序排列
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM expected_executions ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_expected_execution(row) for row in rows]

    def _row_to_execution(self, row) -> AgentExecution:
        """
        将数据库行转换为AgentExecution对象

        参数:
            row: 数据库查询结果行

        返回:
            AgentExecution: 执行记录对象
        """
        steps_detail = [StepDetail(**s) for s in json.loads(row[3] or '[]')]
        tool_calls_detail = [ToolCallDetail(**t) for t in json.loads(row[5] or '[]')]

        metadata = {}
        try:
            if row[12]:
                metadata = json.loads(row[12])
        except (json.JSONDecodeError, IndexError):
            metadata = {}

        return AgentExecution(
            execution_id=row[0],
            query=row[1],
            steps_summary=row[2] or '',
            steps_detail=steps_detail,
            tool_call_count=row[4] or 0,
            tool_calls_detail=tool_calls_detail,
            step_count=row[6] or 0,
            final_output=row[7],
            success=bool(row[8]),
            has_error=bool(row[9]),
            error_message=row[10],
            total_duration_ms=row[11],
            metadata=metadata
        )

    def _row_to_evaluation(self, row) -> EvaluationResult:
        """
        将数据库行转换为EvaluationResult对象

        参数:
            row: 数据库查询结果行

        返回:
            EvaluationResult: 评估结果对象
        """
        from agent_eval.models import MetricScore

        metric_scores = []
        try:
            if row[4]:
                metric_data = json.loads(row[4])
                metric_scores = [MetricScore(**m) for m in metric_data]
        except (json.JSONDecodeError, IndexError):
            metric_scores = []

        scorer_results = []
        try:
            if row[5]:
                scorer_results = json.loads(row[5])
        except (json.JSONDecodeError, IndexError):
            scorer_results = []

        metadata = {}
        try:
            if row[7]:
                metadata = json.loads(row[7])
        except (json.JSONDecodeError, IndexError):
            metadata = {}

        return EvaluationResult(
            evaluation_id=row[0],
            execution_id=row[1],
            query=row[2],
            overall_score=row[3] or 0.0,
            metric_scores=metric_scores,
            agent_execution=AgentExecution(execution_id=row[1], query=row[2]),
            scorer_results=scorer_results,
            created_at=row[6] if len(row) > 6 else datetime.now(),
            metadata=metadata
        )

    def _row_to_expected_execution(self, row) -> GeneratedExpectedExecution:
        """
        将数据库行转换为GeneratedExpectedExecution对象

        参数:
            row: 数据库查询结果行

        返回:
            GeneratedExpectedExecution: 预期执行对象
        """
        steps_detail = [StepDetail(**s) for s in json.loads(row[2] or '[]')]
        tool_calls_detail = [ToolCallDetail(**t) for t in json.loads(row[3] or '[]')]

        metadata = {}
        try:
            if row[8]:
                metadata = json.loads(row[8])
        except (json.JSONDecodeError, IndexError):
            metadata = {}

        return GeneratedExpectedExecution(
            query=row[0],
            expected_output=row[1] or '',
            steps_detail=steps_detail,
            tool_calls_detail=tool_calls_detail,
            step_count=row[4] or 0,
            tool_call_count=row[5] or 0,
            expected_duration_ms=row[6],
            reasoning=row[7],
            metadata=metadata
        )


def create_storage(config: StorageConfig) -> BaseStorage:
    """
    存储后端工厂函数

    根据配置创建对应的存储后端实例

    参数:
        config: 存储配置，包含存储类型和连接信息

    返回:
        BaseStorage: 存储后端实例

    异常:
        ValueError: 如果存储类型不受支持

    示例:
        >>> config = StorageConfig(
        ...     storage_type=StorageType.SQLITE,
        ...     file_path="data.db"
        ... )
        >>> storage = create_storage(config)
    """
    if config.storage_type == StorageType.JSON:
        return JSONStorage(config)
    elif config.storage_type == StorageType.CSV:
        return CSVStorage(config)
    elif config.storage_type == StorageType.SQLITE:
        return SQLiteStorage(config)
    elif config.storage_type == StorageType.POSTGRES:
        return PostgresStorage(config)
    else:
        raise ValueError(f"不支持的存储类型: {config.storage_type}")
