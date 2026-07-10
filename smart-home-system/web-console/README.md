# Smart Home Web Console

`web-console` is the runnable browser client for the smart home system. It is a static HTML/CSS/JavaScript app with no build step. All device state, scene execution, assistant commands and audio replies go through `backend-core` `/api/v1`.

## Features

- Empty-home state before devices are bound.
- Add-device modal that discovers online unbound simulators from `/devices/discover`.
- Bound device cards with online, offline and conflict labels.
- Device drawer for control, display name, room and removal.
- Rule-based scene creation in a modal.
- Natural-language scene creation through `backend-core -> ai-service NLU`.
- Built-in scene execution for home, movie and away modes.
- Text assistant and browser microphone voice assistant.
- TTS reply playback through backend audio proxy.

## Files

```text
web-console/
├── index.html
├── app.js
└── styles.css
```

## Run

Preferred path: start `backend-core` and open:

```text
http://127.0.0.1:8000
```

Standalone static server:

```bash
cd smart-home-system/web-console
python -m http.server 4173
```

Then open `http://127.0.0.1:4173`.

If the static server is not same-origin with `backend-core`, configure the API base in the browser before loading the app:

```js
window.SMART_HOME_API_BASE = "http://127.0.0.1:8000/api/v1";
```

## Check

```bash
node --check app.js
```

---
[中文文档](./README_zh.md)
