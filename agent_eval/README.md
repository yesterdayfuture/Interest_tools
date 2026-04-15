# AgentEval

A comprehensive evaluation system for AI agents with zero-code-intrusion integration.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[中文文档](README_CN.md)

## Features

- **Zero Code Intrusion**: Integrate with decorators - no changes to existing code
- **Comprehensive Metrics**: Correctness, Step Ratio, Tool Call Ratio, Solve Rate, Latency Ratio
- **Hybrid Scoring**: Combine code-based checks with LLM-as-Judge evaluation
- **Multiple Storage Backends**: JSON, CSV, SQLite, PostgreSQL support
- **Ideal Answer Generation**: Use LLM to generate expected execution paths without calling real tools
- **Detailed Reporting**: Single and batch evaluation reports with comparison analysis
- **Framework Agnostic**: Works with LangChain, AutoGen, LangGraph, or custom frameworks
- **Concurrent Execution**: ContextVars-based tracking supports concurrent and nested executions

## Quick Start

### Installation

```bash
pip install agent-eval
```

### Basic Usage

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
    return f"Answer to: {query}"

# Execute - automatically tracked
result = my_agent("What is AI?")
```

### Track Tools and Steps

```python
from agent_eval import track_tool, track_step

@track_tool("search")
def search_api(query: str):
    return {"results": ["result1", "result2"]}

@track_step("parse_query")
def parse_query(query: str):
    return {"intent": "search", "keywords": query.split()}

@track_agent()
def complex_agent(query: str):
    parsed = parse_query(query)
    results = search_api(parsed["keywords"])
    return f"Found {len(results)} results"
```

## Core Components

### 1. AgentEvaluator

`AgentEvaluator` is the core orchestrator of the evaluation framework, integrating recording, metrics calculation, scoring, and storage.

```python
from agent_eval import AgentEvaluator, EvaluationConfig

# Create evaluator
config = EvaluationConfig(
    storage_type=StorageType.SQLITE,
    file_path="evaluations.db"
)
evaluator = AgentEvaluator(config)

# Record execution
with evaluator.create_recording_context("Weather query") as rec:
    result = agent.run("Weather query")
    rec.set_output(result)

# Evaluate
from agent_eval.models import ExpectedResult
expected = ExpectedResult(
    query="Weather query",
    expected_steps=["Parse location", "Fetch data"],
    expected_tools=["weather_api"],
    expected_output="Sunny in Beijing today"
)
evaluation = evaluator.evaluate(expected=expected)
print(f"Overall Score: {evaluation.overall_score:.2%}")
```

### 2. Decorators

#### @track_agent() - Track Agent Execution

```python
from agent_eval.decorators import track_agent

@track_agent(query_arg="question")
def my_agent(question: str, **kwargs):
    # Agent logic
    return result

# Execute with automatic tracking
result = my_agent("What is machine learning?")
```

#### @track_tool() - Track Tool Calls

```python
from agent_eval.decorators import track_tool

@track_tool("calculator")
def calculator(expression: str) -> str:
    return str(eval(expression))

@track_tool()  # Use function name as tool name
def search(query: str) -> dict:
    return {"results": [...]}
```

#### @track_step() - Track Execution Steps

```python
from agent_eval.decorators import track_step

@track_step("data_preprocessing")
def preprocess_data(data: dict) -> dict:
    return cleaned_data
```

### 3. Context Managers

Use `TrackedExecution` for more granular control:

```python
from agent_eval.decorators import TrackedExecution

with TrackedExecution("Complex query", metadata={"source": "web"}) as exec:
    # Step 1: Parse query
    exec.add_step("Parse query", input="Beijing weather", output="Location: Beijing")
    
    # Step 2: Call tool
    exec.add_tool_call("weather_api", {"city": "Beijing"}, result="Sunny 25°C")
    
    # Set final output
    exec.set_output("Beijing is sunny today, 25°C")
# Auto-saved after exiting context
```

### 4. Execution Recorder

Use `ExecutionRecorder` for manual control:

```python
from agent_eval.recorders import ExecutionRecorder

recorder = ExecutionRecorder(storage=storage)

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

## Advanced Usage

### Generate Ideal Answers with LLM

```python
from agent_eval import AgentEvaluator, EvaluationConfig, LLMConfig

config = EvaluationConfig(
    llm_config=LLMConfig(
        model="gpt-4",
        api_key="your-api-key"
    )
)

evaluator = AgentEvaluator(config)

# Generate expected execution without calling real tools
expected = evaluator.generate_and_save_expected(
    query="Calculate 100 + 200",
    available_tools=[
        {"name": "calculator", "description": "Perform calculations"}
    ]
)

print(f"Expected steps: {expected.step_count}")
print(f"Expected tools: {expected.tool_call_count}")
```

### Evaluate from Storage

```python
# Evaluate by loading expected and actual from storage
evaluation = evaluator.evaluate_from_storage(
    query="Calculate 100 + 200"
)

print(f"Overall Score: {evaluation.overall_score:.2%}")
for metric in evaluation.metric_scores:
    print(f"  {metric.metric_name}: {metric.score:.2%}")
```

### Batch Evaluation

```python
# Batch evaluate multiple executions
executions = [exec1, exec2, exec3]
expected_list = [exp1, exp2, exp3]

results = evaluator.batch_evaluate(executions, expected_list)

# Get evaluation summary
summary = evaluator.get_evaluation_summary(results)
print(f"Average Score: {summary['overall_score']['average']:.2%}")
print(f"Total Evaluations: {summary['total_evaluations']}")
```

### Generate Reports

