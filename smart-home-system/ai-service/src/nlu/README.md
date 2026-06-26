# NLU 自然语言理解模块

## 1. 模块定位

NLU（Natural Language Understanding）模块负责把用户的自然语言指令解析为后端可执行的动作计划。

本模块只做语义理解和动作规划：

- 不直接控制设备；
- 不访问数据库；
- 不调用设备模拟器；
- 不生成底层 TCP 消息；
- 不声称设备已经执行成功。

NLU 的输出格式以 `FRONTEND_API_REQUIREMENTS.md` 中 `§8.2 NLU 意图解析` 为准，核心字段为：

```json
{
  "understood": true,
  "reply": "好的，正在处理客厅主灯。",
  "actions": []
}
```

其中：

- `understood` 表示是否理解用户意图；
- `reply` 是给用户的简短回复，只能描述计划或需要补充的信息；
- `actions` 是动作计划列表，后续由 `backend-core` 统一执行。

## 2. 文件结构

```text
nlu/
├── __init__.py       # 导出 FastAPI router
├── routes.py         # NLU 路由、Pydantic 模型、规则引擎
├── llm_engine.py     # DeepSeek/OpenAI 兼容 LLM 调用与输出校验
└── README.md         # 模块说明文档
```

### 2.1 routes.py

`routes.py` 是 NLU 主实现文件，包含：

- FastAPI 路由；
- 请求/响应 Pydantic 模型；
- 本地规则解析逻辑；
- 规则优先、LLM 兜底的调度流程。

### 2.2 llm_engine.py

`llm_engine.py` 封装 DeepSeek/OpenAI 兼容接口调用，包含：

- LLM 环境变量读取；
- Prompt 构造；
- 模型返回 JSON 提取；
- 模型动作计划校验；
- LLM 失败时返回 `None`，由 `routes.py` 回退规则结果。

### 2.3 __init__.py

`__init__.py` 只负责导出：

```python
from .routes import router
```

供 `src/main.py` 挂载 NLU 路由。

## 3. 对外接口

当前 NLU 模块同时支持内部正式路径和旧版兼容路径。

| 方法     | 路径                           | 说明                                   |
| -------- | ------------------------------ | -------------------------------------- |
| `GET`  | `/internal/v1/nlu/health`    | 内部 NLU 健康检查。                    |
| `GET`  | `/ai/nlu/health`             | 旧版兼容健康检查。                     |
| `POST` | `/internal/v1/nlu/interpret` | NLU 主接口，将自然语言解析为动作计划。 |
| `POST` | `/ai/nlu/parse`              | 旧版兼容解析接口，仅走规则解析。       |

## 4. 请求格式

`POST /internal/v1/nlu/interpret` 请求示例：

```json
{
  "text": "打开客厅灯并把空调调到22度",
  "conversation": [],
  "devices": [
    {
      "id": "light-living-001",
      "type": "light",
      "name": "客厅主灯",
      "room": "客厅",
      "online": true,
      "commands": [
        {
          "name": "turn_on",
          "params": {}
        },
        {
          "name": "set_brightness",
          "params": {
            "brightness": {
              "type": "integer",
              "min": 0,
              "max": 100
            }
          }
        }
      ]
    },
    {
      "id": "ac-living-001",
      "type": "air_conditioner",
      "name": "客厅空调",
      "room": "客厅",
      "online": true,
      "commands": [
        {
          "name": "turn_on",
          "params": {}
        },
        {
          "name": "set_temperature",
          "params": {
            "temperature": {
              "type": "integer",
              "min": 16,
              "max": 30
            }
          }
        }
      ]
    }
  ],
  "scenes": [
    {
      "id": "movie",
      "name": "观影"
    }
  ]
}
```

字段说明：

| 字段             | 类型   | 说明                                             |
| ---------------- | ------ | ------------------------------------------------ |
| `text`         | string | 用户输入的自然语言指令。                         |
| `conversation` | array  | 历史对话，目前主要传给 LLM 兜底使用。            |
| `devices`      | array  | 当前可用设备上下文，NLU 只能使用这里存在的设备。 |
| `scenes`       | array  | 当前可用场景上下文，NLU 只能使用这里存在的场景。 |

