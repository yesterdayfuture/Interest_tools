# app/function_loader.py
import importlib.util
import importlib
import sys
from pathlib import Path
from typing import Optional

# 添加路径白名单校验
ALLOWED_DIRS = ["plugins", "extensions"]


def validate_file_path(file_path: str) -> bool:
    abs_path = Path(file_path).absolute()
    for allowed in ALLOWED_DIRS:
        if str(abs_path).startswith(str(Path(allowed).absolute())):
            return True
    return False


class FunctionLoader:
    """业务函数动态加载器（修复版）"""

    def __init__(self):
        self.loaded_modules = {}  # {module_name: file_path}

    def load(self, file_path: str, module_name: str = None) -> Optional[object]:
        """加载模块"""

        file_path = str(Path(file_path).absolute())

        if module_name is None:
            module_name = f"dynamic_{Path(file_path).stem}_{id(file_path)}"

        # 创建 spec
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            raise ImportError(f"Cannot create spec for {file_path}")

        # 创建模块
        module = importlib.util.module_from_spec(spec)

        # ✅ 关键：将 spec 赋值给模块
        module.__spec__ = spec

        # 注册到 sys.modules
        sys.modules[module_name] = module

        # 执行模块代码
        spec.loader.exec_module(module)

        # 记录文件路径以便 reload
        self.loaded_modules[module_name] = file_path

        return module

    def reload(self, module_name: str):
        """重新加载模块（修复版）"""
        if module_name not in self.loaded_modules:
            raise ValueError(f"Module {module_name} not loaded")

        file_path = self.loaded_modules[module_name]

        # ✅ 方案 A：重新创建 spec 并执行（最可靠）
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        module.__spec__ = spec
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

        # ❌ 方案 B：直接使用 importlib.reload（会报错）
        # return importlib.reload(sys.modules[module_name])

    def call(self, module_name: str, function_name: str, *args, **kwargs):
        """调用指定模块中的函数"""
        if module_name not in sys.modules:
            raise ValueError(f"Module {module_name} not loaded")

        module = sys.modules[module_name]
        if not hasattr(module, function_name):
            raise AttributeError(f"Function {function_name} not found in {module_name}")

        func = getattr(module, function_name)

        # 支持异步函数
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(*args, **kwargs))

        return func(*args, **kwargs)