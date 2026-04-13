from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
import asyncio
import json

app = FastAPI()

@app.get("/sse")
async def sse(request: Request):
    async def event_generator():
        try:
            for i in range(5):
                # 检查客户端是否断开（可选）
                if await request.is_disconnected():
                    print("客户端已断开")
                    break

                event_data = {
                    "id": i,
                    "data": f"更新 {i}",
                    "status": "active"
                }

                # 直接 yield 字典，EventSourceResponse 会自动格式化为 SSE 格式
                yield {
                    "event": "update",
                    "id": str(i),
                    "retry": 5000,
                    "data": json.dumps(event_data)
                }
                # yield f"更新 {i}"

                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("任务取消")
        finally:
            print("资源清理完成")

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)