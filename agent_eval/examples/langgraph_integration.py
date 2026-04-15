"""
LangGraph Integration Example for agent-eval

This example demonstrates how to integrate agent-eval with LangGraph to:
1. Record all execution data during graph execution
2. Capture tool calls and their results
3. Evaluate the agent's performance
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
import time

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    print("Please install langgraph: pip install langgraph")
    raise

# Agent eval imports
from agent_eval import AgentEvaluator, EvaluationConfig, StorageConfig, StorageType
from agent_eval.models import AgentExecution, ExpectedResult, ExecutionStep, ToolCall
from agent_eval.recorders import ExecutionRecorder


# ============================================================================
# Global recorder storage (to avoid serialization issues)
# ============================================================================

_recorder_store: Dict[str, ExecutionRecorder] = {}


def get_recorder(execution_id: str) -> Optional[ExecutionRecorder]:
    """Get recorder from global store"""
    return _recorder_store.get(execution_id)


def set_recorder(execution_id: str, recorder: ExecutionRecorder):
    """Store recorder in global store"""
    _recorder_store[execution_id] = recorder


def clear_recorder(execution_id: str):
    """Clear recorder from global store"""
    if execution_id in _recorder_store:
        del _recorder_store[execution_id]


# ============================================================================
# Define State
# ============================================================================

class AgentState(TypedDict):
    """State for the agent - must be serializable"""
    messages: Annotated[List[Dict], operator.add]
    query: str
    execution_id: str
    final_answer: str
    step_count: int
    tool_count: int


# ============================================================================
# Node Functions
# ============================================================================

def initialize_node(state: AgentState) -> AgentState:
    """Initialize the execution recorder"""
    recorder = ExecutionRecorder()
    recorder.start_recording(state["query"])
    
    execution_id = recorder.current_record.execution_id
    set_recorder(execution_id, recorder)
    
    return {
        **state,
        "execution_id": execution_id,
        "step_count": 0,
        "tool_count": 0
    }


def agent_node(state: AgentState) -> AgentState:
    """Agent node that processes the query"""
    recorder = get_recorder(state["execution_id"])
    
    if recorder:
        recorder.record_step("Agent processes query", {
            "query": state["query"],
            "message_count": len(state["messages"])
        })
    
    # Simulate agent thinking/processing
    response = {
        "role": "assistant",
        "content": f"Processing: {state['query']}"
    }
    
    return {
        **state,
        "messages": state["messages"] + [response],
        "step_count": state["step_count"] + 1
    }


def tool_node(state: AgentState) -> AgentState:
    """Tool execution node"""
    recorder = get_recorder(state["execution_id"])
    
    if recorder:
        # Simulate tool execution with timing
        start_time = time.time()
        time.sleep(0.01)  # Simulate execution time
        duration_ms = (time.time() - start_time) * 1000
        
        recorder.record_tool_call(
            tool_name="search_tool",
            arguments={"query": state["query"]},
            result={"data": f"Results for {state['query']}"},
            duration_ms=duration_ms
        )
    
    tool_response = {
        "role": "tool",
        "content": f"Results for {state['query']}",
        "name": "search_tool"
    }
    
    return {
        **state,
        "messages": state["messages"] + [tool_response],
        "step_count": state["step_count"] + 1,
        "tool_count": state["tool_count"] + 1
    }


def final_node(state: AgentState) -> AgentState:
    """Generate final answer and end recording"""
    recorder = get_recorder(state["execution_id"])
    
    final_answer = f"Answer to '{state['query']}': This is the result."
    
    if recorder:
        recorder.record_step("Generate final answer", {
            "answer": final_answer
        })
        
        execution = recorder.end_recording(
            success=True,
            final_output=final_answer
        )
    
    return {
        **state,
        "final_answer": final_answer,
        "step_count": state["step_count"] + 1
    }


# ============================================================================
# Build Graph
# ============================================================================

def build_agent_graph() -> StateGraph:
    """Build the LangGraph workflow"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("init", initialize_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("final", final_node)
    
    # Add edges
    workflow.set_entry_point("init")
    workflow.add_edge("init", "agent")
    workflow.add_edge("agent", "tool")
    workflow.add_edge("tool", "final")
    workflow.add_edge("final", END)
    
    return workflow.compile()


