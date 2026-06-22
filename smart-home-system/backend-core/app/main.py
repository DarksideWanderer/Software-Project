import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.v1 import router as api_v1_router
from .core.device_simulator import hub

# web-console 静态文件路径（相对于 backend-core 目录）
WEB_CONSOLE_DIR = Path(__file__).resolve().parent.parent.parent / "web-console"


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
    allow_origins=["*"],  # 开发/演示阶段允许所有来源；生产环境请改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "devices": len(hub._devices)}


app.include_router(api_v1_router, prefix="/api/v1")

# ★ 托管 web-console 静态文件（必须在路由注册之后，否则会覆盖 API 路由）
if WEB_CONSOLE_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_CONSOLE_DIR), html=True), name="web-console")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
