# Smart Home Mobile App

This directory is reserved for a future mobile client. The current runnable client is `../web-console`, and all implemented product flows are exposed through `backend-core` `/api/v1`.

## Current Status

- No mobile application source code is present in this directory.
- No mobile-client dependency is required for the current project demo.
- Mobile development should reuse the same backend APIs used by `web-console`.

## API Boundary

A future mobile client should call only:

```text
backend-core /api/v1
```

It should not call `ai-service` or DeviceHub directly.

## Related Modules

- `../web-console`: current browser client
- `../backend-core`: API gateway and business orchestration
- `../ai-service`: internal ASR/NLU/TTS service
- `../device-simulator`: local device processes

---
[中文文档](./README_zh.md)
