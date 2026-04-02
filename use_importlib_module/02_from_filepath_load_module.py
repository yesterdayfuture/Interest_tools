import importlib
import importlib.util
import sys

# 根据文件路径加载模块
file_path = "./test_module.py"
# 创建模块规格
new_module_spec = importlib.util.spec_from_file_location(
    name="test_module",
    location=file_path,
)

new_module = importlib.util.module_from_spec(new_module_spec)

# 执行模块代码（相当于导入）
new_module_spec.loader.exec_module(new_module)

# 将模块添加到 sys.modules 以便后续导入
sys.modules["test_module"] = new_module

print(new_module.test_add(1, 2))
print(new_module.__spec__)
print("*"*50)

