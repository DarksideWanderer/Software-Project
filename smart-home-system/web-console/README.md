# 栖居全屋智能 Web 控制台

面向课程大作业闭环演示的静态 Web 前端。页面本身无构建依赖，但所有设备状态、场景执行、文本助手和语音助手都通过 `backend-core` 的 `/api/v1` 接口完成。

## 功能

- 三设备 MVP：中央空调、客厅主灯、智能电视。
- 设备卡片、详情抽屉、开关和参数控制均读取真实后端状态。
- 回家、观影、离家三个场景由后端编排并执行设备命令。
- 文本助手调用 `backend-core -> ai-service NLU -> DeviceHub`，并消费 backend-core 返回的 TTS 回复音频。
- 浏览器录音会编码为 WAV 并上传 `POST /api/v1/assistant/voice`，语音回复仍只从 backend-core 读取。
- API 不可用或设备模拟器未连接时显示明确失败提示。

## 本地运行

先按 `../FINAL_DELIVERY.md` 启动 AI service、backend-core 和三个 C++ simulator，然后在当前目录执行：

```bash
python3 -m http.server 4173
```

访问 <http://127.0.0.1:4173>。

如需改 backend 地址，可在浏览器控制台刷新前设置：

```js
window.SMART_HOME_API_BASE = "http://127.0.0.1:8000/api/v1";
```
