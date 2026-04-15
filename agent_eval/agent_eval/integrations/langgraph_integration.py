"""
LangGraph 集成模块 - 追踪图执行和状态变化

本模块提供 LangGraph 集成，自动追踪图的节点执行、状态变化和边跳转。
特别适用于多智能体系统、复杂工作流和循环执行场景。

依赖：
    pip install langgraph

使用示例：
    >>> from agent_eval.integrations import LangGraphTracer, track_langgraph
    >>> from langgraph.graph import StateGraph
    >>> 
    >>> # 方式1：使用追踪器
    >>> tracer = LangGraphTracer(agent_id="workflow")
    >>> result = tracer.run(graph, {"query": "什么是AI？"})
    >>> 
    >>> # 方式2：使用装饰器
    >>> @track_langgraph(agent_id="workflow")
    >>> def my_workflow(query: str):
    ...     return graph.invoke({"query": query})
    >>> 
    >>> result = my_workflow("什么是AI？")
"""

import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar

from agent_eval.decorators import get_current_execution, _set_current_execution, _reset_current_execution
from agent_eval.models import AgentExecution, StepDetail, ToolCallDetail
from agent_eval.storages import BaseStorage

# 尝试导入 LangGraph
try:
    from langgraph.graph import StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = Any

T = TypeVar('T')


