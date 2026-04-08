"""
API v1 路由聚合模块

该模块聚合所有 v1 版本的 API 路由，统一配置前缀和标签。
通过 api_router 将各个子模块的路由组织在一起，形成完整的 API 结构。

路由结构：
    /api/v1/
    ├── /tasks          # 任务相关接口 (tasks.py)
    │   ├── POST /submit
    │   ├── GET /list
    │   ├── GET /{task_id}
    │   ├── PUT /{task_id}
    │   ├── DELETE /{task_id}
    │   ├── POST /{task_id}/cancel
    │   └── GET /statistics/overview
    └── ...             # 其他模块路由

添加新模块路由的步骤：
1. 在 v1 目录下创建新的路由文件（如 users.py）
2. 在该文件中创建 APIRouter 实例并定义路由
3. 在 api.py 中导入并注册路由
"""

from fastapi import APIRouter

from app.api.v1 import tasks

# 创建 v1 版本的主路由
# prefix 和 tags 会在 include_router 时由调用方设置
api_router = APIRouter()

# ==================== 注册任务路由 ====================
# prefix: 该模块所有路由的前缀
# tags: API 文档中的分组标签
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["tasks"]
)

# 添加其他模块路由的示例：
# from app.api.v1 import users
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# 
# from app.api.v1 import auth
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
