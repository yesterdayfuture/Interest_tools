"""
AgentEval 集成模块 - 与主流框架的集成

本模块提供与 LangChain、LangGraph 等主流 AI 框架的集成，
使这些框架的用户可以无缝使用 AgentEval 的追踪和评估功能。

支持的框架：
- LangChain: 通过回调处理器集成
- LangGraph: 通过状态追踪集成

使用示例：
    >>> from agent_eval.integrations import LangChainCallback, LangGraphTracer
    >>> 
    >>> # LangChain 使用
    >>> callback = LangChainCallback()
    >>> chain.invoke(query, config={"callbacks": [callback]})
    >>> 
    >>> # LangGraph 使用
    >>> tracer = LangGraphTracer()
    >>> result = tracer.run(graph, query)
"""

# 尝试导入可选依赖
try:
    from .langchain_integration import LangChainCallback
    __all__ = ["LangChainCallback"]
except ImportError:
    LangChainCallback = None
    __all__ = []

try:
    from .langgraph_integration import LangGraphTracer, track_langgraph
    if LangChainCallback:
        __all__.extend(["LangGraphTracer", "track_langgraph"])
    else:
        __all__ = ["LangGraphTracer", "track_langgraph"]
except ImportError:
    LangGraphTracer = None
    track_langgraph = None
