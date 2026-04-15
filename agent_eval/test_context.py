"""
测试执行上下文关联机制
"""
from agent_eval.decorators import track_agent, track_tool, get_current_execution, get_current_execution_id

# 定义工具
@track_tool('search')
def search_tool(query: str):
    exec_id = get_current_execution_id()
    execution = get_current_execution()
    print(f'  [search_tool] 当前执行ID: {exec_id}')
    print(f'  [search_tool] 当前查询: {execution.query if execution else "None"}')
    return f'搜索结果: {query}'

# 定义Agent
@track_agent()
def my_agent(query: str):
    print(f'[my_agent] 开始执行查询: {query}')
    exec_id = get_current_execution_id()
    print(f'[my_agent] 当前执行ID: {exec_id}')
    result = search_tool(query)
    return f'回答: {result}'

# 测试执行
print('=== 测试1: 基本执行 ===')
result = my_agent('什么是AI？')
print(f'结果: {result}')
print()

print('=== 测试2: 并发执行 ===')
import threading

def run_agent(query):
    result = my_agent(query)
    exec_id = get_current_execution_id()
    print(f'  [线程] 查询 "{query}" 的执行ID: {exec_id}')

threads = [
    threading.Thread(target=run_agent, args=('问题1',)),
    threading.Thread(target=run_agent, args=('问题2',)),
]
for t in threads:
    t.start()
for t in threads:
    t.join()

print()
print('=== 测试3: 独立调用工具（无Agent上下文）===')
result = search_tool('独立查询')
print(f'结果: {result}')

print()
print('=== 测试完成 ===')
