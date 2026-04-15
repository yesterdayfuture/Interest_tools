# LangChain and LangGraph Integration Guide

AgentEval provides seamless integration with LangChain and LangGraph, enabling automatic tracking of chain, agent, and graph execution.

[中文文档](#langchain-和-langgraph-集成指南)

---

## Installation

```bash
# Base installation
pip install agent-eval

# Install LangChain integration
pip install langchain langchain-openai

# Install LangGraph integration
pip install langgraph
```

## LangChain Integration

### Method 1: Using Callback Handler

```python
from agent_eval.integrations import LangChainCallback
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Create callback handler
callback = LangChainCallback(
    agent_id="my_agent",
    metadata={"version": "1.0"}
)

# Build chain
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{question}")
])
llm = ChatOpenAI(model="gpt-3.5-turbo")
chain = prompt | llm

# Execute and track
result = chain.invoke(
    {"question": "What is AI?"},
    config={"callbacks": [callback]}
)

# Get execution record
execution = callback.get_execution()
print(f"Steps: {execution.step_count}")
print(f"Tool calls: {execution.tool_call_count}")
```

### Method 2: Using Tracer

```python
from agent_eval.integrations import LangChainTracer

# Create tracer
tracer = LangChainTracer(agent_id="my_bot")

# Track execution
result = tracer.trace(chain, {"question": "What is AI?"})

# Get execution record
execution = tracer.get_last_execution()
```

### Agent with Tools

```python
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search for information"""
    return f"Search results: {query}"

# Create callback
callback = LangChainCallback(agent_id="tool_agent")

# Create and execute agent
agent = create_openai_tools_agent(llm, [search], prompt)
agent_executor = AgentExecutor(agent=agent, tools=[search])

result = agent_executor.invoke(
    {"input": "Search for AI"},
    config={"callbacks": [callback]}
)

# View tool call records
execution = callback.get_execution()
for tool_call in execution.tool_calls_detail:
    print(f"{tool_call.name}: {tool_call.input}")
```

## LangGraph Integration

### Method 1: Using Tracer

```python
from agent_eval.integrations import LangGraphTracer
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    query: str
    answer: str

# Define nodes
def retrieve(state: State) -> State:
    return {"query": state["query"], "context": "..."}

def generate(state: State) -> State:
    return {"answer": f"Answer: {state['query']}"}

# Build graph
workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
graph = workflow.compile()

# Use tracer
tracer = LangGraphTracer(agent_id="qa_workflow")
result = tracer.run(graph, {"query": "What is AI?"})

# View execution summary
summary = tracer.get_execution_summary()
print(f"Nodes: {summary['node_count']}")
print(f"Edges: {summary['edge_count']}")
for node in summary['nodes']:
    print(f"  - {node['name']}: {node['success']}")
```

### Method 2: Using Decorator

```python
from agent_eval.integrations import track_langgraph

@track_langgraph(agent_id="my_workflow")
def run_workflow(query: str):
    return graph.invoke({"query": query})

result = run_workflow("What is AI?")

# Get execution record
from agent_eval.decorators import get_current_execution
execution = get_current_execution()
```

### Record Fine-grained Steps in Nodes

```python
from agent_eval.integrations.langgraph_integration import LangGraphCallback

def complex_node(state: State) -> State:
    # Get callback
    callback = LangGraphCallback()
    
    # Record step 1
    callback.on_step_start("parse", state["query"])
    parsed = parse_query(state["query"])
    callback.on_step_end("parse", parsed)
    
    # Record step 2
    callback.on_step_start("process", parsed)
    result = process(parsed)
    callback.on_step_end("process", result)
    
    # Record tool call
    callback.on_tool_call("search", {"query": state["query"]}, "result")
    
    return {"result": result}
```

## Get Current Execution Context

During LangChain/LangGraph execution, you can get the current execution context:

```python
from agent_eval.decorators import get_current_execution, get_current_execution_id

# Get current execution in node or tool
def my_node(state):
    execution = get_current_execution()
    exec_id = get_current_execution_id()
    
    if execution:
        print(f"Current query: {execution.query}")
        print(f"Execution ID: {exec_id}")
    
    return state
```

## Execution Record Structure

LangChain/LangGraph execution records contain the following information:

```python
{
    "execution_id": "uuid",
    "query": "User query",
    "agent_id": "Agent ID",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-01T00:00:05",
    "status": "completed",
    "steps_detail": [
        {
            "step": 1,
            "description": "chain:LLMChain",
            "input": {...},
            "output": {...},
            "success": True
        },
        {
            "step": 2,
            "description": "node:retrieve",
            "input": {...},
            "output": {...},
            "success": True
        }
    ],
    "tool_calls_detail": [
        {
            "name": "search",
            "input": {"query": "..."},
            "output": "...",
            "success": True
        }
    ],
    "metadata": {
        "framework": "langchain",  # or "langgraph"
        "llm_calls": [...],
        "edges": [...]  # LangGraph specific
    }
}
```

## Complete Example

See `examples/langchain_langgraph_example.py` for complete example code:

```bash
python examples/langchain_langgraph_example.py
```

Examples include:
1. LangChain basic tracking
2. LangChain agent with tools
3. LangGraph workflow tracking
4. LangGraph decorator usage
5. Fine-grained step recording in nodes

---

# LangChain 和 LangGraph 集成指南

AgentEval 提供与 LangChain 和 LangGraph 的无缝集成，可以自动追踪链、Agent 和图的执行过程。

[English Documentation](#langchain-and-langgraph-integration-guide)

---

## 安装

```bash
# 基础安装
pip install agent-eval

# 安装 LangChain 集成
pip install langchain langchain-openai

# 安装 LangGraph 集成
pip install langgraph
```

## LangChain 集成

### 方式1：使用回调处理器

```python
from agent_eval.integrations import LangChainCallback
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 创建回调处理器
callback = LangChainCallback(
    agent_id="my_agent",
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

# 获取执行记录
execution = callback.get_execution()
print(f"步骤数: {execution.step_count}")
print(f"工具调用: {execution.tool_call_count}")
```

### 方式2：使用追踪器

```python
from agent_eval.integrations import LangChainTracer

# 创建追踪器
tracer = LangChainTracer(agent_id="my_bot")

# 追踪执行
result = tracer.trace(chain, {"question": "什么是AI？"})

# 获取执行记录
execution = tracer.get_last_execution()
```

### 带工具的 Agent

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

# 查看工具调用记录
execution = callback.get_execution()
for tool_call in execution.tool_calls_detail:
    print(f"{tool_call.name}: {tool_call.input}")
```

## LangGraph 集成

### 方式1：使用追踪器

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
tracer = LangGraphTracer(agent_id="qa_workflow")
result = tracer.run(graph, {"query": "什么是AI？"})

# 查看执行摘要
summary = tracer.get_execution_summary()
print(f"节点数: {summary['node_count']}")
print(f"边数: {summary['edge_count']}")
for node in summary['nodes']:
    print(f"  - {node['name']}: {node['success']}")
```

### 方式2：使用装饰器

```python
from agent_eval.integrations import track_langgraph

@track_langgraph(agent_id="my_workflow")
def run_workflow(query: str):
    return graph.invoke({"query": query})

result = run_workflow("什么是AI？")

# 获取执行记录
from agent_eval.decorators import get_current_execution
execution = get_current_execution()
```

### 在节点中记录细粒度步骤

```python
from agent_eval.integrations.langgraph_integration import LangGraphCallback

def complex_node(state: State) -> State:
    # 获取回调
    callback = LangGraphCallback()
    
    # 记录步骤1
    callback.on_step_start("parse", state["query"])
    parsed = parse_query(state["query"])
    callback.on_step_end("parse", parsed)
    
    # 记录步骤2
    callback.on_step_start("process", parsed)
    result = process(parsed)
    callback.on_step_end("process", result)
    
    # 记录工具调用
    callback.on_tool_call("search", {"query": state["query"]}, "结果")
    
    return {"result": result}
```

## 获取当前执行上下文

在 LangChain/LangGraph 执行过程中，可以获取当前执行上下文：

```python
from agent_eval.decorators import get_current_execution, get_current_execution_id

# 在节点或工具中获取当前执行
def my_node(state):
    execution = get_current_execution()
    exec_id = get_current_execution_id()
    
    if execution:
        print(f"当前查询: {execution.query}")
        print(f"执行ID: {exec_id}")
    
    return state
```

## 执行记录结构

LangChain/LangGraph 的执行记录包含以下信息：

```python
{
    "execution_id": "uuid",
    "query": "用户查询",
    "agent_id": "智能体ID",
    "start_time": "2024-01-01T00:00:00",
    "end_time": "2024-01-01T00:00:05",
    "status": "completed",
    "steps_detail": [
        {
            "step": 1,
            "description": "chain:LLMChain",
            "input": {...},
            "output": {...},
            "success": True
        },
        {
            "step": 2,
            "description": "node:retrieve",
            "input": {...},
            "output": {...},
            "success": True
        }
    ],
    "tool_calls_detail": [
        {
            "name": "search",
            "input": {"query": "..."},
            "output": "...",
            "success": True
        }
    ],
    "metadata": {
        "framework": "langchain",  # 或 "langgraph"
        "llm_calls": [...],
        "edges": [...]  # LangGraph 特有
    }
}
```

## 完整示例

查看 `examples/langchain_langgraph_example.py` 获取完整示例代码：

```bash
python examples/langchain_langgraph_example.py
```

示例包含：
1. LangChain 基础追踪
2. LangChain 带工具的 Agent
3. LangGraph 工作流追踪
4. LangGraph 装饰器使用
5. 节点内细粒度步骤记录
