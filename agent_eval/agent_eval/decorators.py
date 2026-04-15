"""
基于装饰器的集成模块 - 提供非侵入式装饰器用于追踪函数、工具和智能体执行

本模块是AgentEval系统的核心集成层，通过Python装饰器实现零代码侵入的执行追踪。
用户只需在现有函数上添加装饰器，即可自动记录执行详情，无需修改原有业务逻辑。

主要功能：
- @track_agent: 追踪智能体执行
- @track_tool: 追踪工具调用
- @track_step: 追踪执行步骤
- TrackedExecution: 上下文管理器，用于手动追踪

使用示例：
    from agent_eval.decorators import track_agent, track_tool, configure_storage
    from agent_eval.models import StorageConfig, StorageType
    
    # 配置存储后端
    configure_storage(StorageConfig(
        storage_type=StorageType.JSON,
        file_path="evaluations.json"
    ))
    
    # 追踪工具
    @track_tool(tool_name="search")
    def search_api(query: str):
        return f"搜索结果: {query}"
    
    # 追踪智能体
    @track_agent(query_arg="query")
    def my_agent(query: str):
        result = search_api(query)
        return f"回答: {result}"
    
    # 执行时会自动追踪
    result = my_agent("什么是人工智能？")
"""

import functools
import time
import uuid
from contextvars import ContextVar, Token
from typing import Any, Callable, Dict, List, Optional, Union

from agent_eval.models import AgentExecution, StepDetail, ToolCallDetail
from agent_eval.storages import BaseStorage, create_storage, StorageConfig


# =============================================================================
# 全局状态管理
# =============================================================================

# 全局执行记录存储 - 用于临时存储所有执行记录
# key: execution_id (str), value: AgentExecution
_execution_storage: Dict[str, AgentExecution] = {}

# 活跃执行会话 - 用于追踪当前正在进行的执行
# 支持嵌套调用和并发追踪
# key: execution_id (str), value: AgentExecution
_active_executions: Dict[str, AgentExecution] = {}

# 全局存储后端 - 用于持久化存储执行记录
_global_storage_backend: Optional[BaseStorage] = None

# 上下文变量 - 用于在异步/并发环境下正确追踪当前执行
# 使用 ContextVar 替代全局字典，确保每个执行流有独立的上下文
_current_execution_id: ContextVar[Optional[str]] = ContextVar('execution_id', default=None)
_current_execution: ContextVar[Optional[AgentExecution]] = ContextVar('execution', default=None)


def get_current_execution_id() -> Optional[str]:
    """
    获取当前执行上下文的执行ID
    
    使用 ContextVar 获取当前执行流的执行ID，支持并发和异步环境。
    
    Returns:
        当前执行ID，如果没有活跃执行则返回None
        
    Example:
        >>> exec_id = get_current_execution_id()
        >>> if exec_id:
        ...     print(f"当前执行ID: {exec_id}")
    """
    return _current_execution_id.get()


def get_current_execution() -> Optional[AgentExecution]:
    """
    获取当前执行上下文的执行记录
    
    使用 ContextVar 获取当前执行流的 AgentExecution 对象。
    优先从上下文变量获取，如果未设置则回退到全局字典的最后一个活跃执行。
    
    Returns:
        当前 AgentExecution 对象，如果没有活跃执行则返回None
        
    Example:
        >>> execution = get_current_execution()
        >>> if execution:
        ...     print(f"当前查询: {execution.query}")
    """
    # 优先从 ContextVar 获取（支持并发/异步）
    exec_from_ctx = _current_execution.get()
    if exec_from_ctx is not None:
        return exec_from_ctx
    
    # 回退到全局字典（兼容旧代码）
    if _active_executions:
        return list(_active_executions.values())[-1]
    
    return None


def _set_current_execution(execution: AgentExecution) -> Token:
    """
    设置当前执行上下文
    
    内部函数，用于在执行开始时设置上下文变量。
    
    Args:
        execution: AgentExecution 对象
        
    Returns:
        Token 对象，用于后续重置上下文
    """
    token_id = _current_execution_id.set(execution.execution_id)
    token_exec = _current_execution.set(execution)
    return token_id, token_exec


