from fastapi import APIRouter

## @file __init__.py
# @brief API V1 路由定义文件
# @details 汇总并挂载系统版本 1 的所有功能模块路由

router = APIRouter()

## @brief 获取系统概览信息
# @details 返回当前 API 版本的相关信息及支持的功能特性列表
# @return 返回包含版本和功能列表的字典
@router.get("/info", tags=["General"])
async def get_system_info():
    return {
        "version": "v1",
        "supported_features": ["device_control", "environment_sensor"]
    }