class LangGraphTracer:
    """
    LangGraph 追踪器 - 追踪图的执行过程
    
    自动追踪 LangGraph 的节点执行、状态变化和边跳转，
    将图的执行过程转换为 AgentEval 的执行记录。
    
    Attributes:
        agent_id: 智能体/工作流标识符
        storage: 存储后端
        execution: 当前执行记录
        _node_counter: 节点执行计数器
        _edge_counter: 边跳转计数器
        _context_tokens: 上下文变量 token
        _node_start_times: 节点开始时间记录
    
    Example:
        >>> # 定义 LangGraph
        >>> workflow = StateGraph(State)
        >>> workflow.add_node("retrieve", retrieve_node)
        >>> workflow.add_node("generate", generate_node)
        >>> workflow.add_edge("retrieve", "generate")
        >>> graph = workflow.compile()
        >>> 
        >>> # 使用追踪器
        >>> tracer = LangGraphTracer(agent_id="qa_workflow")
        >>> result = tracer.run(graph, {"query": "什么是AI？"})
        >>> 
        >>> # 查看执行记录
        >>> execution = tracer.get_execution()
        >>> for step in execution.steps_detail:
        ...     print(f"{step.description}: {step.output}")
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        storage: Optional[BaseStorage] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化 LangGraph 追踪器
        
        Args:
            agent_id: 智能体/工作流标识符
            storage: 存储后端
            metadata: 执行元数据
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraph is not installed. "
                "Please install it with: pip install langgraph"
            )
        
        self.agent_id = agent_id
        self.storage = storage
        self.metadata = metadata or {}
        
        self.execution: Optional[AgentExecution] = None
        self._node_counter = 0
        self._edge_counter = 0
        self._context_tokens = None
        self._node_start_times: Dict[str, float] = {}
        self._current_node: Optional[str] = None
    
    def _create_execution(self, inputs: Dict[str, Any]):
        """创建执行记录"""
        # 推断查询
        query = None
        for key in ["query", "question", "input", "prompt", "message"]:
            if key in inputs:
                query = str(inputs[key])
                break
        else:
            query = str(inputs)[:100]
        
        self.execution = AgentExecution(
            execution_id=str(uuid.uuid4()),
            query=query,
            agent_id=self.agent_id,
            start_time=datetime.now(),
            metadata={
                **self.metadata,
                "framework": "langgraph",
                "input": inputs
            }
        )
        
        # 设置上下文变量
        self._context_tokens = _set_current_execution(self.execution)
    
    def _save_execution(self, success: bool = True):
        """保存执行记录"""
        if self.execution:
            self.execution.end_time = datetime.now()
            self.execution.success = success and not self.execution.has_error
            
            if self.storage:
                self.storage.save_execution(self.execution)
            
            # 重置上下文（只重置一次）
            if self._context_tokens:
                try:
                    _reset_current_execution(self._context_tokens[0], self._context_tokens[1])
                except RuntimeError:
                    # Token 已经被使用过，忽略错误
                    pass
                self._context_tokens = None
    
    def _on_node_start(self, node_name: str, state: Dict[str, Any]):
        """节点开始执行"""
        self._node_counter += 1
        self._current_node = node_name
        self._node_start_times[node_name] = time.time()
        
        if self.execution:
            step = StepDetail(
                step=self._node_counter,
                description=f"node:{node_name}",
                input=state.copy(),
                output=None,
                success=True
            )
            self.execution.steps_detail.append(step)
            self.execution.step_count = self._node_counter
    
    def _on_node_end(self, node_name: str, result: Dict[str, Any]):
        """节点执行结束"""
        duration_ms = None
        if node_name in self._node_start_times:
            duration_ms = (time.time() - self._node_start_times[node_name]) * 1000
        
        if self.execution and self.execution.steps_detail:
            # 找到对应的步骤并更新
            for step in reversed(self.execution.steps_detail):
                if step.description == f"node:{node_name}" and step.output is None:
                    step.output = result.copy() if result else {}
                    if duration_ms:
                        step.time = duration_ms
                    break
    
    def _on_edge_traversal(self, from_node: str, to_node: str, condition: Optional[str] = None):
        """记录边跳转"""
        self._edge_counter += 1
        
        if self.execution:
            edge_info = {
                "edge_id": self._edge_counter,
                "from": from_node,
                "to": to_node,
                "condition": condition
            }
            
            if "edges" not in self.execution.metadata:
                self.execution.metadata["edges"] = []
            self.execution.metadata["edges"].append(edge_info)
    
    def run(
        self,
        graph,
        inputs: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        运行图并追踪执行
        
        注意：此实现会记录图的整体执行，但不追踪单个节点。
        如需追踪单个节点，请在节点函数内部使用 LangGraphCallback。
        
        Args:
            graph: LangGraph 编译后的图实例 (StateGraph.compile() 的结果)
            inputs: 图的输入状态
            config: 可选的配置
            
        Returns:
            图的最终状态
            
        Example:
            >>> tracer = LangGraphTracer(agent_id="workflow")
            >>> result = tracer.run(graph, {"query": "什么是AI？"})
            >>> print(result["answer"])
        """
        self._create_execution(inputs)
        
        try:
            # 记录开始执行
            self._on_node_start("graph", inputs)
            
            # 执行图
            result = graph.invoke(inputs, config)
            
            # 记录执行完成
            self._on_node_end("graph", result)
            
            # 设置输出
            if self.execution:
                self.execution.final_output = str(result) if result else ""
            
            return result
        except Exception as e:
            if self.execution:
                self.execution.has_error = True
                self.execution.error_message = str(e)
            raise
        finally:
            self._save_execution(success=not (self.execution and self.execution.has_error))
    
    def get_execution(self) -> Optional[AgentExecution]:
        """获取当前执行记录"""
        return self.execution
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            执行摘要字典
        """
        if not self.execution:
            return {"error": "No execution recorded"}
        
        return {
            "execution_id": self.execution.execution_id,
            "query": self.execution.query,
            "success": self.execution.success,
            "has_error": self.execution.has_error,
            "node_count": self._node_counter,
            "edge_count": self._edge_counter,
            "step_count": len(self.execution.steps_detail),
            "duration_ms": self.execution.total_duration_ms,
            "nodes": [
                {
                    "name": step.description.replace("node:", ""),
                    "input": step.input,
                    "output": step.output,
                    "success": step.success
                }
                for step in self.execution.steps_detail
                if step.description.startswith("node:")
            ]
        }


def track_langgraph(
    agent_id: Optional[str] = None,
    storage: Optional[BaseStorage] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    LangGraph 追踪装饰器
    
    用于装饰执行 LangGraph 的函数，自动追踪图的执行过程。
    
    Args:
        agent_id: 智能体/工作流标识符
        storage: 存储后端
        metadata: 执行元数据
        
    Returns:
        装饰器函数
        
    Example:
        >>> @track_langgraph(agent_id="qa_workflow")
        ... def run_qa(query: str):
        ...     return graph.invoke({"query": query})
        ... 
        >>> result = run_qa("什么是AI？")
        >>> # 执行自动被追踪
        
        >>> # 获取执行记录
        >>> from agent_eval.decorators import get_current_execution
        >>> execution = get_current_execution()
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 创建追踪器
            tracer = LangGraphTracer(
                agent_id=agent_id or func.__name__,
                storage=storage,
                metadata={**metadata, "function": func.__name__} if metadata else {"function": func.__name__}
            )
            
            # 设置上下文
            if args:
                # 尝试从第一个参数推断查询
                if isinstance(args[0], str):
                    query = args[0]
                elif isinstance(args[0], dict) and "query" in args[0]:
                    query = args[0]["query"]
                else:
                    query = str(args[0])[:100]
            else:
                query = kwargs.get("query", "unknown")
            
            # 执行函数
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # 如果函数返回的是图实例，执行它
                if hasattr(result, 'invoke'):
                    inputs = kwargs.get('inputs', args[0] if args else {})
                    result = tracer.run(result, inputs)
                
                return result
            except Exception as e:
                raise
        
        return wrapper
    return decorator


class LangGraphCallback:
    """
    LangGraph 回调接口 - 用于更细粒度的控制
    
    可以在 LangGraph 的节点中手动调用，记录自定义步骤。
    
    Example:
        >>> callback = LangGraphCallback()
        >>> 
        >>> def my_node(state):
        ...     callback.on_step_start("process", state)
        ...     result = process(state)
        ...     callback.on_step_end("process", result)
        ...     return result
    """
    
    def __init__(self, execution: Optional[AgentExecution] = None):
        """
        初始化回调
        
        Args:
            execution: 可选的执行记录，如果未提供将使用当前上下文
        """
        self.execution = execution or get_current_execution()
        self._step_counter = 0
    
    def on_step_start(self, step_name: str, inputs: Any = None):
        """记录步骤开始"""
        if not self.execution:
            return
        
        self._step_counter += 1
        step = StepDetail(
            step=self._step_counter,
            description=step_name,
            input=inputs,
            output=None,
            success=True
        )
        self.execution.steps_detail.append(step)
        self.execution.step_count = self._step_counter
    
    def on_step_end(self, step_name: str, outputs: Any = None):
        """记录步骤结束"""
        if not self.execution:
            return
        
        # 查找对应的步骤并更新
        for step in reversed(self.execution.steps_detail):
            if step.description == step_name and step.output is None:
                step.output = outputs
                break
    
    def on_tool_call(self, tool_name: str, tool_input: Dict, tool_output: Any = None):
        """记录工具调用"""
        if not self.execution:
            return
        
        tool_call = ToolCallDetail(
            name=tool_name,
            input=tool_input,
            output=tool_output,
            success=True
        )
        self.execution.tool_calls_detail.append(tool_call)
        self.execution.tool_call_count = len(self.execution.tool_calls_detail)
