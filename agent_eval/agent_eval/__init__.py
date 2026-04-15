"""
Agent Eval - A comprehensive evaluation system for AI agents
"""

__version__ = "0.1.0"

# Core classes
from agent_eval.core import AgentEvaluator, EvaluationConfig, EvaluationResult

# Models
from agent_eval.models import (
    AgentExecution,
    ExpectedResult,
    MetricScore,
    StorageConfig,
    StorageType,
    StepDetail,
    ToolCallDetail,
    LLMConfig,
)

# Metrics
from agent_eval.metrics import (
    Correctness,
    StepRatio,
    ToolCallRatio,
    SolveRate,
    LatencyRatio,
)

# Scorers
from agent_eval.scorers import CodeBasedScorer, LLMJudgeScorer, ScorerResult

# Recorders
from agent_eval.recorders import ExecutionRecorder, ExecutionRecord

# Tracker (new low-intrusive integration tool)
from agent_eval.tracker import (
    AgentTracker,
    ExecutionContext,
    track_agent,
)

# Storages
from agent_eval.storages import (
    JSONStorage,
    CSVStorage,
    SQLiteStorage,
    PostgresStorage,
    create_storage,
)

# Generators
from agent_eval.generators import MetadataGenerator, GeneratedExpectedExecution, ToolInfo

# Reporting
from agent_eval.reporting import ReportGenerator, EvaluationPipeline

# Text Similarity (n-gram based)
from agent_eval.text_similarity import (
    NGramSimilarity,
    calculate_text_similarity,
    SimilarityCalculators,
)

# Decorators (non-intrusive integration)
from agent_eval.decorators import (
    track_agent,
    track_tool,
    track_step,
    track,
    TrackedExecution,
    configure_storage,
    get_execution,
    get_last_execution as get_last_exec,
    list_executions,
    get_current_execution,
    get_current_execution_id,
)

# Framework Integrations
try:
    from agent_eval.integrations import (
        LangChainCallback,
        LangGraphTracer,
        track_langgraph,
    )
except ImportError:
    # 可选依赖未安装
    LangChainCallback = None
    LangGraphTracer = None
    track_langgraph = None

__all__ = [
    # Core
    "AgentEvaluator",
    "EvaluationConfig",
    "EvaluationResult",
    # Models
    "AgentExecution",
    "ExpectedResult",
    "MetricScore",
    "StorageConfig",
    "StorageType",
    "StepDetail",
    "ToolCallDetail",
    "LLMConfig",
    # Metrics
    "Correctness",
    "StepRatio",
    "ToolCallRatio",
    "SolveRate",
    "LatencyRatio",
    # Scorers
    "CodeBasedScorer",
    "LLMJudgeScorer",
    "ScorerResult",
    # Recorders
    "ExecutionRecorder",
    "ExecutionRecord",
    # Tracker (new)
    "AgentTracker",
    "ExecutionContext",
    "track_agent",
    # Storages
    "JSONStorage",
    "CSVStorage",
    "SQLiteStorage",
    "PostgresStorage",
    "create_storage",
    # Generators
    "MetadataGenerator",
    "GeneratedExpectedExecution",
    "ToolInfo",
    # Reporting
    "ReportGenerator",
    "EvaluationPipeline",
    # Text Similarity
    "NGramSimilarity",
    "calculate_text_similarity",
    "SimilarityCalculators",
    # Decorators
    "track_agent",
    "track_tool",
    "track_step",
    "TrackedExecution",
    "configure_storage",
    "get_execution",
    "get_last_exec",
    "list_executions",
    "get_current_execution",
    "get_current_execution_id",
    # Integrations (may be None if dependencies not installed)
    "LangChainCallback",
    "LangGraphTracer",
    "track_langgraph",
]