def _reset_current_execution(token_id: Token, token_exec: Token) -> None:
    """
    重置当前执行上下文
    
    内部函数，用于在执行结束时重置上下文变量。
    
    Args:
        token_id: 执行ID的 Token
        token_exec: 执行对象的 Token
    """
    _current_execution_id.reset(token_id)
    _current_execution.reset(token_exec)


def configure_storage(config: StorageConfig):
    """
    配置全局存储后端
    
    在使用装饰器追踪之前，需要先配置存储后端，否则执行记录只会保存在内存中。
    支持的存储类型：JSON文件、CSV文件、SQLite数据库、PostgreSQL数据库
    
    Args:
        config: 存储配置对象，包含存储类型和连接参数
        
    Example:
        >>> from agent_eval.models import StorageConfig, StorageType
        >>> configure_storage(StorageConfig(
        ...     storage_type=StorageType.SQLITE,
        ...     file_path="evaluations.db"
        ... ))
    """
    global _global_storage_backend
    _global_storage_backend = create_storage(config)


def get_execution(execution_id: str) -> Optional[AgentExecution]:
    """
    根据执行ID获取执行记录
    
    优先从内存缓存中查找，如果未找到且配置了持久化存储，则从存储中读取。
    
    Args:
        execution_id: 执行记录的唯一标识符
        
    Returns:
        AgentExecution对象，如果未找到则返回None
        
    Example:
        >>> execution = get_execution("550e8400-e29b-41d4-a716-446655440000")
        >>> if execution:
        ...     print(f"查询: {execution.query}")
        ...     print(f"输出: {execution.final_output}")
    """
    if execution_id in _execution_storage:
        return _execution_storage[execution_id]
    if _global_storage_backend:
        return _global_storage_backend.get_execution(execution_id)
    return None


def get_last_execution() -> Optional[AgentExecution]:
    """
    获取最近一次执行记录
    
    从内存缓存中获取最后添加的执行记录。适用于快速查看最近一次执行结果。
    
    Returns:
        最近的AgentExecution对象，如果没有执行记录则返回None
        
    Example:
        >>> execution = get_last_execution()
        >>> if execution:
        ...     print(f"最近查询: {execution.query}")
        ...     print(f"执行时间: {execution.total_duration_ms}ms")
    """
    if _execution_storage:
        return list(_execution_storage.values())[-1]
    return None


def list_executions(limit: int = 100) -> List[AgentExecution]:
    """
    列出所有执行记录
    
    合并内存缓存和持久化存储中的执行记录，并去重。
    返回按时间排序的最近limit条记录。
    
    Args:
        limit: 返回的最大记录数，默认100条
        
    Returns:
        AgentExecution对象列表
        
    Example:
        >>> executions = list_executions(limit=10)
        >>> for exec in executions:
        ...     print(f"{exec.query}: {exec.success}")
    """
    executions = list(_execution_storage.values())
    if _global_storage_backend:
        stored = _global_storage_backend.list_executions(limit)
        # 合并并去重
        seen_ids = {e.execution_id for e in executions}
        for e in stored:
            if e.execution_id not in seen_ids:
                executions.append(e)
    return executions[-limit:]


# =============================================================================
# 执行追踪上下文管理器
# =============================================================================