## 5. 响应格式

成功理解设备控制时：

```json
{
  "understood": true,
  "reply": "好的，正在处理客厅主灯、客厅空调。",
  "actions": [
    {
      "kind": "device_command",
      "device_id": "light-living-001",
      "command": "turn_on",
      "params": {}
    },
    {
      "kind": "device_command",
      "device_id": "ac-living-001",
      "command": "set_temperature",
      "params": {
        "temperature": 22
      }
    }
  ]
}
```

成功理解场景时：

```json
{
  "understood": true,
  "reply": "好的，正在执行「观影」场景。",
  "actions": [
    {
      "kind": "scene",
      "scene_id": "movie"
    }
  ]
}
```

无法理解或缺少目标时：

```json
{
  "understood": false,
  "reply": "我还不确定你想控制哪个设备，请告诉我设备名称或房间。",
  "actions": []
}
```

## 6. 核心执行流程

当前 NLU 采用“规则优先、LLM 兜底”的策略。

流程如下：

1. 接收 `text`、`devices`、`scenes` 和 `conversation`。
2. 先执行本地规则引擎 `_interpret()`。
3. 如果规则引擎返回 `understood=true` 且 `actions` 非空，直接返回规则结果。
4. 如果规则引擎无法理解，则检查 LLM 是否可用。
5. 如果配置了 LLM Key，则调用 `llm_engine.llm_interpret()`。
6. 如果 LLM 返回合法动作计划，则返回 LLM 结果。
7. 如果 LLM 不可用、请求失败、返回非法 JSON 或动作校验失败，则返回规则引擎的失败结果。

这样设计的原因：

- 常见课程演示指令更稳定；
- 规则命中时不消耗外部模型额度；
- 网络异常时仍可完成基础演示；
- LLM 只负责处理规则覆盖不到的自然表达。

## 7. 规则引擎能力

规则引擎位于 `routes.py`，主要由 `_interpret()` 调度。

### 7.1 设备匹配

设备匹配优先级：

1. 设备名称精确匹配，例如“客厅主灯”。
2. 房间 + 类型匹配，例如“客厅灯”“卧室窗帘”。
3. 类型关键词匹配，例如“空调”“风扇”。

支持的设备类型关键词：

| 类型                | 关键词                                 |
| ------------------- | -------------------------------------- |
| `light`           | 灯、灯光、主灯、氛围灯、所有灯、全部灯 |
| `air_conditioner` | 空调                                   |
| `curtain`         | 窗帘                                   |
| `tv`              | 电视                                   |
| `refrigerator`    | 冰箱                                   |
| `fan`             | 风扇                                   |

支持的房间关键词：

```text
客厅、卧室、书房、厨房、阳台、主卧
```

### 7.2 数值提取

规则引擎可以提取：

- 阿拉伯数字，例如 `22`、`80`；
- 百分比表达，例如 `百分之80`；
- 窗帘常见表达，例如 `一半`、`半开`。

### 7.3 命令解析

当前支持的典型动作：

| 动作         | 示例                 |
| ------------ | -------------------- |
| 开启设备     | 打开客厅灯、开启空调 |
| 关闭设备     | 关闭卧室灯、关掉电视 |
| 设置亮度     | 把客厅灯亮度调到80   |
| 设置温度     | 把空调调到22度       |
| 设置窗帘开度 | 卧室窗帘开一半       |
| 设置风速     | 风扇调到3档          |
| 场景触发     | 开启观影模式         |

注意：最终能否生成 action，还取决于请求中的设备是否声明了对应 command。

## 8. 安全约束

NLU 必须遵守以下约束：

1. 只能使用请求 `devices` 中存在的设备 ID。
2. 只能使用设备 `commands` 中声明过的命令。
3. 参数必须符合命令参数的类型和范围。
4. 只能使用请求 `scenes` 中存在的场景 ID。
5. 不得自行生成底层 TCP 消息。
6. 不得声称设备已经执行成功。

例如，如果用户说“打开厨房灯”，但请求中没有厨房灯设备，则应返回：

