# AgentEval 集成指南

本指南演示如何以最小代码侵入的方式将 `agent-eval` 集成到您的智能体系统中。

[English Documentation](INTEGRATION_GUIDE.md)

## 目录

- [快速开始](#快速开始)
- [装饰器集成](#装饰器集成)
- [上下文管理器集成](#上下文管理器集成)
- [执行记录器](#执行记录器)
- [框架特定集成](#框架特定集成)
- [高级用法](#高级用法)

## 快速开始

### 1. 安装

```bash
pip install agent-eval
```

### 2. 基本用法

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
    # 智能体逻辑
    return result

# 完成！执行会自动追踪
result = my_agent("什么是人工智能？")
```

## 装饰器集成

### @track_agent - 追踪智能体执行

自动追踪整个智能体执行过程：

```python
from agent_eval import track_agent, get_last_execution

@track_agent(query_arg="query")
def my_chatbot(query: str, user_id: str = "anonymous"):
    # 处理查询
    response = process(query)
    return response

# 执行
result = my_chatbot("你好！")

# 获取执行数据
execution = get_last_execution()
print(f"步骤数: {execution.step_count}")
print(f"耗时: {execution.total_duration_ms}ms")
```

### @track_tool - 追踪工具调用

追踪单个工具执行：

```python
from agent_eval import track_tool

@track_tool(tool_name="search")
def search_api(query: str):
    # 搜索逻辑
    return results

@track_tool(tool_name="calculator")
def calculate(expression: str):
    # 计算逻辑
    return result

# 在智能体中使用
@track_agent()
def my_agent(query: str):
    if "搜索" in query:
        return search_api(query)
    elif "计算" in query:
        return calculate(query)
```

### @track_step - 追踪执行步骤

追踪智能体中的特定步骤：

```python
from agent_eval import track_step, track_agent

@track_agent()
def complex_agent(query: str):
    # 步骤1: 解析
    parsed = parse_query(query)
    
    # 步骤2: 检索
    info = retrieve_info(parsed)
    
    # 步骤3: 生成
    answer = generate_response(info)
    
    return answer

@track_step("解析查询")
def parse_query(query: str):
    return {"intent": "search", "keywords": query.split()}

@track_step("检索信息")
def retrieve_info(parsed: dict):
    return database.search(parsed["keywords"])

@track_step("生成回答")
def generate_response(info: list):
    return llm.generate(info)
```

### 并发和嵌套执行支持

AgentEval 使用 ContextVars 进行线程安全追踪，支持并发和嵌套执行：

```python
import asyncio
from agent_eval import track_agent, track_tool

@track_tool("api_call")
async def api_call(endpoint: str):
    await asyncio.sleep(0.1)
    return f"来自 {endpoint} 的结果"

@track_agent()
async def async_agent(query: str):
    # 并发工具调用
    results = await asyncio.gather(
        api_call("/api/1"),
        api_call("/api/2"),
        api_call("/api/3")
    )
    return results

# 并发执行多个智能体
async def main():
    agents = [
        async_agent(f"查询 {i}")
        for i in range(5)
    ]
    results = await asyncio.gather(*agents)
    return results

asyncio.run(main())
```

## 上下文管理器集成

需要更多控制时，使用上下文管理器：

```python
from agent_eval.decorators import TrackedExecution

def my_agent(query: str):
    with TrackedExecution(query, metadata={"source": "web"}) as exec:
        # 添加自定义步骤
        exec.add_step("理解查询", step_input=query)
        
        # 处理
        result = process(query)
        
        # 添加工具调用
        exec.add_tool_call(
            tool_name="search",
            tool_input={"q": query},
            tool_output=result,
            duration_ms=150
        )
        
        # 设置最终输出
        exec.set_output(result)
        
        return result
```

### 获取当前执行上下文

在嵌套函数中访问当前执行上下文：

```python
from agent_eval.decorators import get_current_execution, get_current_execution_id

@track_agent()
def my_agent(query: str):
    execution = get_current_execution()
    exec_id = get_current_execution_id()
    
    if execution:
        print(f"当前查询: {execution.query}")
        print(f"执行ID: {exec_id}")
    
    # 带上下文感知的处理
    result = process(query)
    return result
```

## 执行记录器

手动控制执行记录：

```python
from agent_eval.recorders import ExecutionRecorder

# 创建记录器
recorder = ExecutionRecorder(storage=storage, auto_save=True)

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

## 框架特定集成

### LangChain 集成

#### 方式1: 使用回调处理器

```python
from agent_eval.integrations import LangChainCallback
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 创建回调
callback = LangChainCallback(
    agent_id="my_agent",
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

# 获取执行
execution = callback.get_execution()
print(f"步骤数: {execution.step_count}")
print(f"工具调用: {execution.tool_call_count}")
```

#### 方式2: 使用追踪器

```python
from agent_eval.integrations import LangChainTracer

# 创建追踪器
tracer = LangChainTracer(
    agent_id="my_bot",
    storage=storage
)

# 追踪执行
result = tracer.trace(chain, {"question": "什么是AI？"})

# 获取执行
execution = tracer.get_last_execution()
```

#### 带工具的 Agent

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """搜索信息"""
    return f"搜索结果: {query}"

# 创建回调
callback = LangChainCallback(agent_id="tool_agent")

# 创建并执行 Agent
agent = create_openai_tools_agent(llm, [search], prompt)
agent_executor = AgentExecutor(agent=agent, tools=[search])

result = agent_executor.invoke(
    {"input": "搜索人工智能"},
    config={"callbacks": [callback]}
)

# 查看工具调用
execution = callback.get_execution()
for tool_call in execution.tool_calls_detail:
    print(f"{tool_call.name}: {tool_call.input}")
```

### LangGraph 集成

#### 方式1: 使用追踪器

```python
from agent_eval.integrations import LangGraphTracer
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    query: str
    answer: str

# 定义节点
def retrieve(state: State) -> State:
    return {"query": state["query"], "context": "..."}

def generate(state: State) -> State:
    return {"answer": f"答案: {state['query']}"}

# 构建图
workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
graph = workflow.compile()

# 使用追踪器
tracer = LangGraphTracer(agent_id="qa_workflow", storage=storage)
result = tracer.run(graph, {"query": "什么是AI？"})

# 查看摘要
summary = tracer.get_execution_summary()
print(f"节点数: {summary['node_count']}")
print(f"边数: {summary['edge_count']}")
for node in summary['nodes']:
    print(f"  - {node['name']}: {node['success']}")
```

#### 方式2: 使用装饰器

```python
from agent_eval.integrations import track_langgraph

@track_langgraph(agent_id="my_workflow", storage=storage)
def run_workflow(query: str):
    return graph.invoke({"query": query})

result = run_workflow("什么是AI？")

# 获取执行
from agent_eval.decorators import get_current_execution
execution = get_current_execution()
```

### AutoGen 集成

```python
from autogen import AssistantAgent, UserProxyAgent
from agent_eval import track_agent, track_tool

# 追踪 AutoGen 智能体执行
@track_agent()
def run_autogen_conversation(task: str):
    assistant = AssistantAgent("assistant")
    user_proxy = UserProxyAgent("user_proxy")
    
    user_proxy.initiate_chat(assistant, message=task)
    return "对话完成"
```

### 自定义框架

```python
class MyAgent:
    def __init__(self):
        self.tools = []
    
    @track_agent(query_arg="query")
    def run(self, query: str):
        # 智能体逻辑
        for tool in self.tools:
            if tool.can_handle(query):
                return tool.execute(query)
        return "无可用工具"
    
    @track_tool()
    def add_tool(self, tool):
        self.tools.append(tool)
```

## 高级用法

### 自定义存储配置

```python
from agent_eval import configure_storage, StorageConfig, StorageType

# JSON 存储
configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="data/evaluations.json"
))

# SQLite 存储
configure_storage(StorageConfig(
    storage_type=StorageType.SQLITE,
    file_path="data/evaluations.db"
))

# CSV 存储
configure_storage(StorageConfig(
    storage_type=StorageType.CSV,
    file_path="data/evaluations"
))
```

### 批量执行追踪

```python
from agent_eval import track_agent, list_executions

@track_agent()
def batch_process(queries: list):
    results = []
    for query in queries:
        result = process(query)
        results.append(result)
    return results

# 执行批量
queries = ["问题1", "问题2", "问题3"]
batch_process(queries)

# 获取所有执行
executions = list_executions()
print(f"总执行数: {len(executions)}")
```

### 错误追踪

```python
from agent_eval import track_agent, get_last_execution

@track_agent()
def error_prone_agent(query: str):
    if "错误" in query:
        raise ValueError("出错了！")
    return "成功"

try:
    error_prone_agent("触发错误")
except ValueError:
    pass

# 检查执行中的错误
execution = get_last_execution()
print(f"成功: {execution.success}")
print(f"有错误: {execution.has_error}")
print(f"错误信息: {execution.error_message}")
```

### 与评估集成

```python
from agent_eval import (
    track_agent, 
    AgentEvaluator, 
    EvaluationConfig,
    LLMConfig
)

# 追踪执行
@track_agent()
def my_agent(query: str):
    return f"回答: {query}"

result = my_agent("什么是人工智能？")

# 评估
config = EvaluationConfig(
    llm_config=LLMConfig(api_key="your-key", model="gpt-4")
)
evaluator = AgentEvaluator(config)

# 获取执行并评估
from agent_eval import get_last_execution
execution = get_last_execution()
evaluation = evaluator.evaluate(execution)

print(f"总分: {evaluation.overall_score:.2%}")
```

## 最佳实践

1. **对主入口使用 @track_agent**：包装您的主智能体函数
2. **对外部调用使用 @track_tool**：追踪 API 调用、数据库查询等
3. **对复杂逻辑使用 @track_step**：将复杂智能体分解为步骤
4. **尽早配置存储**：在运行智能体前设置存储
5. **优雅处理错误**：错误会自动追踪
6. **使用上下文管理器进行细粒度控制**：当您需要手动添加步骤或工具调用时
7. **利用并发执行支持**：使用 async/await 获得更好的性能

## 故障排除

### 问题：装饰器未追踪

确保在使用装饰器前调用 `configure_storage()`：

```python
from agent_eval import configure_storage, StorageConfig

configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="evaluations.json"
))
```

### 问题：缺少执行数据

检查查询参数名称是否匹配：

```python
# 如果函数使用 'input' 而非 'query'
@track_agent(query_arg="input")
def my_agent(input: str):
    return result
```

### 问题：工具调用未追踪

确保在活动智能体执行中调用工具：

```python
@track_agent()
def agent(query: str):
    # 这里的工具调用会被追踪
    return tool_call(query)
```

### 问题：并发执行冲突

AgentEval 使用 ContextVars 进行线程安全追踪。每个执行都有自己的独立上下文：

```python
import asyncio
from agent_eval import track_agent

@track_agent()
async def async_agent(query: str):
    return process(query)

# 每个执行都有自己的上下文
async def main():
    await asyncio.gather(
        async_agent("查询 1"),
        async_agent("查询 2"),
        async_agent("查询 3")
    )
```