# ============================================================================
# Evaluation Functions
# ============================================================================

def get_execution_from_state(state: AgentState) -> Optional[AgentExecution]:
    """Get execution from recorder store"""
    recorder = get_recorder(state.get("execution_id", ""))
    if recorder:
        # Get the most recent execution from history
        history = recorder.get_execution_history()
        if history:
            return history[-1]
    return None


def evaluate_execution(
    execution: AgentExecution,
    expected_output: str,
    expected_steps: int = None,
    expected_tools: int = None
) -> Dict[str, Any]:
    """
    Evaluate a single execution
    
    Args:
        execution: The recorded execution
        expected_output: Expected final output
        expected_steps: Expected number of steps
        expected_tools: Expected number of tool calls
    
    Returns:
        Evaluation results
    """
    config = EvaluationConfig(
        use_code_scorer=True,
        use_llm_scorer=False,
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="langgraph_evaluations.json"
        )
    )
    evaluator = AgentEvaluator(config)
    
    expected = ExpectedResult(
        expected_output=expected_output,
        expected_steps=[f"step_{i}" for i in range(expected_steps)] if expected_steps else None,
        expected_tool_count=expected_tools
    )
    
    result = evaluator.evaluate(execution, expected, save_result=True)
    
    return {
        "evaluation_id": result.evaluation_id,
        "overall_score": result.overall_score,
        "metric_scores": [
            {
                "name": m.metric_name,
                "score": m.score,
                "weight": m.weight,
                "details": m.details
            }
            for m in result.metric_scores
        ],
        "scorer_results": result.scorer_results if isinstance(result.scorer_results, list) else []
    }


def batch_evaluate_executions(
    executions: List[AgentExecution],
    expected_results: List[ExpectedResult]
) -> Dict[str, Any]:
    """Batch evaluate multiple executions"""
    config = EvaluationConfig(use_code_scorer=True)
    evaluator = AgentEvaluator(config)
    
    results = evaluator.batch_evaluate(
        executions,
        expected_results,
        save_results=False
    )
    
    return evaluator.get_evaluation_summary(results)


# ============================================================================
# Main Demos
# ============================================================================

def demo_single_execution():
    """Demo: Single execution with evaluation"""
    print("=" * 70)
    print("Demo 1: Single LangGraph Execution with Evaluation")
    print("=" * 70)
    
    graph = build_agent_graph()
    
    initial_state = {
        "messages": [],
        "query": "What is the weather in New York?",
        "execution_id": "",
        "final_answer": "",
        "step_count": 0,
        "tool_count": 0
    }
    
    # Execute graph
    final_state = graph.invoke(initial_state)
    
    # Get execution from recorder store
    execution = get_execution_from_state(final_state)
    
    if not execution:
        print("Error: Could not retrieve execution")
        return None
    
    print(f"\nExecution Summary:")
    print(f"  Query: {execution.query}")
    print(f"  Steps: {len(execution.steps)}")
    print(f"  Tool Calls: {execution.total_tool_calls}")
    print(f"  Duration: {execution.total_duration_ms:.2f} ms")
    print(f"  Success: {execution.success}")
    
    # Show step details
    print(f"\n  Step Details:")
    for i, step in enumerate(execution.steps):
        print(f"    {i+1}. {step.description}")
        if step.tool_calls:
            for tc in step.tool_calls:
                print(f"       - Tool: {tc.tool_name} ({tc.duration_ms:.2f}ms)")
    
    # Evaluate
    print("\nEvaluating...")
    evaluation = evaluate_execution(
        execution=execution,
        expected_output="weather",
        expected_steps=4,
        expected_tools=1
    )
    
    print(f"\nEvaluation Results:")
    print(f"  Overall Score: {evaluation['overall_score']:.2%}")
    print(f"\n  Metric Scores:")
    for metric in evaluation['metric_scores']:
        print(f"    - {metric['name']}: {metric['score']:.2%}")
        if metric['details']:
            print(f"      Details: {metric['details']}")
    
    # Cleanup
    clear_recorder(final_state["execution_id"])
    
    return execution


