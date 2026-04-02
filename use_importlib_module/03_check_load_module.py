"""
检测当前模块是否可以导入
"""
import importlib.util

module_name = "test_package.ceshi"
spec = importlib.util.find_spec(module_name)
if spec is not None:
    print(f"Found module: {spec.name}")
    print(f"Loader: {spec.loader}")
else:
    print("Module not found")