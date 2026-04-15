"""
LangChain 集成模块 - 通过回调处理器追踪执行

本模块提供 LangChain 回调处理器，自动将 LangChain 的执行过程
转换为 AgentEval 的执行记录，包括步骤、工具调用和 LLM 调用。

依赖：
    pip install langchain

使用示例：
    >>> from agent_eval.integrations import LangChainCallback
    >>> from langchain import LLMChain, PromptTemplate
    >>> from langchain.llms import OpenAI
    >>> 
    >>> # 创建回调处理器
    >>> callback = LangChainCallback(
    ...     agent_id="my_agent",
    ...     metadata={"version": "1.0"}
    ... )
    >>> 
    >>> # 在链中使用
    >>> chain = LLMChain(
    ...     llm=OpenAI(),
    ...     prompt=PromptTemplate.from_template("回答: {question}")
    ... )
    >>> result = chain.invoke(
    ...     {"question": "什么是AI？"},
    ...     config={"callbacks": [callback]}
    ... )
    >>> 
    >>> # 获取执行记录
    >>> execution = callback.get_execution()
    >>> print(f"执行步骤: {execution.step_count}")
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from agent_eval.decorators import get_current_execution, _set_current_execution, _reset_current_execution
from agent_eval.models import AgentExecution, StepDetail, ToolCallDetail
from agent_eval.storages import BaseStorage

# 尝试导入 LangChain
try:
    # 新版 LangChain (0.1.0+)
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.agents import AgentAction, AgentFinish
    from langchain_core.outputs import LLMResult
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        # 旧版 LangChain
        from langchain.callbacks.base import BaseCallbackHandler
        from langchain.schema import AgentAction, AgentFinish, LLMResult
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        # 创建占位类以避免导入错误
        class BaseCallbackHandler:
            pass
        AgentAction = Any
        AgentFinish = Any
        LLMResult = Any


class LangChainCallback(BaseCallbackHandler):
    """
    LangChain 回调处理器 - 自动追踪执行过程
    
    将 LangChain 的回调事件转换为 AgentEval 的执行记录，
    支持追踪链、工具、LLM 调用等。
    
    Attributes:
        agent_id: 智能体标识符
        query: 用户查询
        metadata: 执行元数据
        storage: 存储后端
        execution: 当前执行记录
        _step_counter: 步骤计数器
        _tool_counter: 工具调用计数器
        _context_tokens: 上下文变量 token
    
    Example:
        >>> callback = LangChainCallback(agent_id="qa_bot")
        >>> 
        >>> # 在 LCEL 中使用
        >>> chain = prompt | llm | output_parser
        >>> result = chain.invoke(
        ...     {"question": "什么是AI？"},
        ...     config={"callbacks": [callback]}
        ... )
        >>> 
        >>> # 查看执行记录
        >>> execution = callback.get_execution()
        >>> print(f"步骤数: {len(execution.steps_detail)}")
        >>> print(f"工具调用: {len(execution.tool_calls_detail)}")
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        query: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        storage: Optional[BaseStorage] = None
    ):
        """
        初始化回调处理器
        
        Args:
            agent_id: 智能体标识符
            query: 用户查询（如果未提供，将尝试从输入推断）
            metadata: 执行元数据
            storage: 存储后端
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. "
                "Please install it with: pip install langchain"
            )
        
        self.agent_id = agent_id
        self.query = query
        self.metadata = metadata or {}
        self.storage = storage
        
        self.execution: Optional[AgentExecution] = None
        self._step_counter = 0
        self._tool_counter = 0
        self._context_tokens = None
        self._chain_stack: List[str] = []  # 链调用栈
        self._current_llm_call: Optional[Dict] = None
    
    def _create_execution(self, inputs: Dict[str, Any]):
        """创建执行记录"""
        # 推断查询
        if self.query is None:
            # 尝试从常见输入字段推断
            for key in ["question", "query", "input", "prompt", "text"]:
                if key in inputs:
                    self.query = str(inputs[key])
                    break
            else:
                self.query = str(inputs)[:100]  # 使用前100字符
        
        self.execution = AgentExecution(
            execution_id=str(uuid.uuid4()),
            query=self.query,
            agent_id=self.agent_id,
            start_time=datetime.now(),
            metadata={
                **self.metadata,
                "framework": "langchain",
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
    
    def get_execution(self) -> Optional[AgentExecution]:
        """
        获取执行记录
        
        Returns:
            AgentExecution 对象
        """
        return self.execution
    
    # =========================================================================
    # 链回调
    # =========================================================================
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """链开始执行"""
        chain_name = serialized.get("name", "unknown_chain") if serialized else "unknown_chain"
        self._chain_stack.append(chain_name)
        
        # 如果是顶层链，创建执行记录
        if len(self._chain_stack) == 1:
            self._create_execution(inputs)
        
        # 记录步骤
        self._step_counter += 1
        if self.execution:
            step = StepDetail(
                step=self._step_counter,
                description=f"chain:{chain_name}",
                input=inputs,
                output=None,
                success=True
            )
            self.execution.steps_detail.append(step)
            self.execution.step_count = self._step_counter
    
    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """链执行结束"""
        if self._chain_stack:
            chain_name = self._chain_stack.pop()
        
        # 更新最后一步的输出
        if self.execution and self.execution.steps_detail:
            last_step = self.execution.steps_detail[-1]
            if last_step.description.startswith("chain:"):
                last_step.output = outputs
        
        # 如果是顶层链，保存执行记录
        if len(self._chain_stack) == 0:
            if self.execution:
                if not isinstance(outputs, str):
                    self.execution.final_output = outputs["messages"][-1].content
                if isinstance(outputs, str):
                    self.execution.final_output = outputs
                if not outputs:
                    self.execution.final_output = ""
            self._save_execution()
    
    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        **kwargs: Any
    ) -> None:
        """链执行出错"""
        if self._chain_stack:
            self._chain_stack.pop()
        
        if self.execution:
            self.execution.has_error = True
            self.execution.error_message = str(error)
            
            # 更新最后一步
            if self.execution.steps_detail:
                last_step = self.execution.steps_detail[-1]
                last_step.success = False
                last_step.err_msg = str(error)
        
        if len(self._chain_stack) == 0:
            self._save_execution(success=False)
    
    # =========================================================================
    # 工具回调
    # =========================================================================
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """工具开始执行"""
        tool_name = serialized.get("name", "unknown_tool")
        self._current_tool_start = time.time()
    
    def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """工具执行结束"""
        duration_ms = (time.time() - self._current_tool_start) * 1000 if hasattr(self, '_current_tool_start') else None
        
        if self.execution:
            self._tool_counter += 1
            tool_call = ToolCallDetail(
                name=kwargs.get("name", "unknown_tool"),
                input={"query": kwargs.get("input_str", "")},
                output=output,
                time=duration_ms,
                success=True
            )
            self.execution.tool_calls_detail.append(tool_call)
            self.execution.tool_call_count = self._tool_counter
    
    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        **kwargs: Any
    ) -> None:
        """工具执行出错"""
        duration_ms = (time.time() - self._current_tool_start) * 1000 if hasattr(self, '_current_tool_start') else None
        
        if self.execution:
            self._tool_counter += 1
            tool_call = ToolCallDetail(
                name=kwargs.get("name", "unknown_tool"),
                input={"query": kwargs.get("input_str", "")},
                output=None,
                time=duration_ms,
                success=False,
                err_msg=str(error)
            )
            self.execution.tool_calls_detail.append(tool_call)
            self.execution.tool_call_count = self._tool_counter
    
    # =========================================================================
    # LLM 回调
    # =========================================================================
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """LLM 开始调用"""
        self._current_llm_call = {
            "start_time": time.time(),
            "prompts": prompts,
            "model": serialized.get("name", "unknown_model")
        }
    
    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """LLM 调用结束"""
        if self._current_llm_call and self.execution:
            duration_ms = (time.time() - self._current_llm_call["start_time"]) * 1000
            
            # 记录 LLM 调用作为元数据
            if "llm_calls" not in self.execution.metadata:
                self.execution.metadata["llm_calls"] = []
            
            self.execution.metadata["llm_calls"].append({
                "model": self._current_llm_call["model"],
                "duration_ms": duration_ms,
                "token_usage": response.llm_output.get("token_usage") if response.llm_output else None
            })
        
        self._current_llm_call = None
    
    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        **kwargs: Any
    ) -> None:
        """LLM 调用出错"""
        self._current_llm_call = None


class LangChainTracer:
    """
    LangChain 追踪器 - 高级封装
    
    提供更简单的 API 来追踪 LangChain 链和 Agent。
    
    Example:
        >>> tracer = LangChainTracer(agent_id="my_bot")
        >>> 
        >>> # 追踪链执行
        >>> result = tracer.trace(chain, {"question": "什么是AI？"})
        >>> 
        >>> # 获取执行记录
        >>> execution = tracer.get_last_execution()
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        storage: Optional[BaseStorage] = None
    ):
        """
        初始化追踪器
        
        Args:
            agent_id: 智能体标识符
            storage: 存储后端
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. "
                "Please install it with: pip install langchain"
            )
        
        self.agent_id = agent_id
        self.storage = storage
        self._executions: List[AgentExecution] = []
    
    def trace(
        self,
        chain_or_agent: Any,
        inputs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        追踪链或 Agent 的执行
        
        Args:
            chain_or_agent: LangChain 链或 Agent
            inputs: 输入数据
            metadata: 额外元数据
            
        Returns:
            链或 Agent 的执行结果
        """
        callback = LangChainCallback(
            agent_id=self.agent_id,
            metadata=metadata,
            storage=self.storage
        )
        
        result = chain_or_agent.invoke(
            inputs,
            config={"callbacks": [callback]}
        )
        
        if callback.execution:
            self._executions.append(callback.execution)
        
        return result
    
    def get_last_execution(self) -> Optional[AgentExecution]:
        """获取最近一次执行记录"""
        if self._executions:
            return self._executions[-1]
        return None
    
    def get_all_executions(self) -> List[AgentExecution]:
        """获取所有执行记录"""
        return self._executions.copy()
