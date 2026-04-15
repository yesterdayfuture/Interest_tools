# Agent Eval 集成指南

本指南介绍如何将 agent-eval 集成到您的智能体项目中，以最小代码侵入的方式收集运行信息。

## 目录

1. [数据模型](#数据模型)
2. [集成方式](#集成方式)
3. [存储配置](#存储配置)
4. [评估执行](#评估执行)
5. [完整示例](#完整示例)

## 数据模型

### AgentExecution - 一次问答的完整记录

每个问答会话存储为一条 `AgentExecution` 记录，包含：

```python
{
    "execution_id": "唯一标识符",
    "query": "用户输入",
    
    # 执行步骤摘要 - 格式: "第1步执行xxx\n第2步执行yyy"
    "steps_summary": "第1步执行理解查询\n第2步执行检索信息\n第3步执行生成回答",
    
    # 执行步骤详细信息
    "steps_detail": [
        {
            "step": 1,
            "description": "理解查询",
            "input": "用户输入",
            "output": "解析结果",
            "time": 10.5,  # 耗时(毫秒)
            "success": true,
            "err_msg": null
        }
    ],
    
    # 工具调用信息
    "tool_call_count": 2,
    "tool_calls_detail": [
        {
            "name": "search_tool",
            "input": {"query": "..."},
            "output": {"results": [...]},
            "time": 25.0,
            "success": true,
            "err_msg": null
        }
    ],
    
    # 执行结果
    "step_count": 3,
    "final_output": "最终输出",
    "success": true,
    "has_error": false,
    "error_message": null,
    
    # 时间信息
    "total_duration_ms": 100.5,
    "start_time": "2024-01-01T10:00:00",
    "end_time": "2024-01-01T10:00:01"
}
```

## 集成方式

### 方式1: SimpleTracker - 最简单的方式

适用于快速集成，代码侵入最小。

```python
from agent_eval import SimpleTracker

# 创建 tracker
tracker = SimpleTracker()

# 使用上下文管理器
with tracker.start("用户问题"):
    # 记录步骤
    tracker.step("分析查询", step_input="用户输入")
    
    # 记录工具调用
    tracker.tool_call(
        tool_name="search",
        tool_input={"query": "关键词"},
        tool_output={"results": [...]},
        duration_ms=25.5
    )
    
    # 执行您的智能体逻辑
    result = your_agent.run("用户问题")
    
    # 记录结果
    tracker.record_result(result)

# 获取执行记录
execution = tracker.get_execution()
```

### 方式2: ExecutionTracker - 完整控制

适用于需要精细控制的场景。

```python
from agent_eval import ExecutionTracker

tracker = ExecutionTracker()

# 开始追踪
tracker.start("用户问题")

# 添加步骤
tracker.add_step(
    description="理解查询",
    step_input="用户输入",
    step_output="解析结果"
)

# 添加工具调用
tracker.add_tool_call(
    tool_name="search_tool",
    tool_input={"query": "关键词"},
    tool_output={"results": [...]},
    duration_ms=25.0
)

# 设置最终结果
tracker.set_final_output("最终回答")

# 结束追踪
execution = tracker.finish(success=True)
```

### 方式3: 上下文管理器 - 自动错误处理

```python
from agent_eval import ExecutionTracker

tracker = ExecutionTracker()

try:
    with tracker.track("用户问题") as exec:
        # 您的智能体逻辑
        exec.add_step("步骤1")
        result = your_agent.process("用户问题")
        exec.set_final_output(result)
        
except Exception as e:
    # 错误会自动记录到 execution 中
    print(f"执行失败: {e}")

execution = tracker.execution
```

### 方式4: 装饰器 - 零代码修改

适用于不想修改现有智能体代码的场景。

```python
from agent_eval import ExecutionTracker

tracker = ExecutionTracker()

@tracker.wrap
def your_existing_agent(query: str) -> str:
    """您的现有智能体函数 - 无需修改"""
    # 智能体逻辑
    return result

# 调用方式不变，返回 (result, execution)
result, execution = your_existing_agent("用户问题")
```

### 方式5: 全局 Tracker - 便捷函数

```python
from agent_eval import track, get_last_execution

# 使用全局 tracker
with track("用户问题") as t:
    t.add_step("步骤1")
    t.add_tool_call("tool1", {"arg": "value"})
    t.set_final_output("结果")

# 获取最后一次执行
execution = get_last_execution()
```

## 存储配置

### JSON 存储

```python
from agent_eval import StorageConfig, StorageType

config = StorageConfig(
    storage_type=StorageType.JSON,
    file_path="data/executions.json"
)
```

### CSV 存储

```python
config = StorageConfig(
    storage_type=StorageType.CSV,
    file_path="data/executions.csv"
)
```

### SQLite 存储

```python
config = StorageConfig(
    storage_type=StorageType.SQLITE,
    file_path="data/executions.db"
)
```

### 自动保存执行记录

```python
from agent_eval import ExecutionTracker, create_storage

# 创建存储
storage = create_storage(config)

# 创建带自动保存的 tracker
tracker = ExecutionTracker()

# 手动保存
execution = tracker.finish(success=True)
storage.save_execution(execution)
```

## 评估执行

### 基本评估

```python
from agent_eval import AgentEvaluator, EvaluationConfig, ExpectedResult

# 配置评估器
config = EvaluationConfig(
    use_code_scorer=True,
    use_llm_scorer=False
)
evaluator = AgentEvaluator(config)

# 定义预期结果
expected = ExpectedResult(
    expected_output="预期输出",
    expected_steps=["步骤1", "步骤2", "步骤3"],
    expected_tool_count=2,
    expected_tool_calls=["tool1", "tool2"]
)

# 评估
result = evaluator.evaluate(execution, expected)

print(f"总体得分: {result.overall_score:.2%}")
for metric in result.metric_scores:
    print(f"{metric.metric_name}: {metric.score:.2%}")
```

### 保存评估结果

```python
from agent_eval import StorageConfig, StorageType

config = EvaluationConfig(
    use_code_scorer=True,
    storage_config=StorageConfig(
        storage_type=StorageType.JSON,
        file_path="evaluations.json"
    )
)

evaluator = AgentEvaluator(config)
result = evaluator.evaluate(execution, expected, save_result=True)
```

## 完整示例

### 示例1: 基础智能体集成

```python
import time
from agent_eval import (
    SimpleTracker, AgentEvaluator, EvaluationConfig,
    ExpectedResult, StorageConfig, StorageType
)

class MyAgent:
    def run(self, query: str) -> str:
        # 模拟智能体执行
        time.sleep(0.1)
        return f"Answer to: {query}"

# 集成代码
agent = MyAgent()
tracker = SimpleTracker()

with tracker.start("What is AI?"):
    tracker.step("分析查询")
    
    tracker.tool_call(
        tool_name="knowledge_base",
        tool_input={"query": "AI"},
        tool_output={"info": "..."},
        duration_ms=50.0
    )
    
    result = agent.run("What is AI?")
    tracker.record_result(result)

execution = tracker.get_execution()

# 评估
config = EvaluationConfig(
    use_code_scorer=True,
    storage_config=StorageConfig(
        storage_type=StorageType.JSON,
        file_path="results.json"
    )
)
evaluator = AgentEvaluator(config)

expected = ExpectedResult(
    expected_output="AI is...",
    expected_steps=["分析查询", "检索信息", "生成回答"],
    expected_tool_count=1
)

evaluation = evaluator.evaluate(execution, expected, save_result=True)
print(f"得分: {evaluation.overall_score:.2%}")
```

### 示例2: LangGraph 集成

```python
from agent_eval import ExecutionTracker
from langgraph.graph import StateGraph

# 全局 tracker 存储
_tracker_store = {}

def get_tracker(thread_id: str) -> ExecutionTracker:
    if thread_id not in _tracker_store:
        _tracker_store[thread_id] = ExecutionTracker()
    return _tracker_store[thread_id]

# 定义节点
def agent_node(state):
    tracker = get_tracker(state.get("thread_id", "default"))
    
    # 开始追踪（只在第一个节点）
    if not tracker.execution:
        tracker.start(state["query"])
    
    # 记录步骤
    tracker.add_step("Agent processing", step_input=state["query"])
    
    # 智能体逻辑
    result = process_query(state["query"])
    
    return {"result": result}

def tool_node(state):
    tracker = get_tracker(state.get("thread_id", "default"))
    
    # 记录工具调用
    start = time.time()
    tool_result = call_tool(state["tool_name"], state["tool_input"])
    duration = (time.time() - start) * 1000
    
    tracker.add_tool_call(
        tool_name=state["tool_name"],
        tool_input=state["tool_input"],
        tool_output=tool_result,
        duration_ms=duration
    )
    
    return {"tool_result": tool_result}

# 构建图
builder = StateGraph(dict)
builder.add_node("agent", agent_node)
builder.add_node("tool", tool_node)
builder.set_entry_point("agent")

# 执行
graph = builder.compile()
result = graph.invoke({"query": "用户问题", "thread_id": "thread_1"})

# 获取执行记录
tracker = get_tracker("thread_1")
tracker.set_final_output(result.get("result"))
execution = tracker.finish(success=True)
```

### 示例3: 批量评估

```python
from agent_eval import AgentEvaluator, EvaluationConfig

# 准备测试用例
test_cases = [
    {
        "query": "问题1",
        "expected_output": "答案1",
        "expected_steps": ["步骤1", "步骤2"]
    },
    {
        "query": "问题2",
        "expected_output": "答案2",
        "expected_steps": ["步骤1", "步骤2", "步骤3"]
    }
]

# 批量评估
config = EvaluationConfig(use_code_scorer=True)
evaluator = AgentEvaluator(config)

results = []
for case in test_cases:
    # 执行并记录
    tracker = SimpleTracker()
    with tracker.start(case["query"]):
        result = your_agent.run(case["query"])
        tracker.record_result(result)
    
    execution = tracker.get_execution()
    
    # 评估
    expected = ExpectedResult(
        expected_output=case["expected_output"],
        expected_steps=case["expected_steps"]
    )
    
    eval_result = evaluator.evaluate(execution, expected)
    results.append({
        "query": case["query"],
        "score": eval_result.overall_score,
        "metrics": eval_result.metric_scores
    })

# 汇总结果
avg_score = sum(r["score"] for r in results) / len(results)
print(f"平均得分: {avg_score:.2%}")
```

## 最佳实践

1. **选择合适的 Tracker**: 
   - 快速集成用 `SimpleTracker`
   - 精细控制用 `ExecutionTracker`
   - 不修改代码用装饰器

2. **记录完整信息**:
   - 每个步骤都记录 input/output
   - 工具调用记录耗时
   - 错误信息详细记录

3. **存储选择**:
   - 开发测试用 JSON
   - 数据分析用 CSV
   - 生产环境用 SQLite/PostgreSQL

4. **评估策略**:
   - 先用 Code-based Scorer 快速筛选
   - 再用 LLM-as-Judge 精细评估

## 故障排除

### 问题: 步骤时间显示为 None

解决: 确保调用 `add_step` 时 tracker 已启动

```python
tracker.start("query")  # 必须先启动
# 然后才能添加步骤
tracker.add_step("步骤")
```

### 问题: 存储失败

解决: 检查存储路径是否存在

```python
from pathlib import Path
Path("data").mkdir(parents=True, exist_ok=True)
```

### 问题: 评估得分异常

解决: 检查 expected 和 actual 数据格式

```python
print(f"Execution: {execution.model_dump_json(indent=2)}")
print(f"Expected: {expected.model_dump_json(indent=2)}")
```
