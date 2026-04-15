"""
核心数据模型模块 - 定义智能体评估的所有数据模型

本模块使用Pydantic定义评估框架的核心数据结构，包括：
- 执行记录模型：记录智能体的执行过程
- 评估结果模型：存储评估结果和指标
- 配置模型：存储类型、LLM配置等
- 步骤和工具调用详情：详细的执行信息

所有模型都继承自Pydantic的BaseModel，提供：
- 数据验证：自动验证字段类型和约束
- 序列化：支持JSON和字典转换
- 文档：自动生成字段文档

作者: AgentEval Team
创建日期: 2024
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from dataclasses import dataclass



class StorageType(str, Enum):
    """
    支持的存储类型枚举

    定义了评估框架支持的所有存储后端类型：
    - JSON: JSON文件存储，适合开发测试
    - CSV: CSV文件存储，适合数据分析
    - SQLITE: SQLite数据库存储，适合单机应用
    - POSTGRES: PostgreSQL数据库存储，适合生产环境

    示例:
        >>> storage_type = StorageType.SQLITE
        >>> print(storage_type.value)  # "sqlite"
    """
    JSON = "json"
    CSV = "csv"
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class ToolCallDetail(BaseModel):
    """
    工具调用详情模型

    记录单次工具调用的完整信息，包括输入参数、输出结果、执行状态等。
    用于详细追踪智能体的工具使用情况。

    属性:
        name: 工具名称
        input: 工具输入参数（字典格式）
        output: 工具执行输出（任意类型）
        time: 执行耗时（毫秒）
        success: 是否执行成功
        err_msg: 错误信息（如果失败）
        timestamp: 调用时间戳

    示例:
        >>> detail = ToolCallDetail(
        ...     name="weather_api",
        ...     input={"city": "北京"},
        ...     output={"temperature": 25, "weather": "晴朗"},
        ...     time=150.5,
        ...     success=True
        ... )
    """
    name: str = Field(description="工具名称")
    input: Dict[str, Any] = Field(default_factory=dict, description="工具输入参数")
    output: Optional[Any] = Field(default=None, description="工具执行输出")
    time: Optional[float] = Field(default=None, description="执行耗时（毫秒）")
    success: bool = Field(default=True, description="是否执行成功")
    err_msg: Optional[str] = Field(default=None, description="错误信息（如果失败）")
    timestamp: datetime = Field(default_factory=datetime.now, description="调用时间戳")



class StepDetail(BaseModel):
    """Detailed information about an execution step"""
    step: int = Field(description="Step sequence number (1, 2, 3...)")
    description: str = Field(default="", description="Step description")
    input: Optional[Any] = Field(default=None, description="Step input")
    output: Optional[Any] = Field(default=None, description="Step output")
    time: Optional[float] = Field(default=None, description="Step execution duration in milliseconds")
    success: bool = Field(default=True, description="Whether step execution succeeded")
    err_msg: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Step timestamp")


class AgentExecution(BaseModel):
    """
    Complete execution information of an agent - one Q&A as one record
    
    Contains all information about a single agent execution:
    - User query
    - Execution steps summary (formatted as "第一步执行...\n第二步执行...")
    - Detailed step information
    - Tool call count and details
    - Final result and status
    """
    execution_id: str = Field(description="Unique execution identifier")
    query: str = Field(description="User input query")
    
    # Execution steps summary - formatted as "第一步执行...\n第二步执行..."
    steps_summary: str = Field(default="", description="Execution steps summary in Chinese format")
    
    # Detailed step information
    steps_detail: List[StepDetail] = Field(
        default_factory=list, 
        description="Detailed step information with input/output/time/success/err_msg"
    )
    
    # Tool call information
    tool_call_count: int = Field(default=0, description="Total number of tool calls")
    tool_calls_detail: List[ToolCallDetail] = Field(
        default_factory=list,
        description="Detailed tool call information with name/input/output/time/success/err_msg"
    )
    
    # Step count
    step_count: int = Field(default=0, description="Total number of execution steps")
    
    # Final result
    final_output: Optional[str] = Field(default=None, description="Agent's final output/answer")
    
    # Execution status
    success: bool = Field(default=False, description="Whether execution succeeded")
    has_error: bool = Field(default=False, description="Whether any error occurred")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    # Timing
    total_duration_ms: Optional[float] = Field(default=None, description="Total execution time in milliseconds")
    start_time: Optional[datetime] = Field(default=None, description="Execution start time")
    end_time: Optional[datetime] = Field(default=None, description="Execution end time")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.now, description="Record creation timestamp")

    def to_storage_dict(self) -> Dict[str, Any]:
        """Convert to dictionary optimized for storage"""
        return {
            "execution_id": self.execution_id,
            "query": self.query,
            "steps_summary": self.steps_summary,
            "steps_detail": [step.model_dump() for step in self.steps_detail],
            "tool_call_count": self.tool_call_count,
            "tool_calls_detail": [tool.model_dump() for tool in self.tool_calls_detail],
            "step_count": self.step_count,
            "final_output": self.final_output,
            "success": self.success,
            "has_error": self.has_error,
            "error_message": self.error_message,
            "total_duration_ms": self.total_duration_ms,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class ExpectedResult(BaseModel):
    """Expected result for evaluation"""
    expected_output: Optional[str] = Field(default=None, description="Expected final output")
    expected_steps: Optional[List[str]] = Field(default=None, description="Expected step descriptions")
    expected_tool_calls: Optional[List[str]] = Field(default=None, description="Expected tool call sequence")
    expected_tool_count: Optional[int] = Field(default=None, description="Expected number of tool calls")
    expected_step_count: Optional[int] = Field(default=None, description="Expected number of steps")
    expected_duration_ms: Optional[float] = Field(default=None, description="Expected execution duration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MetricScore(BaseModel):
    """Score for a single metric"""
    metric_name: str = Field(description="Metric name")
    score: float = Field(description="Score value (0.0 to 1.0)", ge=0.0, le=1.0)
    weight: float = Field(default=1.0, description="Metric weight", ge=0.0)
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed information")


class EvaluationResult(BaseModel):
    """Complete evaluation result"""
    evaluation_id: str = Field(description="Unique evaluation identifier")
    execution_id: str = Field(description="Reference to execution")
    query: str = Field(description="Original query")
    overall_score: float = Field(description="Weighted overall score", ge=0.0, le=1.0)
    metric_scores: List[MetricScore] = Field(default_factory=list, description="Individual metric scores")
    agent_execution: AgentExecution = Field(description="Agent execution details")
    expected_result: Optional[ExpectedResult] = Field(default=None, description="Expected result")
    scorer_results: List[Dict[str, Any]] = Field(default_factory=list, description="Scorer results")
    created_at: datetime = Field(default_factory=datetime.now, description="Evaluation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_metric_score(self, metric_name: str) -> Optional[float]:
        """Get score for a specific metric"""
        for metric in self.metric_scores:
            if metric.metric_name == metric_name:
                return metric.score
        return None


# Configuration Models

class LLMConfig(BaseModel):
    """Configuration for LLM-based features"""
    api_key: str = Field(description="API key for LLM service")
    base_url: Optional[str] = Field(default=None, description="Base URL for API")
    model: str = Field(default="gpt-4", description="Model name")
    temperature: float = Field(default=0.0, description="Sampling temperature")
    max_tokens: int = Field(default=500, description="Maximum tokens to generate")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")


class StorageConfig(BaseModel):
    """Configuration for data storage"""
    storage_type: StorageType = Field(default=StorageType.JSON, description="Storage backend type")
    file_path: Optional[str] = Field(default=None, description="Path for file-based storage")
    connection_string: Optional[str] = Field(default=None, description="Connection string for database")
    table_prefix: str = Field(default="agent_eval", description="Prefix for database tables")


class EvaluationConfig(BaseModel):
    """Configuration for evaluation"""
    # Scorer configuration
    use_code_scorer: bool = Field(default=True, description="Enable code-based scorer")
    use_llm_scorer: bool = Field(default=False, description="Enable LLM-based scorer")
    
    # LLM configuration (required if use_llm_scorer=True)
    llm_config: Optional[LLMConfig] = Field(default=None, description="LLM configuration")
    
    # Storage configuration
    storage_config: Optional[StorageConfig] = Field(default=None, description="Storage configuration")
    
    # Metric weights
    correctness_weight: float = Field(default=0.3, description="Weight for correctness metric")
    step_ratio_weight: float = Field(default=0.2, description="Weight for step ratio metric")
    tool_call_ratio_weight: float = Field(default=0.2, description="Weight for tool call ratio metric")
    solve_rate_weight: float = Field(default=0.2, description="Weight for solve rate metric")
    latency_ratio_weight: float = Field(default=0.1, description="Weight for latency ratio metric")
    
    # Metric enablement
    enable_correctness: bool = Field(default=True, description="Enable correctness metric")
    enable_step_ratio: bool = Field(default=True, description="Enable step ratio metric")
    enable_tool_call_ratio: bool = Field(default=True, description="Enable tool call ratio metric")
    enable_solve_rate: bool = Field(default=True, description="Enable solve rate metric")
    enable_latency_ratio: bool = Field(default=True, description="Enable latency ratio metric")
    
    # Recording configuration
    auto_record: bool = Field(default=True, description="Automatically record executions")
    
    class Config:
        arbitrary_types_allowed = True
