# 智能家居课程项目最终交付说明

本文档描述课程大作业闭环版本的启动、演示和验收方式。最终演示范围固定为三设备 MVP：中央空调、客厅主灯、智能电视。

## 架构闭环

```text
web-console
  -> backend-core /api/v1
    -> DeviceHub TCP :9760
      -> device-simulator ac/light/tv
    -> ai-service /internal/v1/asr|nlu|tts
```

浏览器只访问 `backend-core`。模型 API Key 只允许配置在 `ai-service/.env`，仓库只保留 `.env.example`。

## 启动顺序

### 1. AI service

```bash
cd smart-home-system/ai-service
cp .env.example .env
python3 -m pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

无云端密钥时，ASR/NLU/TTS 会使用 mock、规则引擎或本地降级能力。健康检查：

```bash
curl http://127.0.0.1:8001/internal/health
```

### 2. backend-core

```bash
cd smart-home-system/backend-core
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/dashboard
```

### 3. C++ device simulator

```bash
cd smart-home-system/device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
```

分别开启三个终端：

```bash
./build/simulator --device ac
./build/simulator --device light
./build/simulator --device tv
```

### 4. web-console

```bash
cd smart-home-system/web-console
python3 -m http.server 4173
```

访问 <http://127.0.0.1:4173>。

## 演示脚本

1. 打开页面，确认三台设备显示在线。
2. 打开中央空调详情，将温度调整到 26 度，观察状态刷新。
3. 打开客厅主灯详情，将亮度调整到 50%。
4. 点击“观影”场景，确认电视打开、音量调整、灯光变暗、空调保持舒适温度。
5. 在助手里输入“把空调调到 26 度”，确认指令经 NLU 后执行，并出现可播放的 TTS 回复。
6. 点击麦克风，说出“打开客厅灯”，确认浏览器录音上传、ASR 转写、NLU 执行、页面刷新和 TTS 回复播放入口。

## 测试命令

```bash
# 前端语法
cd smart-home-system/web-console
node --check app.js

# backend-core smoke tests
cd ../backend-core
pytest tests -v

# ai-service tests
cd ../ai-service
pytest tests -v

# C++ simulator 编译
cd ../device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build

# Git diff 空白检查
git diff --check
```

## 已知限制

- 最终闭环只承诺空调、灯、电视三类设备；冰箱、风扇和第二盏灯不进入课程交付 MVP。
- 语音录音由前端编码为 WAV；如果浏览器拒绝麦克风权限，语音链路无法执行。
- 当前状态保存在 DeviceHub 与设备进程内，服务重启后恢复设备默认状态。
- WebSocket 实时事件、用户系统、数据库持久化不是本次课程闭环范围。