class TrackedExecution:
    """
    执行追踪上下文管理器
    
    用于手动追踪智能体执行的上下文管理器。支持使用with语句自动管理执行生命周期，
    包括开始追踪、记录步骤和工具调用、自动保存执行记录。
    
    Attributes:
        query: 用户查询字符串
        metadata: 执行相关的元数据字典
        storage: 存储后端实例
        execution: 当前的AgentExecution对象
        _step_counter: 步骤计数器
        _tool_counter: 工具调用计数器
        _start_time: 执行开始时间戳
        
    Example:
        >>> with TrackedExecution("什么是AI？", {"source": "web"}) as exec:
        ...     # 执行智能体逻辑
        ...     result = agent.run("什么是AI？")
        ...     exec.set_output(result)
        ...     # 记录步骤
        ...     exec.add_step("分析查询", input="什么是AI？", output="概念查询")
        >>> # 退出上下文后，执行记录自动保存
    """
    
    def __init__(self, query: str, metadata: Optional[Dict] = None, storage: Optional[BaseStorage] = None):
        """
        初始化追踪执行上下文
        
        Args:
            query: 用户查询字符串
            metadata: 可选的元数据字典，用于存储额外信息
            storage: 可选的存储后端，默认使用全局存储后端
        """
        self.query = query
        self.metadata = metadata or {}
        self.storage = storage or _global_storage_backend
        self.execution: Optional[AgentExecution] = None
        self._step_counter = 0
        self._tool_counter = 0
        self._start_time = None
        self._context_tokens: Optional[tuple] = None  # 用于存储上下文变量的token
    
    def __enter__(self):
        """
        进入上下文，开始追踪执行
        
        创建新的AgentExecution对象，记录开始时间，并将其添加到活跃执行字典中。
        同时设置上下文变量，确保在当前执行流中工具/步骤能正确关联到此执行。
        
        Returns:
            TrackedExecution实例自身，用于链式调用
        """
        from datetime import datetime
        self._start_time = time.time()
        self.execution = AgentExecution(
            execution_id=str(uuid.uuid4()),
            query=self.query,
            metadata=self.metadata,
            start_time=datetime.now()
        )
        # 添加到全局活跃执行字典（向后兼容）
        _active_executions[self.execution.execution_id] = self.execution
        
        # 设置上下文变量（支持并发/异步）
        # 这使得在当前执行流中，工具/步骤装饰器能通过 get_current_execution() 获取此执行
        self._context_tokens = _set_current_execution(self.execution)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文，结束追踪执行
        
        记录结束时间、计算总耗时、标记执行状态（成功/失败）。
        将执行记录保存到内存缓存和持久化存储（如果配置了）。
        从活跃执行字典中移除当前执行，并重置上下文变量。
        
        Args:
            exc_type: 异常类型，如果有异常发生
            exc_val: 异常值，如果有异常发生
            exc_tb: 异常追踪信息，如果有异常发生
            
        Returns:
            False，表示不抑制异常，让异常继续传播
        """
        from datetime import datetime
        if self.execution:
            self.execution.end_time = datetime.now()
            if self._start_time:
                self.execution.total_duration_ms = (time.time() - self._start_time) * 1000
            self.execution.success = exc_type is None
            if exc_val:
                self.execution.has_error = True
                self.execution.error_message = str(exc_val)
            
            # 保存到内存存储
            _execution_storage[self.execution.execution_id] = self.execution
            # 保存到持久化存储
            if self.storage:
                self.storage.save_execution(self.execution)
            
            # 从活跃执行中移除
            if self.execution.execution_id in _active_executions:
                del _active_executions[self.execution.execution_id]
        
        # 重置上下文变量
        if self._context_tokens:
            _reset_current_execution(self._context_tokens[0], self._context_tokens[1])
        
        return False  # 不抑制异常
    
    def add_step(self, description: str, step_input: Any = None, step_output: Any = None, 
                 success: bool = True, err_msg: Optional[str] = None):
        """
        添加执行步骤
        
        记录智能体执行过程中的一个步骤，包括步骤描述、输入输出、执行状态等。
        自动更新步骤计数和步骤摘要。
        
        Args:
            description: 步骤描述，例如"分析查询意图"
            step_input: 步骤输入数据
            step_output: 步骤输出数据
            success: 步骤是否成功执行
            err_msg: 如果失败，错误信息
            
        Example:
            >>> with TrackedExecution("查询天气") as exec:
            ...     exec.add_step("解析地点", input="北京天气", output="地点: 北京")
            ...     exec.add_step("获取数据", input="北京", output="晴天 25°C")
        """
        if not self.execution:
            return
        
        self._step_counter += 1
        step = StepDetail(
            step=self._step_counter,
            description=description,
            input=step_input,
            output=step_output,
            success=success,
            err_msg=err_msg
        )
        self.execution.steps_detail.append(step)
        self.execution.step_count = self._step_counter
        
        # 更新步骤摘要
        if self.execution.steps_summary:
            self.execution.steps_summary += f"\n第{self._step_counter}步执行{description}"
        else:
            self.execution.steps_summary = f"第{self._step_counter}步执行{description}"
    
    def add_tool_call(self, tool_name: str, tool_input: Dict, tool_output: Any = None,
                      duration_ms: Optional[float] = None, success: bool = True,
                      err_msg: Optional[str] = None):
        """
        添加工具调用记录
        
        记录智能体调用外部工具的详细信息，包括工具名称、输入参数、输出结果、执行耗时等。
        
        Args:
            tool_name: 工具名称，例如"search", "calculator"
            tool_input: 工具输入参数字典
            tool_output: 工具执行输出
            duration_ms: 工具执行耗时（毫秒）
            success: 工具调用是否成功
            err_msg: 如果失败，错误信息
            
        Example:
            >>> with TrackedExecution("计算") as exec:
            ...     exec.add_tool_call(
            ...         "calculator",
            ...         {"expression": "1+1"},
            ...         output="2",
            ...         duration_ms=50
            ...     )
        """
        if not self.execution:
            return
        
        self._tool_counter += 1
        tool_call = ToolCallDetail(
            name=tool_name,
            input=tool_input,
            output=tool_output,
            time=duration_ms,
            success=success,
            err_msg=err_msg
        )
        self.execution.tool_calls_detail.append(tool_call)
        self.execution.tool_call_count = self._tool_counter
    
    def set_output(self, output: str):
        """
        设置最终输出结果
        
        设置智能体执行的最终输出/回答。
        
        Args:
            output: 最终输出字符串
            
        Example:
            >>> with TrackedExecution("问问题") as exec:
            ...     result = agent.process("问问题")
            ...     exec.set_output(result)
        """
        if self.execution:
            self.execution.final_output = output


# =============================================================================
# 装饰器函数
# =============================================================================

def track_agent(query_arg: str = "query", storage: Optional[BaseStorage] = None):
    """
    智能体执行追踪装饰器
    
    用于装饰智能体函数，自动追踪函数的执行过程，包括参数、返回值、执行时间等。
    支持从函数参数中自动提取查询字符串。
    
    Args:
        query_arg: 包含查询字符串的参数名称，默认为"query"
        storage: 存储后端实例，可选，默认使用全局存储后端
        
    Returns:
        装饰器函数
        
    Example:
        >>> @track_agent()
        ... def my_agent(query, **kwargs):
        ...     # 智能体逻辑
        ...     return result
        ... 
        >>> result = my_agent("什么是AI？")
        >>> # 执行自动被追踪和保存
        
        >>> @track_agent(query_arg="question")
        ... def qa_bot(question, context=None):
        ...     return answer
        ... 
        >>> answer = qa_bot("什么是机器学习？")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 从kwargs中提取query
            query = kwargs.get(query_arg)
            if query is None and args:
                # 尝试从位置参数中获取
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                if query_arg in params:
                    idx = params.index(query_arg)
                    if idx < len(args):
                        query = args[idx]
            
            if query is None:
                query = "Unknown query"
            
            with TrackedExecution(query, {"function": func.__name__}, storage or _global_storage_backend) as exec:
                try:
                    result = func(*args, **kwargs)
                    exec.set_output(str(result) if result else "")
                    return result
                except Exception as e:
                    exec.execution.has_error = True
                    exec.execution.error_message = str(e)
                    raise
        return wrapper
    return decorator


