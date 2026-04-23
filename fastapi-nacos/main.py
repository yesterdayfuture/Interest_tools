from fastapi import FastAPI
from contextlib import asynccontextmanager
from nacos_client import NacosServiceRegistry

# ====================== 【请修改为你自己的配置】 ======================
NACOS_SERVER_ADDR = "127.0.0.1:8848"
NACOS_NAMESPACE = "public"         # 命名空间 ID
SERVICE_NAME = "fastapi-demo"
SERVICE_IP = "127.0.0.1"           # 生产环境填内网IP
SERVICE_PORT = 8000
NACOS_USERNAME = "nacos"
NACOS_PASSWORD = "nacos"
# ====================================================================

# 全局单例
nacos_registry = NacosServiceRegistry(
    server_addr=NACOS_SERVER_ADDR,
    namespace=NACOS_NAMESPACE,
    service_name=SERVICE_NAME,
    ip=SERVICE_IP,
    port=SERVICE_PORT,
    username=NACOS_USERNAME,
    password=NACOS_PASSWORD
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：注册 + 心跳
    nacos_registry.register()
    nacos_registry.start_heartbeat()
    yield
    # 关闭时：注销服务
    nacos_registry.deregister()


app = FastAPI(
    title="FastAPI + Nacos 注册示例",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
def index():
    return {"code": 200, "msg": "FastAPI 运行正常，已注册到 Nacos"}


@app.get("/health")
def health():
    return {"status": "UP"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
