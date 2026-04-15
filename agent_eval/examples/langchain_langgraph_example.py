"""
LangChain 和 LangGraph 集成示例

本示例展示如何在 LangChain 和 LangGraph 中使用 AgentEval 进行执行追踪。
所有执行记录将保存到 JSON 文件。

安装依赖：
    pip install langchain langgraph langchain-openai

运行示例：
    python examples/langchain_langgraph_example.py
"""

import os
from typing import TypedDict, List, Annotated
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# 设置 OpenAI API Key（如果需要）
# os.environ["OPENAI_API_KEY"] = "your-api-key"

# AgentEval 导入
from agent_eval.decorators import get_current_execution, get_current_execution_id
from agent_eval.integrations import LangChainCallback, LangGraphTracer, track_langgraph
from agent_eval.storages import JSONStorage
from agent_eval.models import StorageConfig

# 创建数据目录（如果不存在）
os.makedirs("./data", exist_ok=True)

# 创建 JSON 存储后端
# 执行记录将保存到 ./data/executions.json
storage = JSONStorage(StorageConfig(file_path="./data/test.json"))


# =============================================================================
# 示例1：LangChain 基础使用
# =============================================================================

def example_langchain_basic():
    """
    LangChain 基础追踪示例
    
    展示如何使用 LangChainCallback 追踪简单的 LLM 链。
    """
    print("=" * 60)
    print("示例1: LangChain 基础追踪")
    print("=" * 60)
    
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_openai import ChatOpenAI
        
        # 创建回调处理器（使用 JSON 存储）
        callback = LangChainCallback(
            agent_id="qa_bot",
            metadata={"version": "1.0", "env": "demo"},
            storage=storage  # 使用 JSON 存储
        )
        
        # 构建简单的 QA 链
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个 helpful 助手。"),
            ("human", "{question}")
        ])
        
        # 使用模拟 LLM（如果没有 API Key）
        try:
            llm = ChatOpenAI(
                base_url=os.getenv("base_url"),
                api_key=os.getenv("api_key"),
                model=os.getenv("model_name"),
            )
        except:
            # 如果没有 API Key，使用模拟
            from langchain_core.language_models import FakeListChatModel
            llm = FakeListChatModel(responses=["这是一个模拟回答。"])
        
        chain = prompt | llm | StrOutputParser()
        
        # 执行并追踪
        result = chain.invoke(
            {"question": "什么是人工智能？"},
            config={"callbacks": [callback]}
        )
        
        print(f"回答: {result}")
        
        # 查看执行记录
        execution = callback.get_execution()
        if execution:
            print(f"\n执行记录:")
            print(f"  执行ID: {execution.execution_id}")
            print(f"  查询: {execution.query}")
            print(f"  步骤数: {execution.step_count}")
            print(f"  工具调用: {execution.tool_call_count}")
            
            for step in execution.steps_detail:
                print(f"    - {step.description}: {step.success}")
        
    except Exception as e:
        print(f"需要安装依赖: {e}")
        print("运行: pip install langchain langchain-openai")


# =============================================================================
# 示例2：LangChain 带工具的 Agent
# =============================================================================

