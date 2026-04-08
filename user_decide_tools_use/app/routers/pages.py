"""
页面路由

提供前端页面相关的路由。
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

# 创建路由
router = APIRouter(tags=["页面"])

# 获取当前文件所在目录
CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(CURRENT_DIR, "templates")


@router.get("/", response_class=HTMLResponse)
async def get_index():
    """返回前端 HTML 页面"""
    index_path = os.path.join(TEMPLATE_DIR, "index.html")
    
    # 如果模板文件存在，直接返回
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # 如果模板文件不存在，返回错误信息
    return HTMLResponse(
        content="<h1>错误</h1><p>前端页面文件未找到</p>",
        status_code=500
    )
