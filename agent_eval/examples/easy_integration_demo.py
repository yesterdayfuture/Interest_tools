"""
Easy Integration Demo for agent-eval

This example demonstrates the new low-intrusive integration approach.
You can integrate agent-eval with minimal code changes to your existing agent.
"""

import time
from agent_eval import (
    ExecutionTracker,
    SimpleTracker,
    track,
    AgentEvaluator,
    EvaluationConfig,
    ExpectedResult,
    StorageConfig,
    StorageType,
)


def demo_simple_tracker():
    """Demo: Ultra-simple integration with SimpleTracker"""
    print("=" * 70)
    print("Demo 1: SimpleTracker - Minimal Code Intrusion")
    print("=" * 70)
    
    # Your existing agent function
    def my_agent(query: str) -> str:
        """Your existing agent implementation"""
        # Step 1: Analyze query
        time.sleep(0.01)
        
        # Step 2: Call tool
        time.sleep(0.02)
        
        # Step 3: Generate answer
        return f"Answer to '{query}': This is the result."
    
    # Wrap with tracker - only 3 lines of code!
    tracker = SimpleTracker()
    
    with tracker.start("What is artificial intelligence?"):
        # Record steps
        tracker.step("分析查询意图", step_input="What is artificial intelligence?")
        
        # Record tool calls
        tracker.tool_call(
            tool_name="search_tool",
            tool_input={"query": "artificial intelligence definition"},
            tool_output={"results": ["AI is...", "Machine learning..."]},
            duration_ms=25.5
        )
        
        # Execute your agent
        result = my_agent("What is artificial intelligence?")
        
        # Record final result
        tracker.record_result(result)
    
    # Get execution data
    execution = tracker.get_execution()
    
    print(f"\nExecution Summary:")
    print(f"  Query: {execution.query}")
    print(f"  Steps Summary: {execution.steps_summary}")
    print(f"  Step Count: {execution.step_count}")
    print(f"  Tool Call Count: {execution.tool_call_count}")
    print(f"  Final Output: {execution.final_output}")
    print(f"  Success: {execution.success}")
    
    print(f"\n  Step Details:")
    for step in execution.steps_detail:
        print(f"    Step {step.step}: {step.description}")
        print(f"      Input: {step.input}")
        print(f"      Output: {step.output}")
        print(f"      Time: {step.time}ms")
    
    print(f"\n  Tool Call Details:")
    for tool in execution.tool_calls_detail:
        print(f"    - {tool.name}")
        print(f"      Input: {tool.input}")
        print(f"      Output: {tool.output}")
        print(f"      Time: {tool.time}ms")
    
    return execution


def demo_execution_tracker():
    """Demo: More control with ExecutionTracker"""
    print("\n" + "=" * 70)
    print("Demo 2: ExecutionTracker - Full Control")
    print("=" * 70)
    
    tracker = ExecutionTracker()
    
    # Start tracking
    tracker.start("Explain quantum computing")
    
    # Add steps with detailed information
    tracker.add_step(
        description="理解查询意图",
        step_input="Explain quantum computing",
        step_output={"intent": "explanation", "topic": "quantum computing"}
    )
    
    tracker.add_step(
        description="检索相关知识",
        step_input={"topic": "quantum computing"},
        step_output={"articles": 5}
    )
    
    # Add tool calls
    tracker.add_tool_call(
        tool_name="knowledge_base_search",
        tool_input={"query": "quantum computing basics", "limit": 10},
        tool_output={"results": [{"title": "Quantum 101", "score": 0.95}]},
        duration_ms=45.2
    )
    
    tracker.add_tool_call(
        tool_name="calculator",
        tool_input={"expression": "2^10"},
        tool_output=1024,
        duration_ms=5.1
    )
    
    # Add final step
    tracker.add_step(
        description="生成最终回答",
        step_output="Quantum computing is a type of computation..."
    )
    
    # Set final output
    tracker.set_final_output("Quantum computing is a type of computation that harnesses quantum mechanical phenomena.")
    
    # Finish tracking
    execution = tracker.finish(success=True)
    
    print(f"\nExecution Summary:")
    print(f"  Query: {execution.query}")
    print(f"  Steps Summary:\n{execution.steps_summary}")
    print(f"  Total Steps: {execution.step_count}")
    print(f"  Total Tool Calls: {execution.tool_call_count}")
    print(f"  Duration: {execution.total_duration_ms:.2f}ms")
    print(f"  Success: {execution.success}")
    
    return execution


