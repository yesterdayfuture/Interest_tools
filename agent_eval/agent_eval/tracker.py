"""
智能体执行追踪器模块 - 核心追踪和记录功能

本模块提供智能体执行的自动追踪、记录和管理功能。
通过装饰器、上下文管理器或直接API调用，可以轻松追踪智能体的执行过程。

主要功能：
- AgentTracker: 核心追踪器类，管理执行记录和存储
- track_agent: 装饰器，用于自动追踪智能体函数
- ExecutionContext: 执行上下文管理器，支持with语句
- 支持多种存储后端（JSON文件、内存等）

使用场景：
- 智能体性能评估
- 执行历史记录
- 调试和问题排查
- 合规性审计

使用示例：
    # 方式1：使用装饰器
    >>> @track_agent()
    ... def my_agent(query, **kwargs):
    ...     return agent.run(query)
    
    # 方式2：使用上下文管理器
    >>> tracker = AgentTracker()
    >>> with tracker.track("什么是AI？") as ctx:
    ...     result = my_agent("什么是AI？")
    ...     ctx.set_output(result)
    
    # 方式3：直接使用Tracker
    >>> tracker = AgentTracker(storage=storage)
    >>> execution = tracker.start_execution("查询")
    >>> result = my_agent("查询")
    >>> tracker.end_execution(execution, result)
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Union
from contextlib import contextmanager
from dataclasses import dataclass, field

from .storages import BaseStorage, JSONStorage
from .models import AgentExecution


# =============================================================================
# 执行上下文
# =============================================================================

@dataclass
class ExecutionContext:
    """
    执行上下文类
    
    管理单个执行的生命周期，提供便捷的方法来设置输出、添加元数据等。
    支持上下文管理器协议，可以使用with语句自动管理执行的开始和结束。
    
    Attributes:
        execution: AgentExecution实例，包含执行的所有信息
        tracker: AgentTracker实例，用于管理执行
        _active: 上下文是否处于活跃状态
        _output_set: 是否已经设置了输出
    
    Example:
        >>> tracker = AgentTracker()
        >>> with tracker.track("查询") as ctx:
        ...     # 执行智能体
        ...     result = agent.run("查询")
        ...     # 设置输出
        ...     ctx.set_output(result)
        ...     # 添加元数据
        ...     ctx.add_metadata("model", "gpt-4")
    """
    
    execution: AgentExecution
    tracker: 'AgentTracker'
    _active: bool = field(default=True, repr=False)
    _output_set: bool = field(default=False, repr=False)
    
    def set_output(self, output: Any, output_type: str = "text") -> None:
        """
        设置执行输出
        
        记录智能体的输出结果，可以是文本、JSON对象等。
        
        Args:
            output: 输出内容
            output_type: 输出类型（text/json等）
            
        Example:
            >>> with tracker.track("查询") as ctx:
            ...     result = agent.run("查询")
            ...     ctx.set_output(result, output_type="json")
        """
        if not self._active:
            raise RuntimeError("Execution context is not active")
        
        self.execution.output = output
        self.execution.output_type = output_type
        self.execution.status = "completed"
        self._output_set = True
    
    def set_error(self, error: Union[str, Exception]) -> None:
        """
        设置执行错误
        
        记录执行过程中发生的错误。
        
        Args:
            error: 错误信息或异常对象
            
        Example:
            >>> with tracker.track("查询") as ctx:
            ...     try:
            ...         result = agent.run("查询")
            ...         ctx.set_output(result)
            ...     except Exception as e:
            ...         ctx.set_error(e)
        """
        if not self._active:
            raise RuntimeError("Execution context is not active")
        
        if isinstance(error, Exception):
            error_msg = f"{type(error).__name__}: {str(error)}"
        else:
            error_msg = str(error)
        
        self.execution.error = error_msg
        self.execution.status = "error"
        self._output_set = True
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        添加元数据
        
        为执行记录添加额外的元数据信息。
        
        Args:
            key: 元数据键
            value: 元数据值
            
        Example:
            >>> with tracker.track("查询") as ctx:
            ...     ctx.add_metadata("model", "gpt-4")
            ...     ctx.add_metadata("temperature", 0.7)
        """
        if not self._active:
            raise RuntimeError("Execution context is not active")
        
        if self.execution.metadata is None:
            self.execution.metadata = {}
        
        self.execution.metadata[key] = value
    
    def add_intermediate_step(
        self,
        step_name: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加中间步骤
        
        记录智能体执行过程中的中间步骤，如工具调用、子任务等。
        
        Args:
            step_name: 步骤名称
            input_data: 步骤输入
            output_data: 步骤输出
            metadata: 步骤元数据
            
        Example:
            >>> with tracker.track("查询") as ctx:
            ...     # 步骤1：搜索
            ...     search_result = search_tool(query)
            ...     ctx.add_intermediate_step(
            ...         "search",
            ...         input_data=query,
            ...         output_data=search_result
            ...     )
            ...     # 步骤2：生成答案
            ...     answer = generate_answer(search_result)
            ...     ctx.set_output(answer)
        """
        if not self._active:
            raise RuntimeError("Execution context is not active")
        
        if self.execution.intermediate_steps is None:
            self.execution.intermediate_steps = []
        
        step = {
            "step_name": step_name,
            "timestamp": datetime.now().isoformat(),
            "input": input_data,
            "output": output_data,
        }
        
        if metadata:
            step["metadata"] = metadata
        
        self.execution.intermediate_steps.append(step)
    
    def complete(self) -> None:
        """
        完成执行
        
        标记执行完成并计算执行时间。如果没有设置输出，状态将保持为"running"。
        
        Example:
            >>> with tracker.track("查询") as ctx:
            ...     result = agent.run("查询")
            ...     ctx.set_output(result)
            ...     ctx.complete()  # 可选，with语句退出时会自动调用
        """
        if not self._active:
            return
        
        self.execution.end_time = datetime.now()
        
        # 如果没有设置输出且没有错误，标记为完成
        if not self._output_set and self.execution.status == "running":
            self.execution.status = "completed"
        
        self._active = False
    
    def __enter__(self) -> 'ExecutionContext':
        """
        进入上下文
        
        支持with语句，返回自身以便链式调用。
        
        Returns:
            ExecutionContext实例
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        退出上下文
        
        自动完成执行并保存到存储。
        如果发生异常，自动记录错误信息。
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪
        """
        if exc_val is not None:
            # 发生异常，记录错误
            self.set_error(exc_val)
        
        self.complete()
        
        # 保存到存储
        if self.tracker.storage:
            self.tracker.storage.save_execution(self.execution)


# =============================================================================
# 智能体追踪器
# =============================================================================

class AgentTracker:
    """
    智能体执行追踪器
    
    核心追踪类，管理智能体执行的记录、存储和检索。
    提供多种追踪方式：装饰器、上下文管理器或直接API。
    
    Attributes:
        storage: 存储后端实例
        auto_save: 是否自动保存执行记录
        _executions: 内存中的执行记录缓存
    
    Example:
        >>> # 初始化追踪器
        >>> tracker = AgentTracker(storage=JSONStorage("./data"))
        >>> 
        >>> # 方式1：使用track方法（上下文管理器）
        >>> with tracker.track("什么是AI？") as ctx:
        ...     result = agent.run("什么是AI？")
        ...     ctx.set_output(result)
        >>> 
        >>> # 方式2：手动控制
        >>> execution = tracker.start_execution("查询")
        >>> try:
        ...     result = agent.run("查询")
        ...     tracker.end_execution(execution, result)
        ... except Exception as e:
        ...     tracker.end_execution(execution, error=e)
        >>> 
        >>> # 获取执行历史
        >>> history = tracker.get_executions(limit=10)
    """
    
    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        auto_save: bool = True
    ):
        """
        初始化追踪器
        
        Args:
            storage: 存储后端实例，默认为None（不持久化）
            auto_save: 是否自动保存执行记录，默认为True
        """
        self.storage = storage
        self.auto_save = auto_save
        self._executions: List[AgentExecution] = []
    
    def start_execution(
        self,
        query: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentExecution:
        """
        开始追踪执行
        
        创建一个新的执行记录并开始追踪。
        
        Args:
            query: 输入查询
            agent_id: 智能体标识符
            metadata: 执行元数据
            
        Returns:
            AgentExecution实例
            
        Example:
            >>> tracker = AgentTracker()
            >>> execution = tracker.start_execution(
            ...     "什么是AI？",
            ...     agent_id="my_agent",
            ...     metadata={"version": "1.0"}
            ... )
        """
        execution = AgentExecution(
            id=str(uuid.uuid4()),
            query=query,
            agent_id=agent_id,
            start_time=datetime.now(),
            status="running",
            metadata=metadata or {}
        )
        
        self._executions.append(execution)
        
        return execution
    
    def end_execution(
        self,
        execution: AgentExecution,
        output: Any = None,
        error: Optional[Union[str, Exception]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentExecution:
        """
        结束执行追踪
        
        完成执行记录，设置输出或错误，并保存到存储。
        
        Args:
            execution: 执行记录实例
            output: 输出结果
            error: 错误信息
            metadata: 额外的元数据
            
        Returns:
            更新后的AgentExecution实例
            
        Example:
            >>> execution = tracker.start_execution("查询")
            >>> try:
            ...     result = agent.run("查询")
            ...     tracker.end_execution(execution, output=result)
            ... except Exception as e:
            ...     tracker.end_execution(execution, error=e)
        """
        execution.end_time = datetime.now()
        
        if error is not None:
            if isinstance(error, Exception):
                execution.error = f"{type(error).__name__}: {str(error)}"
            else:
                execution.error = str(error)
            execution.status = "error"
        elif output is not None:
            execution.output = output
            execution.status = "completed"
        else:
            execution.status = "completed"
        
        # 合并元数据
        if metadata:
            if execution.metadata is None:
                execution.metadata = {}
            execution.metadata.update(metadata)
        
        # 自动保存
        if self.auto_save and self.storage:
            self.storage.save_execution(execution)
        
        return execution
    
    @contextmanager
    def track(
        self,
        query: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        追踪执行的上下文管理器
        
        使用with语句自动管理执行的生命周期。
        
        Args:
            query: 输入查询
            agent_id: 智能体标识符
            metadata: 执行元数据
            
        Yields:
            ExecutionContext实例
            
        Example:
            >>> tracker = AgentTracker()
            >>> with tracker.track("什么是AI？") as ctx:
            ...     result = agent.run("什么是AI？")
            ...     ctx.set_output(result)
            ...     ctx.add_metadata("model", "gpt-4")
        """
        execution = self.start_execution(query, agent_id, metadata)
        context = ExecutionContext(execution=execution, tracker=self)
        
        try:
            yield context
        finally:
            if context._active:
                context.complete()
                if self.auto_save and self.storage:
                    self.storage.save_execution(execution)
    
    def get_executions(
        self,
        limit: Optional[int] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[AgentExecution]:
        """
        获取执行记录
        
        从内存缓存或存储后端检索执行记录。
        
        Args:
            limit: 返回的最大记录数
            agent_id: 按智能体ID过滤
            status: 按状态过滤（running/completed/error）
            
        Returns:
            AgentExecution列表
            
        Example:
            >>> # 获取所有记录
            >>> all_executions = tracker.get_executions()
            >>> 
            >>> # 获取最近的10条
            >>> recent = tracker.get_executions(limit=10)
            >>> 
            >>> # 获取特定智能体的记录
            >>> agent_executions = tracker.get_executions(agent_id="my_agent")
            >>> 
            >>> # 获取失败的记录
            >>> errors = tracker.get_executions(status="error")
        """
        executions = self._executions.copy()
        
        # 从存储加载更多记录
        if self.storage:
            stored = self.storage.load_executions()
            # 合并并去重
            existing_ids = {e.id for e in executions}
            for e in stored:
                if e.id not in existing_ids:
                    executions.append(e)
        
        # 过滤
        if agent_id:
            executions = [e for e in executions if e.agent_id == agent_id]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        # 按开始时间排序（最新的在前）
        executions.sort(key=lambda e: e.start_time, reverse=True)
        
        # 限制数量
        if limit:
            executions = executions[:limit]
        
        return executions
    
    def get_execution(self, execution_id: str) -> Optional[AgentExecution]:
        """
        获取单个执行记录
        
        Args:
            execution_id: 执行记录ID
            
        Returns:
            AgentExecution实例，如果不存在则返回None
            
        Example:
            >>> execution = tracker.get_execution("uuid-123")
            >>> if execution:
            ...     print(f"查询: {execution.query}")
            ...     print(f"状态: {execution.status}")
        """
        # 先在内存中查找
        for e in self._executions:
            if e.id == execution_id:
                return e
        
        # 从存储加载
        if self.storage:
            return self.storage.load_execution(execution_id)
        
        return None
    
    def clear_cache(self) -> None:
        """
        清除内存缓存
        
        清除内存中的执行记录缓存，不影响存储后端的数据。
        
        Example:
            >>> tracker.clear_cache()
            >>> print(f"缓存记录数: {len(tracker._executions)}")  # 0
        """
        self._executions.clear()
    
    def decorator(
        self,
        query_arg: str = "query",
        agent_id: Optional[str] = None
    ) -> Callable:
        """
        创建追踪装饰器
        
        为函数创建装饰器，自动追踪函数的执行。
        
        Args:
            query_arg: 包含查询字符串的参数名称
            agent_id: 智能体标识符
            
        Returns:
            装饰器函数
            
        Example:
            >>> tracker = AgentTracker()
            >>> 
            >>> @tracker.decorator(query_arg="question")
            ... def answer_question(question, **kwargs):
            ...     return agent.run(question)
            >>> 
            >>> result = answer_question("什么是AI？")
            >>> # 执行自动被追踪
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # 从参数中提取查询
                query = kwargs.get(query_arg, "")
                if not query and args:
                    # 尝试从位置参数获取
                    import inspect
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    if query_arg in params:
                        idx = params.index(query_arg)
                        if idx < len(args):
                            query = args[idx]
                
                # 使用上下文管理器追踪执行
                with self.track(query=query, agent_id=agent_id or func.__name__) as ctx:
                    try:
                        result = func(*args, **kwargs)
                        ctx.set_output(result)
                        return result
                    except Exception as e:
                        ctx.set_error(e)
                        raise
            
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            return wrapper
        
        return decorator


# =============================================================================
# 便捷装饰器函数
# =============================================================================

def track_agent(
    query_arg: str = "query",
    storage: Optional[BaseStorage] = None,
    agent_id: Optional[str] = None
) -> Callable:
    """
    智能体执行追踪装饰器
    
    用于装饰智能体函数，自动追踪函数的执行过程。
    这是一个便捷的顶层函数，内部创建AgentTracker实例。
    
    Args:
        query_arg: 包含查询字符串的参数名称，默认为"query"
        storage: 存储后端实例，可选
        agent_id: 智能体标识符，可选，默认为函数名
        
    Returns:
        装饰器函数
        
    Example:
        >>> from agent_eval.tracker import track_agent
        >>> from agent_eval.storage import JSONStorage
        >>> 
        >>> storage = JSONStorage("./data")
        >>> 
        >>> @track_agent(storage=storage)
        ... def my_agent(query, **kwargs):
        ...     # 智能体逻辑
        ...     return result
        >>> 
        >>> result = my_agent("什么是AI？")
        >>> # 执行自动被追踪和保存
        
        >>> # 自定义参数名
        >>> @track_agent(query_arg="question")
        ... def answer(question, **kwargs):
        ...     return agent.run(question)
    """
    tracker = AgentTracker(storage=storage)
    return tracker.decorator(query_arg=query_arg, agent_id=agent_id)
