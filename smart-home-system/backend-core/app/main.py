import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1 import router as api_v1_router
from .core.device_simulator import hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时开启 DeviceHub TCP 服务器"""
    task = asyncio.create_task(hub.start())
    yield
    task.cancel()


app = FastAPI(
    title="Smart Home Backend",
    description="智能家居后端 — 设备自动注册，通用 API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "devices": len(hub._devices)}


app.include_router(api_v1_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