def demo_multiple_executions():
    """Demo: Multiple executions with batch evaluation"""
    print("\n" + "=" * 70)
    print("Demo 2: Batch Evaluation of Multiple Executions")
    print("=" * 70)
    
    graph = build_agent_graph()
    executions = []
    execution_ids = []
    
    queries = [
        "What is the capital of France?",
        "How to bake a cake?",
        "Explain quantum computing"
    ]
    
    for query in queries:
        initial_state = {
            "messages": [],
            "query": query,
            "execution_id": "",
            "final_answer": "",
            "step_count": 0,
            "tool_count": 0
        }
        
        final_state = graph.invoke(initial_state)
        execution = get_execution_from_state(final_state)
        
        if execution:
            executions.append(execution)
            execution_ids.append(final_state["execution_id"])
    
    # Create expected results
    expected_results = [
        ExpectedResult(expected_output="Paris", expected_tool_count=1),
        ExpectedResult(expected_output="cake", expected_tool_count=1),
        ExpectedResult(expected_output="quantum", expected_tool_count=1)
    ]
    
    # Batch evaluate
    print(f"\nEvaluating {len(executions)} executions...")
    summary = batch_evaluate_executions(executions, expected_results)
    
    print(f"\nBatch Evaluation Summary:")
    print(f"  Total Evaluations: {summary['total_evaluations']}")
    print(f"  Average Overall Score: {summary['overall_score']['average']:.2%}")
    print(f"  Score Range: {summary['overall_score']['min']:.2%} - {summary['overall_score']['max']:.2%}")
    print(f"\n  Metric Averages:")
    for metric_name, data in summary['metric_averages'].items():
        print(f"    - {metric_name}: {data['average']:.2%}")
    
    # Cleanup
    for eid in execution_ids:
        clear_recorder(eid)


def demo_custom_recording():
    """Demo: Custom recording with detailed metrics"""
    print("\n" + "=" * 70)
    print("Demo 3: Custom Recording with Detailed Metrics")
    print("=" * 70)
    
    # Create custom workflow
    workflow = StateGraph(AgentState)
    
    def custom_init(state: AgentState) -> AgentState:
        recorder = ExecutionRecorder()
        recorder.start_recording(state["query"])
        execution_id = recorder.current_record.execution_id
        set_recorder(execution_id, recorder)
        return {**state, "execution_id": execution_id, "step_count": 0}
    
    def custom_agent(state: AgentState) -> AgentState:
        recorder = get_recorder(state["execution_id"])
        if recorder:
            # Record multiple steps
            for i in range(3):
                recorder.record_step(f"Processing phase {i+1}", {
                    "iteration": i,
                    "complexity": "high"
                })
                
                # Record multiple tool calls
                for j in range(2):
                    start = time.time()
                    time.sleep(0.005)
                    duration = (time.time() - start) * 1000
                    
                    recorder.record_tool_call(
                        tool_name=f"sub_tool_{j}",
                        arguments={"phase": i, "subtask": j},
                        result={"status": "ok"},
                        duration_ms=duration
                    )
        
        return {**state, "step_count": state["step_count"] + 3}
    
    def custom_final(state: AgentState) -> AgentState:
        recorder = get_recorder(state["execution_id"])
        if recorder:
            final_answer = f"Complex result for: {state['query']}"
            recorder.record_step("Finalize", {"output_length": len(final_answer)})
            recorder.end_recording(success=True, final_output=final_answer)
            return {**state, "final_answer": final_answer}
        return state
    
    workflow.add_node("init", custom_init)
    workflow.add_node("agent", custom_agent)
    workflow.add_node("final", custom_final)
    workflow.set_entry_point("init")
    workflow.add_edge("init", "agent")
    workflow.add_edge("agent", "final")
    workflow.add_edge("final", END)
    
    graph = workflow.compile()
    
    # Execute
    final_state = graph.invoke({
        "messages": [],
        "query": "Complex multi-step task",
        "execution_id": "",
        "final_answer": "",
        "step_count": 0,
        "tool_count": 0
    })
    
    execution = get_execution_from_state(final_state)
    
    if execution:
        print(f"\nDetailed Execution Record:")
        print(f"  Query: {execution.query}")
        print(f"  Total Steps: {len(execution.steps)}")
        print(f"  Total Tool Calls: {execution.total_tool_calls}")
        print(f"  Duration: {execution.total_duration_ms:.2f} ms")
        
        print(f"\n  Step Breakdown:")
        for i, step in enumerate(execution.steps):
            print(f"    Step {i+1}: {step.description}")
            if step.metadata:
                print(f"      Metadata: {step.metadata}")
            if step.tool_calls:
                for tc in step.tool_calls:
                    print(f"      - {tc.tool_name}: {tc.duration_ms:.2f}ms")
        
        # Evaluate
        evaluation = evaluate_execution(
            execution=execution,
            expected_output="result",
            expected_steps=5,
            expected_tools=6
        )
        
        print(f"\n  Evaluation Score: {evaluation['overall_score']:.2%}")
    
    clear_recorder(final_state["execution_id"])