def example_langchain_tools():
    """
    LangChain 工具追踪示例
    
    展示如何追踪带工具调用的 Agent。
    """
    print("\n" + "=" * 60)
    print("示例2: LangChain 带工具的 Agent")
    print("=" * 60)
    
    try:
        from langchain.agents import create_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.tools import tool
        from langchain_openai import ChatOpenAI
        
        # 定义工具
        @tool
        def search(query: str) -> str:
            """搜索信息"""
            return f"搜索结果: {query}"
        
        @tool
        def calculator(expression: str) -> str:
            """计算表达式"""
            try:
                return str(eval(expression))
            except:
                return "计算错误"
        
        tools = [search, calculator]
        
        # 创建回调（使用 JSON 存储）
        callback = LangChainCallback(agent_id="tool_agent", storage=storage)
        
        # 创建 Agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个 helpful 助手，可以使用工具。"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        try:
            llm = ChatOpenAI(
                base_url=os.getenv("base_url"),
                api_key=os.getenv("api_key"),
                model=os.getenv("model_name"),
            )

            agent_executor = create_agent(llm, tools, system_prompt="你是一个 helpful 助手，可以使用工具。")
        except:
            print("跳过（需要 OpenAI API Key）")
            return
        
        # 执行
        result = agent_executor.invoke(
            {"messages": [{"role": "user", "content": "搜索人工智能的定义并计算 2+2"}]},
            config={"callbacks": [callback]}
        )
        
        print(f"结果: {result['messages'][-1].content}")
        
        # 查看工具调用
        execution = callback.get_execution()
        if execution:
            print(f"\n工具调用记录:")
            for tool_call in execution.tool_calls_detail:
                print(f"  - {tool_call.name}: {tool_call.input} -> {tool_call.output}")
        
    except ImportError as e:
        print(f"需要安装依赖: {e}")


# =============================================================================
# 示例3：LangGraph 工作流
# =============================================================================

class State(TypedDict):
    """图状态"""
    query: str
    context: List[str]
    answer: str
    steps: Annotated[List[str], "append"]


def example_langgraph_workflow():
    """
    LangGraph 工作流追踪示例
    
    展示如何追踪多节点工作流。
    """
    print("\n" + "=" * 60)
    print("示例3: LangGraph 工作流追踪")
    print("=" * 60)
    
    try:
        from langgraph.graph import StateGraph, END
        
        # 定义节点函数
        def retrieve_node(state: State) -> State:
            """检索节点"""
            print(f"  [节点] 检索: {state['query']}")
            # 模拟检索
            return {
                **state,
                "context": [f"关于 {state['query']} 的信息..."],
                "steps": ["retrieve"]
            }
        
        def generate_node(state: State) -> State:
            """生成节点"""
            print(f"  [节点] 生成答案")
            # 模拟生成
            return {
                **state,
                "answer": f"根据上下文，{state['query']} 是...",
                "steps": ["generate"]
            }
        
        def should_continue(state: State) -> str:
            """决定下一步"""
            if len(state.get("context", [])) > 0:
                return "generate"
            return END
        
        # 构建图
        workflow = StateGraph(State)
        
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)
        
        workflow.set_entry_point("retrieve")
        workflow.add_conditional_edges("retrieve", should_continue)
        workflow.add_edge("generate", END)
        
        graph = workflow.compile()
        
        # 方式1：使用追踪器（使用 JSON 存储）
        print("\n方式1: 使用 LangGraphTracer")
        tracer = LangGraphTracer(
            agent_id="qa_workflow",
            metadata={"type": "rag"},
            storage=storage  # 使用 JSON 存储
        )
        
        result = tracer.run(
            graph,
            {"query": "什么是机器学习？"}
        )
        
        print(f"结果: {result['answer']}")
        
        # 查看执行摘要
        summary = tracer.get_execution_summary()
        print(f"\n执行摘要:")
        print(f"  执行ID: {summary['execution_id']}")
        print(f"  节点数: {summary['node_count']}")
        print(f"  步骤数: {summary['step_count']}")
        for node in summary['nodes']:
            print(f"    - {node['name']}: {node['success']}")
        
    except ImportError as e:
        print(f"需要安装依赖: {e}")
        print("运行: pip install langgraph")


# =============================================================================
# 示例4：LangGraph 装饰器
# =============================================================================

