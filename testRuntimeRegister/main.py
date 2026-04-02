# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.function_loader import FunctionLoader, validate_file_path

app = FastAPI()
function_loader = FunctionLoader()


class LoadModuleRequest(BaseModel):
    file_path: str
    module_name: str = None


class CallFunctionRequest(BaseModel):
    module_name: str
    function_name: str
    args: list = []
    kwargs: dict = {}


@app.post("/admin/load-module")
async def load_module(req: LoadModuleRequest):
    """加载新模块"""
    # 在 load_module 中使用
    if not validate_file_path(req.file_path):
        raise HTTPException(status_code=403, detail="Path not allowed")


    try:
        module = function_loader.load(req.file_path, req.module_name)
        # 获取模块中所有可调用函数
        functions = [
            name for name in dir(module)
            if callable(getattr(module, name)) and not name.startswith("_")
        ]
        return {
            "status": "success",
            "module_name": req.module_name,
            "available_functions": functions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/call-function")
async def call_function(req: CallFunctionRequest):
    """调用模块中的函数"""
    try:
        result = function_loader.call(
            req.module_name,
            req.function_name,
            *req.args,
            **req.kwargs
        )
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/reload-module")
async def reload_module(module_name: str):
    """重新加载模块（用于代码更新后）"""
    try:
        function_loader.reload(module_name)
        return {"status": "success", "message": f"Module {module_name} reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)