```python
from agent_eval.reporting import EvaluationPipeline

pipeline = EvaluationPipeline(
    storage=evaluator.storage,
    evaluator=evaluator
)

# Single evaluation report
report = pipeline.evaluate_from_storage(
    query="What is AI?",
    report_path="reports/single_eval.json"
)

# Batch evaluation report
batch_report = pipeline.batch_evaluate_from_storage(
    report_path="reports/batch_eval.json"
)

print(f"Average Score: {batch_report['summary']['average_overall_score']:.2%}")
print(f"Score Distribution: {batch_report['summary']['score_distribution']}")
```

## Framework Integration

### LangChain Integration

```python
from agent_eval.integrations import LangChainCallback
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# Create callback handler
callback = LangChainCallback(
    agent_id="qa_bot",
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

# Execute and track
result = chain.invoke(
    {"question": "What is AI?"},
    config={"callbacks": [callback]}
)

# View execution record
execution = callback.get_execution()
print(f"Steps: {execution.step_count}")
print(f"Tool calls: {execution.tool_call_count}")
```

### LangGraph Integration

```python
from agent_eval.integrations import LangGraphTracer, track_langgraph
from langgraph.graph import StateGraph, END

# Method 1: Using tracer
workflow = StateGraph(State)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
graph = workflow.compile()

tracer = LangGraphTracer(agent_id="qa_workflow", storage=storage)
result = tracer.run(graph, {"query": "What is AI?"})

# View execution summary
summary = tracer.get_execution_summary()
print(f"Nodes: {summary['node_count']}")
print(f"Steps: {summary['step_count']}")

# Method 2: Using decorator
@track_langgraph(agent_id="my_workflow", storage=storage)
def run_workflow(query: str):
    return graph.invoke({"query": query})

result = run_workflow("What is AI?")
```

### AutoGen Integration

```python
from autogen import AssistantAgent
from agent_eval import track_agent

@track_agent()
def run_conversation(task: str):
    assistant = AssistantAgent("assistant")
    # ... conversation logic
    return result
```

## Evaluation Metrics

| Metric | Description | Weight |
|--------|-------------|--------|
| **Correctness** | Output accuracy compared to expected | 0.30 |
| **Step Ratio** | Actual vs expected step count | 0.20 |
| **Tool Call Ratio** | Actual vs expected tool calls | 0.20 |
| **Solve Rate** | Task completion success | 0.15 |
| **Latency Ratio** | Actual vs expected duration | 0.15 |

## Storage Options

```python
from agent_eval import StorageConfig, StorageType

# JSON File
config = StorageConfig(
    storage_type=StorageType.JSON,
    file_path="data/evaluations.json"
)

# SQLite Database
config = StorageConfig(
    storage_type=StorageType.SQLITE,
    file_path="data/evaluations.db"
)

# CSV Files
config = StorageConfig(
    storage_type=StorageType.CSV,
    file_path="data/evaluations"
)
```

## Project Structure

```
agent_eval/
├── agent_eval/              # Core package
│   ├── __init__.py          # Main exports
│   ├── core.py              # AgentEvaluator core class
│   ├── models.py            # Data models
│   ├── metrics.py           # Evaluation metrics
│   ├── scorers.py           # Scoring mechanisms
│   ├── generators.py        # LLM generators
│   ├── storages.py          # Storage backends
│   ├── decorators.py        # Decorator integration
│   ├── tracker.py           # Execution tracking
│   ├── recorders.py         # Execution recording
│   ├── reporting.py         # Report generation
│   ├── text_similarity.py   # Text similarity
│   └── integrations/        # Framework integrations
│       ├── __init__.py
│       ├── langchain_integration.py    # LangChain integration
│       └── langgraph_integration.py    # LangGraph integration
├── examples/                # Example code
│   ├── basic_usage.py
│   ├── decorator_example.py
│   ├── langchain_langgraph_example.py
│   └── ideal_answer_example.py
├── docs/                    # Documentation
│   ├── INTEGRATION_GUIDE.md
│   ├── INTEGRATION_GUIDE_CN.md
│   ├── LANGCHAIN_LANGGRAPH_INTEGRATION.md
│   └── ARCHITECTURE.md
└── tests/                   # Tests
```

## Documentation

- [Integration Guide (English)](docs/INTEGRATION_GUIDE.md)
- [Integration Guide (中文)](docs/INTEGRATION_GUIDE_CN.md)
- [LangChain & LangGraph Integration](docs/LANGCHAIN_LANGGRAPH_INTEGRATION.md)
- [Architecture Design](docs/ARCHITECTURE.md)

## API Reference

### Core Classes

- `AgentEvaluator` - Main evaluation orchestrator
- `EvaluationConfig` - Evaluation configuration
- `AgentExecution` - Execution data model
- `EvaluationResult` - Evaluation result model
- `TrackedExecution` - Tracked execution context
- `ExecutionRecorder` - Execution recorder

### Decorators

- `@track_agent()` - Track agent execution
- `@track_tool()` - Track tool calls
- `@track_step()` - Track execution steps
- `@track_langgraph()` - Track LangGraph workflow

### Integration Classes

- `LangChainCallback` - LangChain callback handler
- `LangChainTracer` - LangChain tracer
- `LangGraphTracer` - LangGraph tracer

### Storage

- `JSONStorage` - JSON file storage
- `CSVStorage` - CSV file storage
- `SQLiteStorage` - SQLite database storage
- `PostgresStorage` - PostgreSQL storage (placeholder)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v0.1.0
- Initial release
- Core evaluation metrics
- Decorator-based integration
- Multiple storage backends
- LLM-based ideal answer generation
- Report generation
- LangChain and LangGraph integration
- ContextVars-based concurrent execution tracking
