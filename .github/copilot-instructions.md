# GitHub Copilot 通用规范

本文件为 GitHub Copilot 提供项目级别的编码规范与协作约定，涵盖分支命名、PR 规范、Commit 规范等。

---

## 1. 分支命名规范 (Branch Naming Convention)

所有分支必须遵循以下命名格式，便于 Copilot 和团队成员快速识别分支用途：

```
<type>/<scope>/<short-description>
```

### 1.1 分支类型 (type)

| 类型 | 说明 |
|------|------|
| `feat` | 新功能开发 |
| `bugfix` | Bug 修复 |
| `hotfix` | 紧急线上修复（直接从 main 拉取） |
| `refactor` | 代码重构（不改变功能） |
| `docs` | 文档更新 |
| `test` | 测试相关 |
| `chore` | 构建、CI、依赖等杂项 |
| `experiment` | 实验性分支 |

### 1.2 作用域 (scope)

对应子模块名称，使用小写：

| scope | 对应模块 |
|-------|----------|
| `backend` | backend-core |
| `ai` | ai-service |
| `simulator` | device-simulator |
| `app` | app-mobile |
| `deploy` | deployment |
| `all` | 跨模块改动 |

### 1.3 示例

```bash
feat/backend/add-device-shadow     # 后端新增设备影子功能
bugfix/simulator/fix-light-adapter    # 修复模拟器灯光适配器 Bug
hotfix/security-patch                 # 紧急安全补丁
refactor/ai/optimize-asr-pipeline     # 重构 AI 服务 ASR 管线
docs/all/update-api-readme            # 更新 API 文档
```

---

## 2. Commit 规范 (Commit Convention)

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### 2.1 格式要求

- **type**: `feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `style` / `perf`
- **scope**: 同分支 scope
- **subject**: 使用英文，祈使句，首字母小写，不超过 72 字符
- **body**: 说明变更原因和内容（可选）
- **footer**: 关联 Issue（如 `Closes #42`）或 Breaking Change 声明

### 2.2 示例

```
feat(backend): add device shadow sync via Redis

Implement shadow state synchronization using Redis pub/sub
to ensure real-time device state consistency across services.

Closes #23
```

```
fix(simulator): resolve LightAdapter memory leak in event loop
```

---

## 3. PR 规范 (Pull Request)

### 3.1 标题格式

```
<type>(<scope>): <简短描述>
```

与 Commit 规范一致，如：`feat(backend): add MQTT device discovery`

### 3.2 PR 描述模板

每个 PR 必须包含以下内容（模板见 `.github/PULL_REQUEST_TEMPLATE.md`）：

1. **变更说明** — 做了什么，为什么这样做
2. **关联 Issue** — 引用相关 Issue 编号
3. **测试说明** — 如何验证变更
4. **检查清单** — 提交前自查项

### 3.3 审核要求

- 至少 **1 位** 团队成员 Approve 后方可合并
- CI 全部通过（Lint + Test + Build）
- 禁止直接推送到 `main` 分支

---

## 4. 代码风格速查

Copilot 生成代码时请遵循项目 `Rule.md` 中的规范：

| 语言 | 格式化 | 命名风格 |
|------|--------|----------|
| Python | `black` | 类: `PascalCase`，函数/变量: `snake_case` |
| C++ | `clang-format` (Google) | 类: `PascalCase`，方法: `camelCase`，成员: `snake_case_` |
| API 路径 | — | kebab-case: `/api/v1/device-control` |

---

## 5. 目录约定

```
smart-home-system/
├── backend-core/        # FastAPI 后端
├── ai-service/          # AI 推理服务
├── device-simulator/    # C++ 设备模拟器
├── app-mobile/          # Flutter 移动端
├── deployment/          # Docker & CI/CD
├── tool/                # 工具文档
└── sprint1/             # Sprint 1 产出
```
