"""
执行录制模块 - 用于追踪智能体执行的详细信息

本模块提供了传统的录制接口，通过ExecutionRecorder类实现更细粒度的执行控制。
适合需要精确控制录制时机的场景，支持手动录制、上下文管理器和装饰器三种使用方式。

主要组件：
- ExecutionRecord: 单个执行记录的数据容器
- ExecutionRecorder: 执行录制器，支持多种录制模式
- ToolCallTracker: 工具调用追踪辅助类

使用示例：
    # 方式1：使用上下文管理器
    recorder = ExecutionRecorder()
    with recorder.record("什么是AI？") as record:
        result = agent.run("什么是AI？")
        record.set_output(result)
    
    # 方式2：手动控制录制
    recorder.start_recording("什么是AI？")
    recorder.record_step("解析查询")
    result = agent.run("什么是AI？")
    execution = recorder.end_recording(final_output=result)
    
    # 方式3：使用装饰器
    @recorder.decorator
    def my_agent(query):
        return agent.run(query)
    
    result = my_agent("什么是AI？")
"""

import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from agent_eval.models import (
    AgentExecution,
    StepDetail,
    ToolCallDetail,
)


# =============================================================================
# 执行记录类
# =============================================================================

class ExecutionRecord:
    """
    执行记录数据容器 - 与新的数据模型兼容
    
    用于存储单个智能体执行的完整信息，包括查询、步骤、工具调用、输出等。
    提供将记录转换为标准AgentExecution模型的方法。
    
    Attributes:
        execution_id: 执行记录唯一标识符
        query: 用户查询字符串
        steps_detail: 详细步骤列表
        tool_calls_detail: 工具调用详情列表
        steps_summary: 步骤摘要文本
        final_output: 最终输出结果
        success: 执行是否成功
        has_error: 是否发生错误
        error_message: 错误信息
        metadata: 元数据字典
        start_time: 开始时间
        end_time: 结束时间
        created_at: 创建时间
        _step_counter: 步骤计数器（内部使用）
        _tool_counter: 工具调用计数器（内部使用）
        _current_step_start: 当前步骤开始时间（内部使用）
    
    Example:
        >>> record = ExecutionRecord(query="什么是AI？")
        >>> record.start()
        >>> record.add_step("解析查询", input="什么是AI？", output="概念查询")
        >>> record.add_tool_call("search", {"q": "AI"}, result="人工智能是...")
        >>> record.set_output("人工智能是...")
        >>> record.end(success=True)
        >>> execution = record.to_agent_execution()
    """

    def __init__(
        self,
        execution_id: Optional[str] = None,
        query: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化执行记录
        
        Args:
            execution_id: 可选的执行ID，默认自动生成UUID
            query: 用户查询字符串
            metadata: 可选的元数据字典
        """
        self.execution_id = execution_id or str(uuid.uuid4())
        self.query = query
        self.steps_detail: List[StepDetail] = []
        self.tool_calls_detail: List[ToolCallDetail] = []
        self.steps_summary: str = ""
        self.final_output: Optional[str] = None
        self.success: bool = False
        self.has_error: bool = False
        self.error_message: Optional[str] = None
        self.metadata = metadata or {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.created_at = datetime.now()
        self._step_counter = 0
        self._tool_counter = 0
        self._current_step_start: Optional[float] = None

    def start(self):
        """
        开始录制执行
        
        记录开始时间和初始化步骤计时器。应在执行开始前调用。
        
        Example:
            >>> record = ExecutionRecord(query="测试")
            >>> record.start()
            >>> # 执行智能体逻辑
            >>> record.end()
        """
        self.start_time = datetime.now()
        self._current_step_start = time.time()

    def end(self, success: bool = True, error_message: Optional[str] = None):
        """
        结束录制执行
        
        记录结束时间，标记执行状态。应在执行结束后调用。
        
        Args:
            success: 执行是否成功
            error_message: 如果失败，错误信息
            
        Example:
            >>> record.end(success=True)
            >>> # 或
            >>> record.end(success=False, error_message="网络错误")
        """
        self.end_time = datetime.now()
        self.success = success and not self.has_error
        if error_message:
            self.error_message = error_message
            self.has_error = True
            self.success = False

    def add_step(
        self,
        description: str,
        step_input: Any = None,
        step_output: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StepDetail:
        """
        添加执行步骤
        
        记录智能体执行过程中的一个步骤。自动计算步骤耗时并更新步骤摘要。
        
        Args:
            description: 步骤描述，例如"解析查询意图"
            step_input: 步骤输入数据
            step_output: 步骤输出数据
            metadata: 可选的元数据字典
            
        Returns:
            创建的StepDetail对象
            
        Example:
            >>> record.add_step("解析查询", input="北京天气", output="地点: 北京")
            >>> record.add_step("获取数据", input="北京", output="晴天 25°C")
        """
        self._step_counter += 1
        
        # 计算步骤耗时
        current_time = time.time()
        duration_ms = None
        if self._current_step_start:
            duration_ms = (current_time - self._current_step_start) * 1000
        self._current_step_start = current_time
        
        step = StepDetail(
            step=self._step_counter,
            description=description,
            input=step_input,
            output=step_output,
            time=duration_ms,
            success=True,
            metadata=metadata or {}
        )
        
        self.steps_detail.append(step)
        
        # 更新步骤摘要
        if self.steps_summary:
            self.steps_summary += f"\n第{self._step_counter}步执行{description}"
        else:
            self.steps_summary = f"第{self._step_counter}步执行{description}"
        
        return step

    def add_tool_call(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        err_msg: Optional[str] = None
    ) -> ToolCallDetail:
        """
        添加工具调用记录
        
        记录智能体调用外部工具的详细信息。
        
        Args:
            tool_name: 工具名称
            arguments: 工具输入参数
            result: 工具执行结果
            duration_ms: 执行耗时（毫秒）
            success: 工具调用是否成功
            err_msg: 如果失败，错误信息
            
        Returns:
            创建的ToolCallDetail对象
            
        Example:
            >>> record.add_tool_call(
            ...     "search",
            ...     arguments={"q": "AI"},
            ...     result="人工智能是...",
            ...     duration_ms=150
            ... )
        """
        self._tool_counter += 1
        
        tool_call = ToolCallDetail(
            name=tool_name,
            input=arguments or {},
            output=result,
            time=duration_ms,
            success=success,
            err_msg=err_msg
        )
        
        self.tool_calls_detail.append(tool_call)
        
        return tool_call

    def set_output(self, output: str):
        """
        设置最终输出结果
        
        Args:
            output: 最终输出字符串
            
        Example:
            >>> result = agent.process("查询")
            >>> record.set_output(result)
        """
        self.final_output = output

    def set_error(self, error_message: str):
        """
        设置错误信息
        
        标记执行出错并记录错误信息。
        
        Args:
            error_message: 错误描述
            
        Example:
            >>> try:
            ...     result = agent.process("查询")
            ... except Exception as e:
            ...     record.set_error(str(e))
        """
        self.error_message = error_message
        self.has_error = True
        self.success = False

    def to_agent_execution(self) -> AgentExecution:
        """
        转换为AgentExecution模型
        
        将ExecutionRecord转换为标准的AgentExecution数据模型，
        便于存储和后续处理。
        
        Returns:
            AgentExecution对象
            
        Example:
            >>> execution = record.to_agent_execution()
            >>> storage.save_execution(execution)
        """
        total_duration_ms = None
        if self.start_time and self.end_time:
            total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        
        return AgentExecution(
            execution_id=self.execution_id,
            query=self.query,
            steps_summary=self.steps_summary,
            steps_detail=self.steps_detail,
            tool_call_count=self._tool_counter,
            tool_calls_detail=self.tool_calls_detail,
            step_count=self._step_counter,
            final_output=self.final_output,
            success=self.success,
            has_error=self.has_error,
            error_message=self.error_message,
            total_duration_ms=total_duration_ms,
            start_time=self.start_time,
            end_time=self.end_time,
            metadata=self.metadata,
            created_at=self.created_at
        )


# =============================================================================
# 执行录制器类
# =============================================================================

class ExecutionRecorder:
    """
    执行录制器 - 自动记录智能体执行详情
    
    提供三种使用方式：
    1. 上下文管理器：使用with语句自动管理录制生命周期
    2. 手动控制：显式调用start_recording和end_recording
    3. 装饰器：使用decorator方法包装函数
    
    Attributes:
        storage: 存储后端实例
        auto_save: 是否自动保存到存储
        on_record_complete: 录制完成时的回调函数
        _current_record: 当前活跃的执行记录
        _records: 所有执行记录列表
    
    Example:
        >>> # 方式1：上下文管理器
        >>> recorder = ExecutionRecorder(storage=my_storage)
        >>> with recorder.record("什么是AI？") as record:
        ...     result = agent.run("什么是AI？")
        ...     record.set_output(result)
        
        >>> # 方式2：手动控制
        >>> recorder.start_recording("什么是AI？")
        >>> recorder.record_step("解析查询")
        >>> result = agent.run("什么是AI？")
        >>> execution = recorder.end_recording(final_output=result)
        
        >>> # 方式3：装饰器
        >>> @recorder.decorator
        >>> def my_agent(query):
        ...     return agent.run(query)
    """

    def __init__(
        self,
        storage=None,
        auto_save: bool = True,
        on_record_complete: Optional[Callable[[AgentExecution], None]] = None
    ):
        """
        初始化执行录制器
        
        Args:
            storage: 存储后端实例，用于持久化存储
            auto_save: 是否自动保存执行记录，默认为True
            on_record_complete: 录制完成时的回调函数，接收AgentExecution对象
        """
        self.storage = storage
        self.auto_save = auto_save
        self.on_record_complete = on_record_complete
        self._current_record: Optional[ExecutionRecord] = None
        self._records: List[ExecutionRecord] = []

    @property
    def current_record(self) -> Optional[ExecutionRecord]:
        """
        获取当前录制会话
        
        Returns:
            当前活跃的ExecutionRecord对象，如果没有活跃会话则返回None
        """
        return self._current_record

    def start_recording(
        self,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExecutionRecord:
        """
        开始新的录制会话
        
        创建新的ExecutionRecord并开始录制。必须在调用其他录制方法之前调用。
        
        Args:
            query: 用户查询字符串
            metadata: 可选的元数据字典
            
        Returns:
            新创建的ExecutionRecord对象
            
        Example:
            >>> recorder = ExecutionRecorder()
            >>> record = recorder.start_recording("什么是AI？", {"user_id": "123"})
        """
        record = ExecutionRecord(
            query=query,
            metadata=metadata
        )
        record.start()
        self._current_record = record
        self._records.append(record)
        return record

    def end_recording(
        self,
        success: bool = True,
        error_message: Optional[str] = None,
        final_output: Optional[str] = None
    ) -> AgentExecution:
        """
        结束当前录制会话
        
        完成录制，保存执行记录（如果配置了auto_save），并触发回调函数。
        
        Args:
            success: 执行是否成功
            error_message: 如果失败，错误信息
            final_output: 最终输出结果
            
        Returns:
            完成的AgentExecution对象
            
        Raises:
            RuntimeError: 如果没有活跃的录制会话
            
        Example:
            >>> execution = recorder.end_recording(
            ...     success=True,
            ...     final_output="人工智能是..."
            ... )
        """
        if self._current_record is None:
            raise RuntimeError("No active recording session")

        if final_output:
            self._current_record.set_output(final_output)

        self._current_record.end(success=success, error_message=error_message)
        execution = self._current_record.to_agent_execution()

        # 保存到存储（如果配置了）
        if self.auto_save and self.storage:
            self.storage.save_execution(execution)

        # 调用回调函数（如果配置了）
        if self.on_record_complete:
            self.on_record_complete(execution)

        self._current_record = None
        return execution

    def record_step(
        self,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        step_input: Any = None,
        step_output: Any = None
    ) -> StepDetail:
        """
        在当前会话中记录步骤
        
        Args:
            description: 步骤描述
            metadata: 可选的元数据
            step_input: 步骤输入
            step_output: 步骤输出
            
        Returns:
            创建的StepDetail对象
            
        Raises:
            RuntimeError: 如果没有活跃的录制会话
        """
        if self._current_record is None:
            raise RuntimeError("No active recording session. Call start_recording first.")
        return self._current_record.add_step(description, step_input, step_output, metadata)

    def record_tool_call(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        err_msg: Optional[str] = None
    ) -> ToolCallDetail:
        """
        在当前会话中记录工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 工具输入参数
            result: 工具执行结果
            duration_ms: 执行耗时（毫秒）
            success: 是否成功
            err_msg: 错误信息
            
        Returns:
            创建的ToolCallDetail对象
            
        Raises:
            RuntimeError: 如果没有活跃的录制会话
        """
        if self._current_record is None:
            raise RuntimeError("No active recording session. Call start_recording first.")
        return self._current_record.add_tool_call(tool_name, arguments, result, duration_ms, success, err_msg)

    @contextmanager
    def record(self, query: str, metadata: Optional[Dict[str, Any]] = None):
        """
        录制执行的上下文管理器
        
        使用with语句自动管理录制生命周期。进入时开始录制，退出时自动结束录制。
        如果发生异常，会记录错误信息并重新抛出异常。
        
        Args:
            query: 用户查询字符串
            metadata: 可选的元数据字典
            
        Yields:
            ExecutionRecord对象
            
        Example:
            >>> with recorder.record("什么是AI？") as record:
            ...     result = agent.run("什么是AI？")
            ...     record.set_output(result)
            >>> # 退出with块后，执行记录自动保存
        """
        self.start_recording(query, metadata)
        try:
            yield self._current_record
            self.end_recording(success=True)
        except Exception as e:
            self.end_recording(success=False, error_message=str(e))
            raise

    def decorator(self, func: Callable) -> Callable:
        """
        自动录制函数执行的装饰器
        
        将函数包装为自动录制的版本。函数的第一个参数应为查询字符串。
        
        Args:
            func: 要包装的函数
            
        Returns:
            包装后的函数
            
        Example:
            >>> @recorder.decorator
            ... def my_agent(query: str, **kwargs):
            ...     return agent.run(query, **kwargs)
            ... 
            >>> result = my_agent("什么是AI？")
            >>> # 执行自动被录制
        """
        def wrapper(query: str, *args, **kwargs):
            metadata = {
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            with self.record(query, metadata):
                result = func(query, *args, **kwargs)
                if self._current_record:
                    self._current_record.set_output(str(result))
                return result
        return wrapper

    def get_all_records(self) -> List[ExecutionRecord]:
        """
        获取所有录制的会话
        
        Returns:
            ExecutionRecord对象列表的副本
        """
        return self._records.copy()

    def get_execution_history(self) -> List[AgentExecution]:
        """
        获取所有执行记录（AgentExecution格式）
        
        Returns:
            AgentExecution对象列表
        """
        return [record.to_agent_execution() for record in self._records]

    def clear_history(self):
        """
        清除所有录制的会话
        
        清空所有历史记录和当前录制会话。
        
        Example:
            >>> recorder.clear_history()
            >>> assert len(recorder.get_all_records()) == 0
        """
        self._records.clear()
        self._current_record = None


# =============================================================================
# 工具调用追踪辅助类
# =============================================================================

class ToolCallTracker:
    """
    工具调用追踪辅助类 - 带自动计时功能
    
    用于追踪工具调用的执行时间和结果。可以与with语句配合使用，
    自动计算工具调用的耗时。
    
    Attributes:
        recorder: 关联的ExecutionRecorder实例
        _start_time: 开始时间戳
    
    Example:
        >>> recorder = ExecutionRecorder()
        >>> recorder.start_recording("测试")
        >>> 
        >>> # 使用上下文管理器自动计时
        >>> with ToolCallTracker(recorder) as tracker:
        ...     result = search_api("AI")
        ...     tracker.track("search", {"q": "AI"}, result)
        >>> 
        >>> # 耗时自动计算
    """

    def __init__(self, recorder: ExecutionRecorder):
        """
        初始化工具调用追踪器
        
        Args:
            recorder: 关联的ExecutionRecorder实例
        """
        self.recorder = recorder
        self._start_time: Optional[float] = None

    def __enter__(self):
        """
        进入上下文，开始计时
        
        Returns:
            ToolCallTracker实例自身
        """
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文
        
        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪信息
        """
        pass

    def track(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None
    ):
        """
        追踪工具调用（带自动计时）
        
        记录工具调用信息，并根据进入上下文时的时间自动计算耗时。
        
        Args:
            tool_name: 工具名称
            arguments: 工具输入参数
            result: 工具执行结果
            
        Example:
            >>> with ToolCallTracker(recorder) as tracker:
            ...     result = calculator("1+1")
            ...     tracker.track("calculator", {"expr": "1+1"}, result)
            >>> # 耗时自动计算为从__enter__到track的时间差
        """
        duration_ms = None
        if self._start_time:
            duration_ms = (time.time() - self._start_time) * 1000
        
        success = exc_type is None
        err_msg = str(exc_val) if exc_val else None
        
        self.recorder.record_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            duration_ms=duration_ms,
            success=success,
            err_msg=err_msg
        )


# =============================================================================
# 工厂函数
# =============================================================================

def create_recorder(storage=None, auto_save: bool = True) -> ExecutionRecorder:
    """
    创建ExecutionRecorder的工厂函数
    
    便捷函数，用于快速创建ExecutionRecorder实例。
    
    Args:
        storage: 存储后端实例
        auto_save: 是否自动保存，默认为True
        
    Returns:
        ExecutionRecorder实例
        
    Example:
        >>> from agent_eval.storages import create_storage, StorageConfig, StorageType
        >>> storage = create_storage(StorageConfig(storage_type=StorageType.JSON))
        >>> recorder = create_recorder(storage=storage, auto_save=True)
    """
    return ExecutionRecorder(storage=storage, auto_save=auto_save)