def example_langgraph_decorator():
    """
    LangGraph 装饰器示例
    
    展示如何使用装饰器自动追踪。
    """
    print("\n" + "=" * 60)
    print("示例4: LangGraph 装饰器")
    print("=" * 60)
    
    try:
        from langgraph.graph import StateGraph, END
        
        class SimpleState(TypedDict):
            input: str
            output: str
        
        def process_node(state: SimpleState) -> SimpleState:
            return {"input": state["input"], "output": f"处理结果: {state['input']}"}
        
        # 构建简单图
        workflow = StateGraph(SimpleState)
        workflow.add_node("process", process_node)
        workflow.set_entry_point("process")
        workflow.add_edge("process", END)
        graph = workflow.compile()
        
        # 使用装饰器（使用 JSON 存储）
        @track_langgraph(agent_id="simple_workflow", storage=storage)
        def run_workflow(query: str):
            return graph.invoke({"input": query})
        
        print("\n执行工作流...")
        result = run_workflow("测试输入")
        print(f"结果: {result['output']}")
        
        # 获取执行记录
        execution = get_current_execution()
        if execution:
            print(f"\n执行记录:")
            print(f"  执行ID: {execution.execution_id}")
            print(f"  查询: {execution.query}")
        
    except ImportError as e:
        print(f"需要安装依赖: {e}")


# =============================================================================
# 示例5：在节点中使用回调
# =============================================================================

def example_node_callback():
    """
    节点内回调示例
    
    展示如何在节点内部使用回调记录细粒度步骤。
    """
    print("\n" + "=" * 60)
    print("示例5: 节点内回调")
    print("=" * 60)
    
    try:
        from langgraph.graph import StateGraph, END
        from agent_eval.integrations.langgraph_integration import LangGraphCallback
        
        class State(TypedDict):
            query: str
            result: str
        
        def complex_node(state: State) -> State:
            """复杂节点，内部有多个步骤"""
            # 获取回调
            callback = LangGraphCallback()
            
            # 记录步骤1
            callback.on_step_start("parse_query", state["query"])
            parsed = f"解析: {state['query']}"
            callback.on_step_end("parse_query", parsed)
            print(f"  步骤1: {parsed}")
            
            # 记录步骤2
            callback.on_step_start("process_data", parsed)
            processed = f"处理: {parsed}"
            callback.on_step_end("process_data", processed)
            print(f"  步骤2: {processed}")
            
            # 记录工具调用
            callback.on_tool_call(
                "search_tool",
                {"query": state["query"]},
                "搜索结果"
            )
            print(f"  工具调用: search_tool")
            
            return {"query": state["query"], "result": processed}
        
        # 构建图
        workflow = StateGraph(State)
        workflow.add_node("process", complex_node)
        workflow.set_entry_point("process")
        workflow.add_edge("process", END)
        graph = workflow.compile()
        
        # 使用追踪器（使用 JSON 存储）
        tracer = LangGraphTracer(agent_id="callback_workflow", storage=storage)
        result = tracer.run(graph, {"query": "复杂查询"})
        
        print(f"\n结果: {result['result']}")
        
        # 查看详细步骤
        execution = tracer.get_execution()
        if execution:
            print(f"\n详细步骤:")
            for step in execution.steps_detail:
                print(f"  - {step.description}")
            
            print(f"\n工具调用:")
            for tool in execution.tool_calls_detail:
                print(f"  - {tool.name}: {tool.input}")
        
    except ImportError as e:
        print(f"需要安装依赖: {e}")


# =============================================================================
# 主函数
# =============================================================================

def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("AgentEval - LangChain/LangGraph 集成示例")
    print("=" * 60)
    print(f"\n执行记录将保存到: ./data/test.json")
    
    # 运行示例
    # example_langchain_basic()
    # example_langchain_tools()  # 需要 OpenAI API Key
    example_langgraph_workflow()
    # example_langgraph_decorator()
    # example_node_callback()
    
    # 从 JSON 存储读取所有执行记录
    print("\n" + "=" * 60)
    print("从 JSON 存储读取执行记录")
    print("=" * 60)
    
    executions = storage.list_executions(limit=10)
    print(f"\n共保存了 {len(executions)} 条执行记录:")
    for i, exec in enumerate(executions, 1):
        print(f"\n  [{i}] 执行ID: {exec.execution_id}")
        print(f"      查询: {exec.query}")
        print(f"      步骤: {exec.step_count}")
        print(f"      工具调用: {exec.tool_call_count}")
        print(f"      成功: {exec.success}")
    
    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
