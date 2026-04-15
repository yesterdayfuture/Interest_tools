# AgentEval

一个全面的 AI 智能体评估系统，支持零代码侵入式集成。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English Documentation](README.md)

## 功能特性

- **零代码侵入**: 通过装饰器集成，无需修改现有代码
- **全面指标**: 正确性、步骤比例、工具调用比例、解决率、延迟比例
- **混合评分**: 结合基于代码规则的检查和 LLM-as-Judge 评估
- **多种存储后端**: 支持 JSON、CSV、SQLite、PostgreSQL
- **理想答案生成**: 使用 LLM 生成预期执行路径，无需调用真实工具
- **详细报告**: 单条和批量评估报告，支持对比分析
- **框架无关**: 支持 LangChain、AutoGen、LangGraph 或自定义框架
- **并发执行**: 基于 ContextVars 的追踪支持并发和嵌套执行

## 快速开始

### 安装

```bash
pip install agent-eval
```

### 基础用法

```python
from agent_eval import track_agent, configure_storage, StorageConfig, StorageType

# 配置存储
configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="evaluations.json"
))

# 为智能体添加装饰器
@track_agent()
def my_agent(query: str):
    # 你的智能体逻辑
    return f"回答: {query}"

# 执行 - 自动追踪
result = my_agent("什么是人工智能？")
```

### 追踪工具和步骤

```python
from agent_eval import track_tool, track_step

@track_tool("search")
def search_api(query: str):
    return {"results": ["结果1", "结果2"]}

@track_step("parse_query")
def parse_query(query: str):
    return {"intent": "search", "keywords": query.split()}

@track_agent()
def complex_agent(query: str):
    parsed = parse_query(query)
    results = search_api(parsed["keywords"])
    return f"找到 {len(results)} 个结果"
```

## 核心组件

### 1. AgentEvaluator - 评估器

`AgentEvaluator` 是评估框架的核心协调器，集成了记录、指标计算、评分和存储功能。

```python
from agent_eval import AgentEvaluator, EvaluationConfig

# 创建评估器
config = EvaluationConfig(
    storage_type=StorageType.SQLITE,
    file_path="evaluations.db"
)
evaluator = AgentEvaluator(config)

# 记录执行
with evaluator.create_recording_context("查询天气") as rec:
    result = agent.run("查询天气")
    rec.set_output(result)

# 评估
from agent_eval.models import ExpectedResult
expected = ExpectedResult(
    query="查询天气",
    expected_steps=["解析地点", "获取数据"],
    expected_tools=["weather_api"],
    expected_output="北京今天晴天"
)
evaluation = evaluator.evaluate(expected=expected)
print(f"总体分数: {evaluation.overall_score:.2%}")
```

### 2. 装饰器

#### @track_agent() - 追踪智能体执行

```python
from agent_eval.decorators import track_agent

@track_agent(query_arg="question")
def my_agent(question: str, **kwargs):
    # 智能体逻辑
    return result

# 执行自动追踪
result = my_agent("什么是机器学习？")
```

#### @track_tool() - 追踪工具调用

```python
from agent_eval.decorators import track_tool

@track_tool("calculator")
def calculator(expression: str) -> str:
    return str(eval(expression))

@track_tool()  # 使用函数名作为工具名
def search(query: str) -> dict:
    return {"results": [...]}
```

#### @track_step() - 追踪执行步骤

```python
from agent_eval.decorators import track_step

@track_step("数据预处理")
def preprocess_data(data: dict) -> dict:
    return cleaned_data
```

### 3. 上下文管理器

使用 `TrackedExecution` 进行更细粒度的控制：

```python
from agent_eval.decorators import TrackedExecution

with TrackedExecution("复杂查询", metadata={"source": "web"}) as exec:
    # 步骤1: 解析查询
    exec.add_step("解析查询", input="北京天气", output="地点: 北京")
    
    # 步骤2: 调用工具
    exec.add_tool_call("weather_api", {"city": "北京"}, result="晴天 25°C")
    
    # 设置最终输出
    exec.set_output("北京今天晴天，25°C")
# 退出上下文后自动保存
```

### 4. 执行记录器

