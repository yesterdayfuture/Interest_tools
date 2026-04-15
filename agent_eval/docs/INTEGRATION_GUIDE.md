# AgentEval Integration Guide

This guide demonstrates how to integrate `agent-eval` into your agent system with minimal code changes.

[中文文档](INTEGRATION_GUIDE_CN.md)

## Table of Contents

- [Quick Start](#quick-start)
- [Decorator-Based Integration](#decorator-based-integration)
- [Context Manager Integration](#context-manager-integration)
- [Execution Recorder](#execution-recorder)
- [Framework-Specific Integration](#framework-specific-integration)
- [Advanced Usage](#advanced-usage)

## Quick Start

### 1. Installation

```bash
pip install agent-eval
```

### 2. Basic Usage

```python
from agent_eval import track_agent, configure_storage, StorageConfig, StorageType

# Configure storage
configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="evaluations.json"
))

# Add decorator to your agent
@track_agent()
def my_agent(query: str):
    # Your agent logic
    return result

# That's it! Execution is automatically tracked
result = my_agent("What is AI?")
```

## Decorator-Based Integration

### @track_agent - Track Agent Execution

Automatically track the entire agent execution:

```python
from agent_eval import track_agent, get_last_execution

@track_agent(query_arg="query")
def my_chatbot(query: str, user_id: str = "anonymous"):
    # Process query
    response = process(query)
    return response

# Execute
result = my_chatbot("Hello!")

# Get execution data
execution = get_last_execution()
print(f"Steps: {execution.step_count}")
print(f"Duration: {execution.total_duration_ms}ms")
```

### @track_tool - Track Tool Calls

Track individual tool executions:

```python
from agent_eval import track_tool

@track_tool(tool_name="search")
def search_api(query: str):
    # Search logic
    return results

@track_tool(tool_name="calculator")
def calculate(expression: str):
    # Calculation logic
    return result

# Use in your agent
@track_agent()
def my_agent(query: str):
    if "search" in query:
        return search_api(query)
    elif "calculate" in query:
        return calculate(query)
```

### @track_step - Track Execution Steps

Track specific steps in your agent:

```python
from agent_eval import track_step, track_agent

@track_agent()
def complex_agent(query: str):
    # Step 1: Parse
    parsed = parse_query(query)
    
    # Step 2: Retrieve
    info = retrieve_info(parsed)
    
    # Step 3: Generate
    answer = generate_response(info)
    
    return answer

@track_step("parse_query")
def parse_query(query: str):
    return {"intent": "search", "keywords": query.split()}

@track_step("retrieve_info")
def retrieve_info(parsed: dict):
    return database.search(parsed["keywords"])

@track_step("generate_response")
def generate_response(info: list):
    return llm.generate(info)
```

### Concurrent and Nested Execution Support

AgentEval uses ContextVars for thread-safe tracking, supporting concurrent and nested executions:

```python
import asyncio
from agent_eval import track_agent, track_tool

@track_tool("api_call")
async def api_call(endpoint: str):
    await asyncio.sleep(0.1)
    return f"Result from {endpoint}"

@track_agent()
async def async_agent(query: str):
    # Concurrent tool calls
    results = await asyncio.gather(
        api_call("/api/1"),
        api_call("/api/2"),
        api_call("/api/3")
    )
    return results

# Execute multiple agents concurrently
async def main():
    agents = [
        async_agent(f"Query {i}")
        for i in range(5)
    ]
    results = await asyncio.gather(*agents)
    return results

asyncio.run(main())
```

## Context Manager Integration

For more control, use the context manager:

```python
from agent_eval.decorators import TrackedExecution

def my_agent(query: str):
    with TrackedExecution(query, metadata={"source": "web"}) as exec:
        # Add custom steps
        exec.add_step("Understanding query", step_input=query)
        
        # Process
        result = process(query)
        
        # Add tool call
        exec.add_tool_call(
            tool_name="search",
            tool_input={"q": query},
            tool_output=result,
            duration_ms=150
        )
        
        # Set final output
        exec.set_output(result)
        
        return result
```

### Get Current Execution Context

Access the current execution context within nested functions:

```python
from agent_eval.decorators import get_current_execution, get_current_execution_id

@track_agent()
def my_agent(query: str):
    execution = get_current_execution()
    exec_id = get_current_execution_id()
    
    if execution:
        print(f"Current query: {execution.query}")
        print(f"Execution ID: {exec_id}")
    
    # Process with context awareness
    result = process(query)
    return result
```

## Execution Recorder

For manual control over execution recording:

```python
from agent_eval.recorders import ExecutionRecorder

# Create recorder
recorder = ExecutionRecorder(storage=storage, auto_save=True)

# Method 1: Context manager
with recorder.record("Query") as record:
    result = agent.run("Query")
    record.set_output(result)

# Method 2: Manual control
recorder.start_recording("Query")
recorder.record_step("Parse query")
result = agent.run("Query")
recorder.record_tool_call("api", {"q": "Query"}, result)
execution = recorder.end_recording(final_output=result)
```

## Framework-Specific Integration

### LangChain Integration

#### Method 1: Using Callback Handler

```python
from agent_eval.integrations import LangChainCallback
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Create callback
callback = LangChainCallback(
    agent_id="my_agent",
    storage=storage,
    metadata={"version": "1.0"}
)

# Build chain
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "{question}")
])
llm = ChatOpenAI(model="gpt-3.5-turbo")
chain = prompt | llm

# Execute with tracking
result = chain.invoke(
    {"question": "What is AI?"},
    config={"callbacks": [callback]}
)

# Get execution
execution = callback.get_execution()
print(f"Steps: {execution.step_count}")
print(f"Tool calls: {execution.tool_call_count}")
```

#### Method 2: Using Tracer

```python
from agent_eval.integrations import LangChainTracer

# Create tracer
tracer = LangChainTracer(
    agent_id="my_bot",
    storage=storage
)

# Trace execution
result = tracer.trace(chain, {"question": "What is AI?"})

# Get execution
execution = tracer.get_last_execution()
```

#### Agent with Tools

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

# View tool calls
execution = callback.get_execution()
for tool_call in execution.tool_calls_detail:
    print(f"{tool_call.name}: {tool_call.input}")
```

### LangGraph Integration

#### Method 1: Using Tracer

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
tracer = LangGraphTracer(agent_id="qa_workflow", storage=storage)
result = tracer.run(graph, {"query": "What is AI?"})

# View summary
summary = tracer.get_execution_summary()
print(f"Nodes: {summary['node_count']}")
print(f"Edges: {summary['edge_count']}")
for node in summary['nodes']:
    print(f"  - {node['name']}: {node['success']}")
```

#### Method 2: Using Decorator

```python
from agent_eval.integrations import track_langgraph

@track_langgraph(agent_id="my_workflow", storage=storage)
def run_workflow(query: str):
    return graph.invoke({"query": query})

result = run_workflow("What is AI?")

# Get execution
from agent_eval.decorators import get_current_execution
execution = get_current_execution()
```

### AutoGen Integration

```python
from autogen import AssistantAgent, UserProxyAgent
from agent_eval import track_agent, track_tool

# Track AutoGen agent execution
@track_agent()
def run_autogen_conversation(task: str):
    assistant = AssistantAgent("assistant")
    user_proxy = UserProxyAgent("user_proxy")
    
    user_proxy.initiate_chat(assistant, message=task)
    return "Conversation completed"
```

### Custom Framework

```python
class MyAgent:
    def __init__(self):
        self.tools = []
    
    @track_agent(query_arg="query")
    def run(self, query: str):
        # Agent logic
        for tool in self.tools:
            if tool.can_handle(query):
                return tool.execute(query)
        return "No tool available"
    
    @track_tool()
    def add_tool(self, tool):
        self.tools.append(tool)
```

## Advanced Usage

### Custom Storage Configuration

```python
from agent_eval import configure_storage, StorageConfig, StorageType

# JSON storage
configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="data/evaluations.json"
))

# SQLite storage
configure_storage(StorageConfig(
    storage_type=StorageType.SQLITE,
    file_path="data/evaluations.db"
))

# CSV storage
configure_storage(StorageConfig(
    storage_type=StorageType.CSV,
    file_path="data/evaluations"
))
```

### Batch Execution Tracking

```python
from agent_eval import track_agent, list_executions

@track_agent()
def batch_process(queries: list):
    results = []
    for query in queries:
        result = process(query)
        results.append(result)
    return results

# Execute batch
queries = ["Q1", "Q2", "Q3"]
batch_process(queries)

# Get all executions
executions = list_executions()
print(f"Total executions: {len(executions)}")
```

### Error Tracking

```python
from agent_eval import track_agent, get_last_execution

@track_agent()
def error_prone_agent(query: str):
    if "error" in query:
        raise ValueError("Something went wrong!")
    return "Success"

try:
    error_prone_agent("trigger error")
except ValueError:
    pass

# Check error in execution
execution = get_last_execution()
print(f"Success: {execution.success}")
print(f"Has Error: {execution.has_error}")
print(f"Error Message: {execution.error_message}")
```

### Integration with Evaluation

```python
from agent_eval import (
    track_agent, 
    AgentEvaluator, 
    EvaluationConfig,
    LLMConfig
)

# Track execution
@track_agent()
def my_agent(query: str):
    return f"Answer to: {query}"

result = my_agent("What is AI?")

# Evaluate
config = EvaluationConfig(
    llm_config=LLMConfig(api_key="your-key", model="gpt-4")
)
evaluator = AgentEvaluator(config)

# Get execution and evaluate
from agent_eval import get_last_execution
execution = get_last_execution()
evaluation = evaluator.evaluate(execution)

print(f"Overall Score: {evaluation.overall_score:.2%}")
```

## Best Practices

1. **Use @track_agent for main entry points**: Wrap your main agent function
2. **Use @track_tool for external calls**: Track API calls, database queries, etc.
3. **Use @track_step for complex logic**: Break down complex agents into steps
4. **Configure storage early**: Set up storage before running agents
5. **Handle errors gracefully**: Errors are automatically tracked
6. **Use context managers for fine-grained control**: When you need to manually add steps or tool calls
7. **Leverage concurrent execution support**: Use async/await for better performance

## Troubleshooting

### Issue: Decorator not tracking

Make sure to call `configure_storage()` before using decorators:

```python
from agent_eval import configure_storage, StorageConfig

configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="evaluations.json"
))
```

### Issue: Missing execution data

Check that the query argument name matches:

```python
# If your function uses 'input' instead of 'query'
@track_agent(query_arg="input")
def my_agent(input: str):
    return result
```

### Issue: Tool calls not tracked

Ensure tools are called within an active agent execution:

```python
@track_agent()
def agent(query: str):
    # Tool calls here will be tracked
    return tool_call(query)
```

### Issue: Concurrent execution conflicts

AgentEval uses ContextVars for thread-safe tracking. Each execution has its own isolated context:

```python
import asyncio
from agent_eval import track_agent

@track_agent()
async def async_agent(query: str):
    return process(query)

# Each execution has its own context
async def main():
    await asyncio.gather(
        async_agent("Query 1"),
        async_agent("Query 2"),
        async_agent("Query 3")
    )
```
