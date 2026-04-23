
import inspect

class ClassDecorator:
    def __init__(self, func):
        self.func = func
        # 直接存储原函数的元数据
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __call__(self, *args, **kwargs):

        print('函数名称:', self.__name__)
        print('函数描述:', self.__doc__)
        print('函数名称:', self.func.__name__)
        print('函数描述:', self.func.__doc__)

        # 动态获取参数信息
        sig = inspect.signature(self.func)

        params = sig.parameters
        print("Parameters:", [f"{k}: {v.annotation}" for k, v in params.items()])

        bound_args = sig.bind(*args, **kwargs)
        print(f"Arguments: {bound_args.arguments}")
        
        return self.func(*args, **kwargs)


@ClassDecorator
def my_method(x: int, y: int):
    """Add two numbers."""
    return x + y

result = my_method(3, y=5)  
print(result)