# ============================================================================
# Integration Helper Class
# ============================================================================

class LangGraphEvaluator:
    """
    Helper class to integrate agent-eval with LangGraph
    
    Usage:
        evaluator = LangGraphEvaluator()
        
        # Define your graph
        graph = build_your_graph()
        
        # Execute and evaluate
        result = evaluator.execute_and_evaluate(
            graph=graph,
            query="Your query here",
            expected_output="Expected answer"
        )
    """
    
    def __init__(self, storage_path: str = "evaluations.json"):
        self.config = EvaluationConfig(
            storage_config=StorageConfig(
                storage_type=StorageType.JSON,
                file_path=storage_path
            )
        )
        self.evaluator = AgentEvaluator(self.config)
        self.execution_history = []
    
    def execute_and_evaluate(
        self,
        graph,
        query: str,
        expected_output: str,
        expected_steps: int = None,
        expected_tools: int = None
    ) -> Dict[str, Any]:
        """
        Execute a LangGraph and evaluate the result
        
        Args:
            graph: Compiled LangGraph
            query: Input query
            expected_output: Expected final output
            expected_steps: Expected number of steps
            expected_tools: Expected number of tool calls
        
        Returns:
            Dictionary with execution and evaluation results
        """
        initial_state = {
            "messages": [],
            "query": query,
            "execution_id": "",
            "final_answer": "",
            "step_count": 0,
            "tool_count": 0
        }
        
        # Execute graph
        final_state = graph.invoke(initial_state)
        
        # Get execution
        execution = get_execution_from_state(final_state)
        
        if not execution:
            raise ValueError("No execution found. Make sure your graph uses the recording pattern.")
        
        # Store in history
        self.execution_history.append(execution)
        
        # Evaluate
        expected = ExpectedResult(
            expected_output=expected_output,
            expected_steps=[f"step_{i}" for i in range(expected_steps)] if expected_steps else None,
            expected_tool_count=expected_tools
        )
        
        evaluation = self.evaluator.evaluate(execution, expected)
        
        # Cleanup
        clear_recorder(final_state["execution_id"])
        
        return {
            "execution": execution,
            "evaluation": evaluation,
            "overall_score": evaluation.overall_score
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all evaluations"""
        if not self.execution_history:
            return {"message": "No executions recorded"}
        
        return {
            "total_executions": len(self.execution_history),
            "executions": [
                {
                    "id": e.execution_id,
                    "query": e.query,
                    "success": e.success,
                    "steps": len(e.steps),
                    "tool_calls": e.total_tool_calls
                }
                for e in self.execution_history
            ]
        }


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LangGraph Integration Examples for agent-eval")
    print("=" * 70 + "\n")
    
    # Run demos
    demo_single_execution()
    demo_multiple_executions()
    demo_custom_recording()
    
    print("\n" + "=" * 70)
    print("All LangGraph integration demos completed!")
    print("=" * 70)