使用 `ExecutionRecorder` 进行手动控制：

```python
from agent_eval.recorders import ExecutionRecorder

recorder = ExecutionRecorder(storage=storage)

# 方式1: 上下文管理器
with recorder.record("查询") as record:
    result = agent.run("查询")
    record.set_output(result)

# 方式2: 手动控制
recorder.start_recording("查询")
recorder.record_step("解析查询")
result = agent.run("查询")
recorder.record_tool_call("api", {"q": "查询"}, result)
execution = recorder.end_recording(final_output=result)
```

## 高级用法

### 使用 LLM 生成理想答案

```python
from agent_eval import AgentEvaluator, EvaluationConfig, LLMConfig

config = EvaluationConfig(
    llm_config=LLMConfig(
        model="gpt-4",
        api_key="your-api-key"
    )
)

evaluator = AgentEvaluator(config)

# 生成预期执行（无需调用真实工具）
expected = evaluator.generate_and_save_expected(
    query="计算 100 + 200",
    available_tools=[
        {"name": "calculator", "description": "执行计算"}
    ]
)

print(f"预期步骤数: {expected.step_count}")
print(f"预期工具调用: {expected.tool_call_count}")
```

### 从存储中评估

```python
# 从存储加载预期和实际执行进行评估
evaluation = evaluator.evaluate_from_storage(
    query="计算 100 + 200"
)

print(f"总体分数: {evaluation.overall_score:.2%}")
for metric in evaluation.metric_scores:
    print(f"  {metric.metric_name}: {metric.score:.2%}")
```

### 批量评估

```python
# 批量评估多个执行
executions = [exec1, exec2, exec3]
expected_list = [exp1, exp2, exp3]

results = evaluator.batch_evaluate(executions, expected_list)

# 获取评估摘要
summary = evaluator.get_evaluation_summary(results)
print(f"平均分数: {summary['overall_score']['average']:.2%}")
print(f"评估数量: {summary['total_evaluations']}")
```

### 生成报告

```python
from agent_eval.reporting import EvaluationPipeline

pipeline = EvaluationPipeline(
    storage=evaluator.storage,
    evaluator=evaluator
)

# 单条评估报告
report = pipeline.evaluate_from_storage(
    query="什么是AI？",
    report_path="reports/single_eval.json"
)

# 批量评估报告
batch_report = pipeline.batch_evaluate_from_storage(
    report_path="reports/batch_eval.json"
)

print(f"平均分数: {batch_report['summary']['average_overall_score']:.2%}")
print(f"分数分布: {batch_report['summary']['score_distribution']}")
```

## 框架集成

### LangChain 集成

```python
from agent_eval.integrations import LangChainCallback
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 创建回调处理器
callback = LangChainCallback(
    agent_id="qa_bot",
    storage=storage,
    metadata={"version": "1.0"}
)

# 构建链
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个 helpful 助手。"),
    ("human", "{question}")
])
llm = ChatOpenAI(model="gpt-3.5-turbo")
chain = prompt | llm

# 执行并追踪
result = chain.invoke(
    {"question": "什么是AI？"},
    config={"callbacks": [callback]}
)

# 查看执行记录
execution = callback.get_execution()
print(f"步骤数: {execution.step_count}")
print(f"工具调用: {execution.tool_call_count}")
```

### LangGraph 集成

```python
from agent_eval.integrations import LangGraphTracer, track_langgraph
from langgraph.graph import StateGraph, END

# 方式1: 使用追踪器
workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
graph = workflow.compile()

tracer = LangGraphTracer(agent_id="qa_workflow", storage=storage)
result = tracer.run(graph, {"query": "什么是AI？"})

# 查看执行摘要
summary = tracer.get_execution_summary()
print(f"节点数: {summary['node_count']}")
print(f"步骤数: {summary['step_count']}")

# 方式2: 使用装饰器
@track_langgraph(agent_id="my_workflow", storage=storage)
def run_workflow(query: str):
    return graph.invoke({"query": query})

result = run_workflow("什么是AI？")
```

### AutoGen 集成

```python
from autogen import AssistantAgent
from agent_eval import track_agent

@track_agent()
def run_conversation(task: str):
    assistant = AssistantAgent("assistant")
    # ... 对话逻辑
    return result
```

