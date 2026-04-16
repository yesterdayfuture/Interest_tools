"""
这是一个使用 Python 的内置函数 inspect.getmembers() 和 inspect.isfunction() 来获取模块中所有函数的示例。
"""
import importlib
import inspect

# 获取模块中所有函数
def list_module_functions(module_name):
    try:
        module = importlib.import_module(module_name)
        return [(name,obj) for name, obj in inspect.getmembers(module, inspect.isfunction)]
    except ImportError as e:
        print(f"导入失败: {e}")
        return []


# 获取模块中自己定义的函数
def get_own_functions(module_name):
    module = importlib.import_module(module_name)
    own_functions = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if obj.__module__ == module.__name__:
            own_functions.append((name, obj))

    return own_functions


# 获取模块中函数的参数
def list_functions_with_params(module_name):
    module = importlib.import_module(module_name)
    print(dir(module))
    functions = [(name, obj) for name, obj in inspect.getmembers(module, inspect.isfunction)]

    for name, func in functions:
        sig = inspect.signature(func)
        params = []
        for p_name, p in sig.parameters.items():
            # if p.annotation is not p.empty:
            #     print(f"{p_name}: {p.annotation}")  # a: <class 'int'>, b: <class 'str'>
            #     params.append({"name": p_name, "type": p.annotation or None, "default": p.default or None})
            # else:
            #     print(f"{p_name}: 无类型注解")
            # # 格式化参数显示
            # default = "" if p.default is p.empty else f"={p.default}"
            # params.append(f"{p_name}{default}")
            params.append({"name": p_name, "type": p.annotation or None, "default": "" if p.default is p.empty else p.default})
        print(f"{name}({params})")


# 使用
result = list_module_functions('test_module')
print(result)
result2 = get_own_functions('test_module')
print(result2)
# 输出: ['acos', 'acosh', 'asin', ...]

list_functions_with_params('test_module')