def track_tool(tool_name: Optional[str] = None, storage: Optional[BaseStorage] = None):
    """
    工具调用追踪装饰器
    
    用于装饰工具函数，自动追踪工具的调用过程，包括输入参数、输出结果、执行耗时等。
    工具调用会被关联到当前活跃的智能体执行记录中。
    
    Args:
        tool_name: 工具名称，默认为被装饰函数的名称
        storage: 存储后端实例，可选
        
    Returns:
        装饰器函数
        
    Example:
        >>> @track_tool("search")
        ... def search_tool(query: str):
        ...     # 搜索逻辑
        ...     return results
        ... 
        >>> # 工具调用自动被追踪
        
        >>> @track_tool()  # 使用函数名作为工具名
        ... def calculator(expression: str):
        ...     return eval(expression)
    """
    def decorator(func: Callable) -> Callable:
        nonlocal tool_name
        if tool_name is None:
            tool_name = func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 使用 get_current_execution() 获取当前执行上下文
            # 支持 ContextVar（并发/异步）和全局字典（向后兼容）
            active_exec = get_current_execution()
            exec_id = get_current_execution_id()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # 如果有活跃执行，记录工具调用
                if active_exec:
                    tool_input = _build_tool_input(args, kwargs, func)
                    active_exec.tool_calls_detail.append(ToolCallDetail(
                        name=tool_name,
                        input=tool_input,
                        output=result,
                        time=duration_ms,
                        success=True
                    ))
                    active_exec.tool_call_count = len(active_exec.tool_calls_detail)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                if active_exec:
                    tool_input = _build_tool_input(args, kwargs, func)
                    active_exec.tool_calls_detail.append(ToolCallDetail(
                        name=tool_name,
                        input=tool_input,
                        output=None,
                        time=duration_ms,
                        success=False,
                        err_msg=str(e)
                    ))
                    active_exec.tool_call_count = len(active_exec.tool_calls_detail)
                raise
        
        return wrapper
    return decorator


