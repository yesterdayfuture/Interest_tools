# LangGraph 集成指南

本指南介绍如何将 `agent-eval` 与 LangGraph 集成，以记录执行过程并评估智能体性能。

## 核心概念

### 1. 记录执行数据

由于 LangGraph 的状态必须是可序列化的，我们使用全局存储来保存 `ExecutionRecorder` 实例：

```python
from agent_eval.recorders import ExecutionRecorder

# 全局存储
_recorder_store = {}

def get_recorder(execution_id: str):
    return _recorder_store.get(execution_id)

def set_recorder(execution_id: str, recorder: ExecutionRecorder):
    _recorder_store[execution_id] = recorder
```

### 2. 在 LangGraph 节点中记录

在每个节点中，你可以记录步骤和工具调用：

```python
def agent_node(state: AgentState) -> AgentState:
    # 获取记录器
    recorder = get_recorder(state["execution_id"])
    
    # 记录步骤
    if recorder:
        recorder.record_step("Agent processes query", {
            "query": state["query"]
        })
    
    # 记录工具调用（带计时）
    if recorder:
        start_time = time.time()
        result = some_tool.call()
        duration_ms = (time.time() - start_time) * 1000
        
        recorder.record_tool_call(
            tool_name="some_tool",
            arguments={"arg": "value"},
            result=result,
            duration_ms=duration_ms
        )
    
    return state
```

### 3. 结束记录

在最终节点中结束记录并获取执行数据：

```python
def final_node(state: AgentState) -> AgentState:
    recorder = get_recorder(state["execution_id"])
    
    if recorder:
        # 记录最终步骤
        recorder.record_step("Generate final answer")
        
        # 结束记录
        execution = recorder.end_recording(
            success=True,
            final_output="Your answer here"
        )
    
    return state
```

## 完整示例

```python
from typing import TypedDict, Annotated
import operator
import time
from langgraph.graph import StateGraph, END
from agent_eval import AgentEvaluator, EvaluationConfig
from agent_eval.models import ExpectedResult
from agent_eval.recorders import ExecutionRecorder

# 全局存储
_recorder_store = {}

def get_recorder(eid: str):
    return _recorder_store.get(eid)

def set_recorder(eid: str, recorder):
    _recorder_store[eid] = recorder

# 定义状态
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    query: str
    execution_id: str

# 节点函数
def init_node(state: AgentState):
    recorder = ExecutionRecorder()
    recorder.start_recording(state["query"])
    eid = recorder.current_record.execution_id
    set_recorder(eid, recorder)
    return {**state, "execution_id": eid}

def agent_node(state: AgentState):
    recorder = get_recorder(state["execution_id"])
    if recorder:
        recorder.record_step("Process query")
    return state

def tool_node(state: AgentState):
    recorder = get_recorder(state["execution_id"])
    if recorder:
        start = time.time()
        # 执行工具...
        duration = (time.time() - start) * 1000
        recorder.record_tool_call(
            tool_name="search",
            arguments={"q": state["query"]},
            result={"data": "..."},
            duration_ms=duration
        )
    return state

def final_node(state: AgentState):
    recorder = get_recorder(state["execution_id"])
    if recorder:
        execution = recorder.end_recording(
            success=True,
            final_output="Answer"
        )
    return state

# 构建图
workflow = StateGraph(AgentState)
workflow.add_node("init", init_node)
workflow.add_node("agent", agent_node)
workflow.add_node("tool", tool_node)
workflow.add_node("final", final_node)
workflow.set_entry_point("init")
workflow.add_edge("init", "agent")
workflow.add_edge("agent", "tool")
workflow.add_edge("tool", "final")
workflow.add_edge("final", END)

graph = workflow.compile()

# 执行并评估
initial_state = {
    "messages": [],
    "query": "What is AI?",
    "execution_id": ""
}

final_state = graph.invoke(initial_state)

# 获取执行数据
recorder = get_recorder(final_state["execution_id"])
execution = recorder.get_execution_history()[-1]

# 评估
evaluator = AgentEvaluator(EvaluationConfig())
expected = ExpectedResult(expected_output="AI")
result = evaluator.evaluate(execution, expected)

print(f"Overall Score: {result.overall_score:.2%}")
for metric in result.metric_scores:
    print(f"  {metric.metric_name}: {metric.score:.2%}")
```

## 使用 LangGraphEvaluator 辅助类

我们提供了 `LangGraphEvaluator` 类来简化集成：

```python
from agent_eval.examples.langgraph_integration import LangGraphEvaluator

# 创建评估器
evaluator = LangGraphEvaluator(storage_path="my_evaluations.json")

# 执行并评估
result = evaluator.execute_and_evaluate(
    graph=my_graph,
    query="What is machine learning?",
    expected_output="machine learning",
    expected_steps=3,
    expected_tools=2
)

print(f"Score: {result['overall_score']:.2%}")
print(f"Execution ID: {result['execution'].execution_id}")

# 查看历史
summary = evaluator.get_summary()
print(f"Total executions: {summary['total_executions']}")
```

## 记录的数据

系统会自动记录以下数据：

1. **查询信息**：用户输入的问题
2. **执行步骤**：每个节点的执行记录
3. **工具调用**：
   - 工具名称
   - 输入参数
   - 执行结果
   - 执行耗时
4. **最终结果**：智能体的输出
5. **执行状态**：成功/失败

## 评估指标

评估时会计算以下指标：

- **Correctness**：输出与预期的匹配度
- **StepRatio**：实际步骤与预期步骤的比率
- **ToolCallRatio**：工具调用数量与预期的比率
- **SolveRate**：任务完成成功率
- **LatencyRatio**：执行耗时与预期的比率

## 存储选项

评估结果可以保存到：

- **JSON**：`StorageType.JSON`
- **CSV**：`StorageType.CSV`
- **SQLite**：`StorageType.SQLITE`
- **PostgreSQL**：`StorageType.POSTGRES`

```python
from agent_eval import StorageConfig, StorageType

config = EvaluationConfig(
    storage_config=StorageConfig(
        storage_type=StorageType.SQLITE,
        file_path="evaluations.db"
    )
)
```

## 最佳实践

1. **始终记录工具调用**：包括输入、输出和耗时
2. **添加有意义的步骤描述**：便于后续分析
3. **使用元数据**：记录额外的上下文信息
4. **及时清理**：执行完成后清理 recorder 存储
5. **批量评估**：对于多个查询，使用 `batch_evaluate`

## 故障排除

### ExecutionRecorder 无法序列化

**问题**：LangGraph 报错无法序列化 ExecutionRecorder

**解决**：使用全局存储模式，状态中只保存 `execution_id`

### 找不到执行记录

**问题**：`get_execution_history()` 返回空

**解决**：确保在 `final_node` 中调用了 `end_recording()`

### 工具调用未记录

**问题**：工具调用数量不正确

**解决**：确保在每个工具调用前后使用 `record_tool_call()`
