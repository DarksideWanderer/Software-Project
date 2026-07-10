# 智能家居移动端

本目录是后续移动端客户端的预留目录。当前项目可运行客户端是 `../web-console`，已实现的业务流程都通过 `backend-core` 的 `/api/v1` 暴露。

## 当前状态

- 本目录目前没有移动端应用源码。
- 当前项目演示不需要移动端依赖。
- 后续移动端应复用 `web-console` 已使用的后端 API。

## 接口边界

后续移动端只应调用：

```text
backend-core /api/v1
```

移动端不应直接调用 `ai-service` 或 DeviceHub。

## 相关模块

- `../web-console`：当前浏览器客户端
- `../backend-core`：API 网关和业务编排
- `../ai-service`：内部 ASR/NLU/TTS 服务
- `../device-simulator`：本地设备进程
