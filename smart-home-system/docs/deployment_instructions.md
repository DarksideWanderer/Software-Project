# 必要部署和操作说明

本文档位于仓库根目录，用于说明智能家居中控系统的必要部署步骤、启动顺序、基础操作流程和验收方式。

## 1. 系统组成

项目主体位于 `smart-home-system/`，当前运行闭环如下：

```text
web-console
  -> backend-core /api/v1
    -> ai-service /internal/v1/asr|nlu|tts
    -> DeviceHub TCP :9760
      -> device-simulator 进程
```

| 模块 | 路径 | 作用 |
| --- | --- | --- |
| Web 控制台 | `smart-home-system/web-console` | 设备、场景、添加家电、助手交互界面 |
| 主后端 | `smart-home-system/backend-core` | API、家庭缓存、DeviceHub、场景执行、AI 代理 |
| AI 服务 | `smart-home-system/ai-service` | ASR、NLU、TTS 内部接口 |
| 设备模拟器 | `smart-home-system/device-simulator` | C++ 家电模拟进程 |

浏览器只访问 `backend-core`，不直接访问 `ai-service` 或 DeviceHub。

## 2. 环境要求

### 2.1 基础环境

- Python 3.10+
- Node.js，用于检查前端 JS 语法
- CMake
- C++20 编译环境
- Windows 下建议使用 MSYS2 编译和运行设备模拟器，因为模拟器使用 POSIX socket 头文件

### 2.2 端口

| 端口 | 服务 |
| --- | --- |
| `8000` | `backend-core` 和 Web 控制台 |
| `8001` | `ai-service` |
| `9760` | DeviceHub TCP 服务，由 `backend-core` 自动启动 |

## 3. 配置文件

AI 服务配置位于：

```text
smart-home-system/ai-service/.env
```

如果没有 `.env`，可从示例文件复制：

```bash
cd smart-home-system/ai-service
cp .env.example .env
```

家庭状态缓存位于：

```text
smart-home-system/backend-core/data/home_state.json
```

该文件保存已绑定设备、设备状态缓存和用户创建的场景。需要恢复空家庭状态时，可以在服务停止后备份或删除该文件。

## 4. 启动顺序

必须按以下顺序启动。

### 4.1 启动 AI 服务

```bash
cd smart-home-system/ai-service
python -m pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

健康检查：

```bash
curl http://127.0.0.1:8001/internal/health
```

正常响应应包含 `status: ok`，并显示 ASR、NLU、TTS 模块状态。

### 4.2 启动主后端

```bash
cd smart-home-system/backend-core
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

主后端启动后会自动启动 DeviceHub，监听 `9760` 端口。

健康检查：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/dashboard
```

### 4.3 编译设备模拟器

```bash
cd smart-home-system/device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
```

Windows 下如遇到 `sys/socket.h` 找不到，需要切换到 MSYS2 环境编译。

### 4.4 启动设备模拟器

每个家电建议单独开一个终端进程。例如：

```bash
cd smart-home-system/device-simulator