def track_step(step_name: Optional[str] = None, storage: Optional[BaseStorage] = None):
    """
    执行步骤追踪装饰器
    
    用于装饰执行步骤函数，自动追踪步骤的执行过程。步骤会被关联到当前活跃的智能体执行记录中。
    
    Args:
        step_name: 步骤名称，默认为被装饰函数的名称
        storage: 存储后端实例，可选
        
    Returns:
        装饰器函数
        
    Example:
        >>> @track_step("parse_query")
        ... def parse_query(query: str):
        ...     # 解析逻辑
        ...     return parsed
        ... 
        >>> # 步骤自动被追踪
        
        >>> @track_step()  # 使用函数名作为步骤名
        ... def retrieve_documents(query: str):
        ...     return docs
    """
    def decorator(func: Callable) -> Callable:
        nonlocal step_name
        if step_name is None:
            step_name = func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # 使用 get_current_execution() 获取当前执行上下文
            # 支持 ContextVar（并发/异步）和全局字典（向后兼容）
            active_exec = get_current_execution()
            exec_id = get_current_execution_id()
            
            # 计算步骤序号
            step_num = 1
            if active_exec:
                step_num = len(active_exec.steps_detail) + 1
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                if active_exec:
                    step_input = _build_tool_input(args, kwargs, func)
                    active_exec.steps_detail.append(StepDetail(
                        step=step_num,
                        description=step_name,
                        input=step_input,
                        output=result,
                        time=duration_ms,
                        success=True
                    ))
                    active_exec.step_count = len(active_exec.steps_detail)
                    
                    # 更新步骤摘要
                    if active_exec.steps_summary:
                        active_exec.steps_summary += f"\n第{step_num}步执行{step_name}"
                    else:
                        active_exec.steps_summary = f"第{step_num}步执行{step_name}"
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                if active_exec:
                    step_input = _build_tool_input(args, kwargs, func)
                    active_exec.steps_detail.append(StepDetail(
                        step=step_num,
                        description=step_name,
                        input=step_input,
                        output=None,
                        time=duration_ms,
                        success=False,
                        err_msg=str(e)
                    ))
                    active_exec.step_count = len(active_exec.steps_detail)
                raise
        
        return wrapper
    return decorator


