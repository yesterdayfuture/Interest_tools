
import inspect
from functools import wraps

class Logger:

    info = [] #定义一个类变量，用于存储使用装饰器的函数的信息

    def __init__(self, name):
        self.name = name
        


    def log_method(self, func):


        # === 在装饰时直接收集信息（不依赖函数调用）===
        func_name = func.__name__
        func_desc = func.__doc__
        sig = inspect.signature(func)
        params = sig.parameters

        # print("Parameters:", [f"{k}: {v.annotation}" for k, v in params.items()])
        
        # 直接访问类变量（非实例变量）
        Logger.info.append({  # 使用Logger.info而非self.info
            "name": func_name,
            "desc": func_desc,
            "params": [f"{k}: {v.annotation}" for k, v in params.items()]
        })

        @wraps(func)
        def wrapper(*args, **kwargs):

            # args[0] 是实例对象 (self)
            print(f"Calling {func.__name__} in {args[0].__class__.__name__}")
            return func(*args, **kwargs)
        return wrapper


logger = Logger("name")

@logger.log_method  # 类方法作为装饰器
def compute(a: int, b:int):
    """Calculate product."""
    return a * b

@logger.log_method
def sum( a, b):
    """sum product."""
    return a * b


#获取所有 被装饰器 装饰的函数信息
info = Logger.info
print(info)


