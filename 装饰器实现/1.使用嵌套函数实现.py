
import inspect # 用于获取函数的参数信息
from functools import wraps

def method_decorator(func):
    @wraps(func)  # 保留原函数的元数据
    def wrapper(*args, **kwargs):
        # 获取方法名称和描述
        print(f"Method name: {func.__name__}")
        print(f"Docstring: {func.__doc__}")
        
        # 获取参数详情
        sig = inspect.signature(func)
        params = sig.parameters
        print("Parameters:", [f"{k}: {v.annotation}" for k, v in params.items()])
        
        return func(*args, **kwargs)
    return wrapper


@method_decorator
def my_method( a: int, b: str) -> float:
    """Example method description."""
    return a + float(b)

# 调用
result = my_method(1, '2.5')
print(result)