./build/simulator --device ac --id ac-003
./build/simulator --device ac --id ac-004
./build/simulator --device light --id light-001
./build/simulator --device tv --id tv-001
```

支持的设备类型：

| 参数 | 类型 |
| --- | --- |
| `ac` | 空调 |
| `light` | 灯 |
| `tv` | 电视 |
| `fridge` | 冰箱 |
| `washer` | 洗衣机 |
| `heater` | 热水器 |
| `purifier` | 空气净化器 |
| `curtain` | 窗帘 |
| `socket` | 插座 |
| `robot` | 扫地机器人 |

### 4.5 打开前端

推荐直接访问主后端托管的页面：

```text
http://127.0.0.1:8000
```

也可以单独启动静态前端：

```bash
cd smart-home-system/web-console
python -m http.server 4173
```

然后访问：

```text
http://127.0.0.1:4173
```

## 5. 基础操作流程

### 5.1 添加家电

1. 打开 Web 控制台。
2. 点击“添加家电”。
3. 系统会检索当前 DeviceHub 捕获到的未绑定设备。
4. 在候选列表中选择设备，例如 `AC / ac-003`。
5. 点击添加后，设备进入家庭设备列表。

已绑定设备不会再次出现在候选列表。

### 5.2 控制家电

1. 在首页点击设备卡片。
2. 在详情抽屉中执行开关或参数调整。
3. 后端会校验设备是否已绑定、是否在线、类型是否冲突、命令参数是否合法。
4. 控制成功后页面自动刷新设备状态。

离线设备会显示“离线”，不能控制，但可以修改名称、房间或移除。

### 5.3 创建和执行场景

系统保留预设场景：

- 回家模式
- 观影模式
- 离家模式

用户也可以创建自定义场景：

1. 点击场景创建入口。
2. 选择规则创建，手动选择设备、命令和参数。
3. 或使用自然语言描述场景，例如：`睡觉模式：关闭电视，卧室空调调到 27 度。`
4. 后端调用 AI NLU 解析自然语言，并将结果转换为可执行场景。
5. 场景保存后刷新页面仍然存在。

### 5.4 使用智能助手

文本助手：

1. 在助手输入框输入命令，例如：`关闭客厅的空调`。
2. 后端将当前已绑定设备和场景作为上下文传给 AI NLU。
3. NLU 返回动作计划。
4. `backend-core` 校验并执行动作。

语音助手：

1. 点击麦克风按钮。
2. 浏览器录音并上传 WAV。
3. `ai-service` ASR 转写为文本。
4. 后续复用文本助手流程。
5. TTS 回复音频通过 `backend-core` 代理播放。

## 6. 验证命令

### 6.1 检查 AI 服务

```bash
curl http://127.0.0.1:8001/internal/health
```

### 6.2 检查主后端

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/dashboard
```

### 6.3 检查设备发现

启动至少一个设备模拟器后执行：

```bash
curl http://127.0.0.1:8000/api/v1/devices/discover
```

### 6.4 检查 NLU

```bash
curl -X POST http://127.0.0.1:8001/internal/v1/nlu/interpret \
  -H "Content-Type: application/json" \
  -d '{"text":"关闭客厅的空调","devices":[],"scenes":[]}'
```

实际控制时应通过 `backend-core` 的助手接口调用，因为后端会提供已绑定设备上下文。

## 7. 测试命令

```bash
# 前端语法检查
cd smart-home-system/web-console
node --check app.js

# 主后端测试
cd ../backend-core
pytest tests -v

# AI 服务测试
cd ../ai-service
pytest tests -v

# 设备模拟器编译检查
cd ../device-simulator
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build
```

## 8. 常见问题

### 8.1 前端显示后端未连接

检查 `backend-core` 是否启动在 `8000` 端口：

```bash
curl http://127.0.0.1:8000/health
```

### 8.2 添加家电时没有候选设备

检查是否已经启动 C++ 模拟器，并确认主后端 DeviceHub 已经启动。可用以下接口查看：

```bash
curl http://127.0.0.1:8000/api/v1/devices/discover
```

### 8.3 设备显示离线

说明该设备在缓存中存在，但对应模拟器进程当前没有连接到 DeviceHub。重新启动对应编号的模拟器即可。

### 8.4 设备显示冲突

说明缓存中的设备 ID 对应一种类型，但当前连接到 DeviceHub 的同 ID 设备是另一种类型。应移除该设备后重新绑定，或用正确类型和 ID 重新启动模拟器。

### 8.5 AI NLU 502 或 503

检查 `ai-service` 是否启动，以及 `backend-core` 的 `AI_SERVICE_BASE_URL` 是否指向正确地址：

```bash
curl http://127.0.0.1:8001/internal/health
```

## 9. 演示建议流程

1. 启动 AI 服务。
2. 启动主后端。
3. 启动两个空调、一个灯、一个电视模拟器。
4. 打开 `http://127.0.0.1:8000`。
5. 点击“添加家电”，绑定检索到的设备。
6. 修改设备名称和房间，例如将 `ac-003` 设为“客厅空调”。
7. 控制设备开关和参数。
8. 执行回家、观影、离家预设场景。
9. 创建一个规则场景。
10. 创建一个自然语言场景。
11. 在助手中输入 `关闭客厅的空调`，确认只操作对应设备。
12. 关闭某个模拟器，验证前端离线提示和禁止控制行为。