```json
{
  "understood": false,
  "reply": "我还不确定你想控制哪个设备，请告诉我设备名称或房间。",
  "actions": []
}
```

## 9. LLM 兜底说明

LLM 兜底逻辑位于 `llm_engine.py`。

当前实现使用 DeepSeek/OpenAI 兼容接口，读取以下环境变量：

| 环境变量              | 默认值                          | 说明                              |
| --------------------- | ------------------------------- | --------------------------------- |
| `LLM_API_KEY`       | 空                              | LLM API Key。未配置时不调用 LLM。 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容接口地址。             |
| `NLU_MODEL`         | `deepseek-chat`               | NLU 使用的模型名称。              |

LLM Prompt 会要求模型只输出 JSON，结构必须包含：

```json
{
  "understood": true,
  "reply": "已生成动作计划。",
  "actions": []
}
```

模型返回后会经过 `_validate_actions()` 校验。校验会清理：

- 不存在的设备 ID；
- 设备不支持的 command；
- 未声明的参数；
- 不符合范围的数值参数；
- 不存在的场景 ID。

如果清洗后没有合法 action，系统会回退到规则失败结果。

## 10. 手动测试

启动服务后访问：

```text
http://localhost:8100/docs
```

### 10.1 健康检查

```powershell
Invoke-RestMethod -Uri "http://localhost:8100/internal/v1/nlu/health"
```

返回示例：

```json
{
  "status": "ok",
  "module": "nlu",
  "engine": "rule",
  "strategy": "rule_first_llm_fallback"
}
```

### 10.2 规则命中测试

```powershell
$body = @{
  text = "打开客厅灯"
  conversation = @()
  devices = @(
    @{
      id = "light-living-001"
      type = "light"
      name = "客厅主灯"
      room = "客厅"
      online = $true
      commands = @(
        @{ name = "turn_on"; params = @{} },
        @{ name = "turn_off"; params = @{} },
        @{ name = "set_brightness"; params = @{ brightness = @{ type = "integer"; min = 0; max = 100 } } }
      )
    }
  )
  scenes = @()
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://localhost:8100/internal/v1/nlu/interpret" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

### 10.3 多动作测试

```powershell
$body = @{
  text = "打开客厅灯并把空调调到22度"
  conversation = @()
  devices = @(
    @{
      id = "light-living-001"
      type = "light"
      name = "客厅主灯"
      room = "客厅"
      online = $true
      commands = @(
        @{ name = "turn_on"; params = @{} }
      )
    },
    @{
      id = "ac-living-001"
      type = "air_conditioner"
      name = "客厅空调"
      room = "客厅"
      online = $true
      commands = @(
        @{ name = "set_temperature"; params = @{ temperature = @{ type = "integer"; min = 16; max = 30 } } }
      )
    }
  )
  scenes = @()
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://localhost:8100/internal/v1/nlu/interpret" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

### 10.4 LLM 兜底测试

配置 `LLM_API_KEY` 后，可以测试规则不擅长的表达：

```powershell
$body = @{
  text = "我有点冷，把客厅弄暖和一点"
  conversation = @()
  devices = @(
    @{
      id = "ac-living-001"
      type = "air_conditioner"
      name = "客厅空调"
      room = "客厅"
      online = $true
      commands = @(
        @{ name = "set_temperature"; params = @{ temperature = @{ type = "integer"; min = 16; max = 30 } } }
      )
    }
  )
  scenes = @()
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://localhost:8100/internal/v1/nlu/interpret" `
  -Method Post `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

如果没有配置 LLM，或者 LLM 调用失败，会返回规则引擎的失败结果。

## 11. 测试命令

只跑 NLU 测试：

```powershell
uv run --with pytest --with fastapi --with pydantic --with httpx --with pytest-asyncio --with python-multipart --with dashscope --with pyttsx3 --with python-dotenv pytest tests/test_nlu.py
```

跑 AI 服务全部测试：

```powershell
uv run --with pytest --with fastapi --with pydantic --with httpx --with pytest-asyncio --with python-multipart --with dashscope --with pyttsx3 --with python-dotenv pytest
```
