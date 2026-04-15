"""
Decorator-based Integration Examples for agent-eval
演示如何使用装饰器方式集成 agent-eval（无代码侵入）
"""

import time
from agent_eval import (
    track_agent,
    track_tool,
    track_step,
    track,
    configure_storage,
    StorageConfig,
    StorageType,
    get_execution,
    get_last_exec,
    list_executions,
)


# 配置存储
configure_storage(StorageConfig(
    storage_type=StorageType.JSON,
    file_path="data/decorator_evaluations.json"
))


# ============ 示例 1: 使用 @track_agent 装饰器 ============
print("=" * 60)
print("示例 1: @track_agent 装饰器")
print("=" * 60)

@track_agent(query_arg="query")
def my_chatbot(query: str, user_id: str = "anonymous"):
    """
    简单的聊天机器人
    只需添加 @track_agent() 装饰器即可自动追踪
    """
    # 模拟处理
    time.sleep(0.1)
    
    if "天气" in query:
        return get_weather(query)
    elif "计算" in query:
        return calculate(query)
    else:
        return f"这是对 '{query}' 的回答"


@track_tool(tool_name="weather_api")
def get_weather(query: str) -> str:
    """获取天气信息 - 使用 @track_tool 追踪工具调用"""
    time.sleep(0.05)
    return "今天天气晴朗，25°C"


@track_tool(tool_name="calculator")
def calculate(query: str) -> str:
    """计算工具 - 使用 @track_tool 追踪工具调用"""
    time.sleep(0.03)
    return "计算结果: 42"


# 运行示例
result1 = my_chatbot("今天天气怎么样？", user_id="user123")
print(f"查询结果: {result1}")

# 获取执行记录
last_exec = get_last_exec()
if last_exec:
    print(f"\n执行记录:")
    print(f"  - 执行ID: {last_exec.execution_id}")
    print(f"  - 查询: {last_exec.query}")
    print(f"  - 步骤数: {last_exec.step_count}")
    print(f"  - 工具调用: {last_exec.tool_call_count}")
    print(f"  - 成功: {last_exec.success}")


# ============ 示例 2: 使用 @track_step 装饰器 ============
print("\n" + "=" * 60)
print("示例 2: @track_step 装饰器")
print("=" * 60)

@track_agent()
def complex_agent(query: str):
    """复杂智能体，包含多个步骤"""
    # 步骤1: 解析查询
    parsed = parse_query(query)
    
    # 步骤2: 检索信息
    info = retrieve_info(parsed)
    
    # 步骤3: 生成回答
    answer = generate_answer(info)
    
    return answer


@track_step("解析查询")
def parse_query(query: str) -> dict:
    """解析用户查询"""
    time.sleep(0.02)
    return {"intent": "search", "keywords": query.split()}


@track_step("检索信息")
def retrieve_info(parsed: dict) -> list:
    """检索相关信息"""
    time.sleep(0.05)
    return ["信息1", "信息2", "信息3"]


@track_step("生成回答")
def generate_answer(info: list) -> str:
    """生成最终回答"""
    time.sleep(0.03)
    return "基于检索到的信息，这是最终回答。"


# 运行示例
result2 = complex_agent("Python 编程技巧")
print(f"查询结果: {result2}")

last_exec = get_last_exec()
if last_exec:
    print(f"\n执行步骤详情:")
    for step in last_exec.steps_detail:
        print(f"  步骤 {step.step}: {step.description}")


# ============ 示例 3: 使用 Context Manager ============
print("\n" + "=" * 60)
print("示例 3: Context Manager 方式")
print("=" * 60)

def custom_agent_logic(query: str) -> str:
    """自定义智能体逻辑"""
    # 使用 context manager 追踪
    with track(query) as exec:
        # 手动添加步骤
        exec.add_step("理解查询", step_input=query)
        
        # 模拟处理
        time.sleep(0.05)
        
        # 添加工具调用
        exec.add_tool_call(
            tool_name="search",
            tool_input={"q": query},
            tool_output={"results": ["result1", "result2"]},
            duration_ms=50
        )
        
        # 添加更多步骤
        exec.add_step("处理结果")
        
        # 设置最终输出
        result = f"关于 '{query}' 的搜索结果"
        exec.set_output(result)
        
        return result


result3 = custom_agent_logic("机器学习教程")
print(f"查询结果: {result3}")

last_exec = get_last_exec()
if last_exec:
    print(f"\n执行摘要:")
    print(f"  {last_exec.steps_summary}")


# ============ 示例 4: 批量执行和评估 ============
print("\n" + "=" * 60)
print("示例 4: 批量执行")
print("=" * 60)

queries = [
    "什么是人工智能？",
    "Python 异步编程",
    "深度学习基础",
    "自然语言处理",
]

for query in queries:
    result = my_chatbot(query)
    print(f"✓ {query}")

# 查看所有执行
all_execs = list_executions()
print(f"\n总共执行了 {len(all_execs)} 次查询")

# 统计信息
total_tools = sum(e.tool_call_count for e in all_execs)
print(f"总工具调用次数: {total_tools}")


# ============ 示例 5: 与 LangChain 风格集成 ============
print("\n" + "=" * 60)
print("示例 5: LangChain 风格集成")
print("=" * 60)

class MyAgent:
    """模拟 LangChain 风格的智能体"""
    
    def __init__(self):
        self.tools = {
            "search": self._search,
            "calculate": self._calculate,
        }
    
    @track_agent(query_arg="input")
    def run(self, input: str) -> str:
        """运行智能体"""
        # 决定使用哪个工具
        if "计算" in input or "calculate" in input:
            return self.tools["calculate"](input)
        else:
            return self.tools["search"](input)
    
    @track_tool("search")
    def _search(self, query: str) -> str:
        """搜索工具"""
        time.sleep(0.05)
        return f"搜索结果: {query}"
    
    @track_tool("calculate")
    def _calculate(self, expression: str) -> str:
        """计算工具"""
        time.sleep(0.03)
        return f"计算结果: 100"


# 使用示例
agent = MyAgent()
result = agent.run("计算 50 + 50")
print(f"结果: {result}")

last_exec = get_last_exec()
if last_exec:
    print(f"\n工具调用详情:")
    for tool in last_exec.tool_calls_detail:
        print(f"  - {tool.name}: {tool.input}")


# ============ 示例 6: 错误处理 ============
print("\n" + "=" * 60)
print("示例 6: 错误处理")
print("=" * 60)

@track_agent()
def error_prone_agent(query: str) -> str:
    """可能出错的智能体"""
    if "error" in query.lower():
        raise ValueError("模拟错误!")
    return f"成功处理: {query}"


try:
    error_prone_agent("触发 error")
except ValueError as e:
    print(f"捕获错误: {e}")
    
last_exec = get_last_exec()
if last_exec:
    print(f"\n错误记录:")
    print(f"  - 成功: {last_exec.success}")
    print(f"  - 错误: {last_exec.has_error}")
    print(f"  - 错误信息: {last_exec.error_message}")


# 成功的情况
result = error_prone_agent("正常查询")
print(f"\n成功结果: {result}")


print("\n" + "=" * 60)
print("所有示例运行完成!")
print("=" * 60)
print("\n特点:")
print("1. 零代码侵入 - 只需添加装饰器")
print("2. 自动追踪 - 步骤、工具调用、错误")
print("3. 灵活使用 - 装饰器或 Context Manager")
print("4. 自动保存 - 执行数据自动持久化")
