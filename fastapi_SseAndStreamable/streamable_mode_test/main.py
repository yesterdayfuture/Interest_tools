from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import json

app = FastAPI()

@app.get("/stream")
async def stream_data():
    async def generate():
        for i in range(5):
            # 可以自定义任何格式，无需data:前缀
            data =  f"Chunk {i}\n"
            yield json.dumps({"message": data})
            await asyncio.sleep(1)
    return StreamingResponse(generate(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)