def _build_tool_input(args: tuple, kwargs: dict, func: Callable) -> Dict[str, Any]:
    """
    从函数参数构建工具输入字典
    
    使用inspect模块获取函数签名，将位置参数和关键字参数合并为字典。
    
    Args:
        args: 位置参数元组
        kwargs: 关键字参数字典
        func: 被调用的函数
        
    Returns:
        包含所有参数的字典
        
    Example:
        >>> def my_func(a, b, c=3):
        ...     pass
        >>> _build_tool_input((1, 2), {"c": 4}, my_func)
        {"a": 1, "b": 2, "c": 4}
    """
    import inspect
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())
    
    input_dict = {}
    for i, arg in enumerate(args):
        if i < len(params):
            input_dict[params[i]] = arg
    
    input_dict.update(kwargs)
    return input_dict


# =============================================================================
# 便捷函数
# =============================================================================

def track(query: str, metadata: Optional[Dict] = None, storage: Optional[BaseStorage] = None):
    """
    快速追踪上下文管理器
    
    便捷的上下文管理器函数，用于快速创建TrackedExecution。
    
    Args:
        query: 用户查询字符串
        metadata: 可选的元数据字典
        storage: 可选的存储后端
        
    Returns:
        TrackedExecution上下文管理器
        
    Example:
        >>> with track("什么是AI？") as exec:
        ...     result = agent.run("什么是AI？")
        ...     exec.set_output(result)
        >>> # 执行记录自动保存
    """
    return TrackedExecution(query, metadata, storage)


# =============================================================================
# 使用示例和说明
# =============================================================================

"""
执行上下文关联机制说明
========================

本模块使用 ContextVar 来确保在并发和嵌套场景下，工具/步骤能正确关联到对应的 Agent 执行。

核心机制：
1. 当 Agent 开始执行时（通过 @track_agent 或 TrackedExecution），会设置上下文变量 _current_execution
2. 工具/步骤装饰器通过 get_current_execution() 获取当前执行上下文
3. 执行结束时，上下文变量自动重置

这种机制支持：
- 并发执行：每个线程/协程有独立的上下文
- 嵌套调用：Agent A 调用 Agent B，各自有独立的上下文
- 异步执行：asyncio 任务间上下文隔离

使用示例：

    # 示例1：基本使用
    @track_tool("search")
    def search_tool(query: str):
        return f"搜索结果: {query}"
    
    @track_agent()
    def my_agent(query: str):
        # search_tool 会自动关联到 my_agent 的当前执行
        result = search_tool(query)
        return f"回答: {result}"
    
    result = my_agent("什么是AI？")
    
    # 示例2：并发执行（线程安全）
    import threading
    
    def run_agent(query):
        result = my_agent(query)
        exec_id = get_current_execution_id()
        print(f"查询 '{query}' 的执行ID: {exec_id}")
    
    threads = [
        threading.Thread(target=run_agent, args=("问题1",)),
        threading.Thread(target=run_agent, args=("问题2",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 每个线程有独立的执行ID，不会混淆
    
    # 示例3：获取当前执行信息
    @track_tool("calculator")
    def calculator(expr: str):
        exec_id = get_current_execution_id()
        execution = get_current_execution()
        if execution:
            print(f"当前执行查询: {execution.query}")
        return eval(expr)
    
    # 示例4：检查是否在执行上下文中
    @track_tool("helper")
    def helper():
        execution = get_current_execution()
        if execution:
            print("在Agent执行上下文中")
            # 可以添加步骤、工具调用等
        else:
            print("独立调用，无Agent上下文")
        return "done"
    
    # 独立调用（不关联到任何Agent执行）
    helper()  # 输出: 独立调用，无Agent上下文
    
    # 在Agent中调用
    @track_agent()
    def agent_with_helper(query: str):
        return helper()  # 输出: 在Agent执行上下文中
"""
