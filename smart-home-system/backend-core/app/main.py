from fastapi import FastAPI
from .api.v1 import router as api_v1_router

## @mainpage 智能家居后端核心服务 (Backend Core)
# @section intro_sec 项目介绍
# 本项目是智能家居系统的核心后端，基于 FastAPI 框架路由分发、设备状态管理及业务逻辑处理。
# 
# @section info_sec 版本信息
# - 版本: 0.1.0
# - 接口前缀: /api/v1

app = FastAPI(
    title="Smart Home System - Backend Core",
    description="智能家居后端核心服务，负责设备管理与业务逻辑",
    version="0.1.0"
)

## @brief 系统健康检查接口
# @details 该接口用于监控系统运行状态，返回服务是否正常。
# @return 返回包含状态信息的字典
@app.get("/health", tags=["System"])
async def health_check():
    """
    系统健康检查接口
    """
    return {"status": "ok", "message": "Backend service is running"}

# 挂载 API 路由
app.include_router(api_v1_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
