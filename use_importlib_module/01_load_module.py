import importlib

# 导入同级模块
new_module = importlib.import_module("test_module")
print(new_module.test_add(1, 2))

# 加载同级包下的模块
new_module2 = importlib.import_module(".ceshi", package="test_package")
print(hasattr(new_module2, "sub_operate"))
print(new_module2.sub_operate(1, 2))