## 评估指标

| 指标 | 描述 | 权重 |
|------|------|------|
| **Correctness** | 输出与预期的准确性对比 | 0.30 |
| **Step Ratio** | 实际步骤数与预期步骤数比例 | 0.20 |
| **Tool Call Ratio** | 实际工具调用与预期工具调用比例 | 0.20 |
| **Solve Rate** | 任务完成成功率 | 0.15 |
| **Latency Ratio** | 实际耗时与预期耗时比例 | 0.15 |

## 存储选项

```python
from agent_eval import StorageConfig, StorageType

# JSON 文件
config = StorageConfig(
    storage_type=StorageType.JSON,
    file_path="data/evaluations.json"
)

# SQLite 数据库
config = StorageConfig(
    storage_type=StorageType.SQLITE,
    file_path="data/evaluations.db"
)

# CSV 文件
config = StorageConfig(
    storage_type=StorageType.CSV,
    file_path="data/evaluations"
)
```

## 项目结构

```
agent_eval/
├── agent_eval/              # 核心包
│   ├── __init__.py          # 主要导出
│   ├── core.py              # AgentEvaluator 核心类
│   ├── models.py            # 数据模型
│   ├── metrics.py           # 评估指标
│   ├── scorers.py           # 评分机制
│   ├── generators.py        # LLM 生成器
│   ├── storages.py          # 存储后端
│   ├── decorators.py        # 装饰器集成
│   ├── tracker.py           # 执行追踪
│   ├── recorders.py         # 执行录制
│   ├── reporting.py         # 报告生成
│   ├── text_similarity.py   # 文本相似度
│   └── integrations/        # 框架集成
│       ├── __init__.py
│       ├── langchain_integration.py    # LangChain 集成
│       └── langgraph_integration.py    # LangGraph 集成
├── examples/                # 示例代码
│   ├── basic_usage.py
│   ├── decorator_example.py
│   ├── langchain_langgraph_example.py
│   └── ideal_answer_example.py
├── docs/                    # 文档
│   ├── INTEGRATION_GUIDE.md
│   ├── INTEGRATION_GUIDE_CN.md
│   ├── LANGCHAIN_LANGGRAPH_INTEGRATION.md
│   └── ARCHITECTURE.md
└── tests/                   # 测试
```

## 文档

- [Integration Guide (English)](docs/INTEGRATION_GUIDE.md)
- [集成指南 (中文)](docs/INTEGRATION_GUIDE_CN.md)
- [LangChain & LangGraph 集成](docs/LANGCHAIN_LANGGRAPH_INTEGRATION.md)
- [架构设计](docs/ARCHITECTURE.md)

## API 参考

### 核心类

- `AgentEvaluator` - 主要评估协调器
- `EvaluationConfig` - 评估配置
- `AgentExecution` - 执行数据模型
- `EvaluationResult` - 评估结果模型
- `TrackedExecution` - 追踪执行上下文
- `ExecutionRecorder` - 执行记录器

### 装饰器

- `@track_agent()` - 追踪智能体执行
- `@track_tool()` - 追踪工具调用
- `@track_step()` - 追踪执行步骤
- `@track_langgraph()` - 追踪 LangGraph 工作流

### 集成类

- `LangChainCallback` - LangChain 回调处理器
- `LangChainTracer` - LangChain 追踪器
- `LangGraphTracer` - LangGraph 追踪器

### 存储

- `JSONStorage` - JSON 文件存储
- `CSVStorage` - CSV 文件存储
- `SQLiteStorage` - SQLite 数据库存储
- `PostgresStorage` - PostgreSQL 存储（占位）

## 贡献

欢迎贡献！请随时提交 Pull Request。

## 许可证

本项目采用 MIT 许可证 - 详见 LICENSE 文件。

## 更新日志

### v0.1.0
- 初始版本
- 核心评估指标
- 基于装饰器的集成
- 多种存储后端
- 基于 LLM 的理想答案生成
- 报告生成
- LangChain 和 LangGraph 集成
- 基于 ContextVars 的并发执行追踪
