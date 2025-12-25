from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "欢迎使用AI对冲基金API"}


@router.get("/ping")
async def ping():
    async def event_generator():
        for i in range(5):
            # 为每次ping创建一个JSON对象
            data = {"ping": f"ping {i+1}/5", "timestamp": i + 1}

            # 格式化为SSE
            yield f"data: {json.dumps(data)}\n\n"

            # 等待1秒
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
