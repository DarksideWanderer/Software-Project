# 智能家居 Web 控制台

`web-console` 是当前项目可运行的浏览器客户端。它是无构建步骤的静态 HTML/CSS/JavaScript 应用。所有设备状态、场景执行、助手命令和语音回复都通过 `backend-core` 的 `/api/v1` 完成。

## 功能

- 家庭初始为空，绑定设备后才显示家电卡片。
- “添加家电”弹窗通过 `/devices/discover` 检索在线且未绑定的模拟器。
- 已绑定设备卡片显示在线、离线和冲突状态。
- 设备详情抽屉支持控制、修改显示名称、修改房间和移除设备。
- 规则场景在弹窗中创建。
- 自然语言场景通过 `backend-core -> ai-service NLU` 创建。
- 保留回家、观影、离家预设场景。
- 支持文本助手和浏览器麦克风语音助手。
- TTS 回复音频通过后端代理播放。

## 文件

```text
web-console/
├── index.html
├── app.js
└── styles.css
```

## 运行

推荐方式：启动 `backend-core` 后直接访问：

```text
http://127.0.0.1:8000
```

也可以单独启动静态服务：

```bash
cd smart-home-system/web-console
python -m http.server 4173
```

然后访问 `http://127.0.0.1:4173`。

如果静态服务和 `backend-core` 不同源，可以在浏览器加载前配置：

```js
window.SMART_HOME_API_BASE = "http://127.0.0.1:8000/api/v1";
```

## 检查

```bash
node --check app.js
```