def demo_context_manager():
    """Demo: Using context manager"""
    print("\n" + "=" * 70)
    print("Demo 3: Context Manager - Automatic Error Handling")
    print("=" * 70)
    
    tracker = ExecutionTracker()
    
    try:
        with tracker.track("Complex query processing"):
            # Step 1
            tracker.add_step("解析查询")
            
            # Step 2 with tool
            tracker.add_tool_call(
                tool_name="parser",
                tool_input={"text": "Complex query"},
                duration_ms=10.0
            )
            
            # Simulate error
            # raise ValueError("Something went wrong!")
            
            # Step 3
            tracker.add_step("生成结果")
            tracker.set_final_output("Result")
            
    except Exception as e:
        print(f"Error captured: {e}")
    
    execution = tracker.execution
    
    print(f"\nExecution Summary:")
    print(f"  Query: {execution.query}")
    print(f"  Success: {execution.success}")
    print(f"  Has Error: {execution.has_error}")
    print(f"  Steps: {execution.step_count}")
    
    return execution


def demo_decorator():
    """Demo: Using decorator"""
    print("\n" + "=" * 70)
    print("Demo 4: Decorator - Zero Code Changes to Agent")
    print("=" * 70)
    
    tracker = ExecutionTracker()
    
    # Your existing agent function
    @tracker.wrap
    def my_existing_agent(query: str) -> str:
        """Your existing agent - no changes needed!"""
        # Simulate processing
        time.sleep(0.01)
        return f"Processed: {query}"
    
    # Call as usual - returns (result, execution)
    result, execution = my_existing_agent("Test query")
    
    print(f"\nAgent Result: {result}")
    print(f"\nExecution Data:")
    print(f"  ID: {execution.execution_id}")
    print(f"  Query: {execution.query}")
    print(f"  Success: {execution.success}")
    
    return execution


def demo_evaluation():
    """Demo: Evaluate the execution"""
    print("\n" + "=" * 70)
    print("Demo 5: Evaluate Execution")
    print("=" * 70)
    
    # Create execution
    tracker = ExecutionTracker()
    tracker.start("What is the capital of France?")
    
    tracker.add_step("理解查询", step_input="What is the capital of France?")
    tracker.add_tool_call(
        tool_name="search",
        tool_input={"query": "capital of France"},
        tool_output={"answer": "Paris"},
        duration_ms=30.0
    )
    tracker.add_step("生成回答")
    tracker.set_final_output("The capital of France is Paris.")
    
    execution = tracker.finish(success=True)
    
    # Evaluate
    config = EvaluationConfig(
        use_code_scorer=True,
        use_llm_scorer=False,
        storage_config=StorageConfig(
            storage_type=StorageType.JSON,
            file_path="evaluations.json"
        )
    )
    evaluator = AgentEvaluator(config)
    
    expected = ExpectedResult(
        expected_output="Paris",
        expected_steps=["理解查询", "检索信息", "生成回答"],
        expected_tool_count=1
    )
    
    result = evaluator.evaluate(execution, expected, save_result=True)
    
    print(f"\nEvaluation Results:")
    print(f"  Overall Score: {result.overall_score:.2%}")
    print(f"\n  Metric Scores:")
    for metric in result.metric_scores:
        print(f"    - {metric.metric_name}: {metric.score:.2%}")
        if metric.details:
            print(f"      Details: {metric.details}")
    
    return result


def demo_global_tracker():
    """Demo: Using global tracker"""
    print("\n" + "=" * 70)
    print("Demo 6: Global Tracker - Convenience Function")
    print("=" * 70)
    
    # Use global tracker
    with track("Global tracking demo") as t:
        t.add_step("Step 1")
        t.add_tool_call("tool1", {"arg": "value"})
        t.add_step("Step 2")
        t.set_final_output("Done")
    
    # Get last execution
    from agent_eval import get_last_execution
    execution = get_last_execution()
    
    print(f"\nExecution from global tracker:")
    print(f"  Query: {execution.query}")
    print(f"  Steps: {execution.step_count}")
    print(f"  Tools: {execution.tool_call_count}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Agent Eval - Easy Integration Demos")
    print("=" * 70 + "\n")
    
    demo_simple_tracker()
    demo_execution_tracker()
    demo_context_manager()
    demo_decorator()
    demo_evaluation()
    demo_global_tracker()
    
    print("\n" + "=" * 70)
    print("All demos completed!")
    print("=" * 70)
