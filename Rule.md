# 项目开发规范 (Development Rules)

本文件定义了智能家居系统的开发流程、代码风格及工程标准。所有贡献者必须严格遵守。

---

## 1. 代码风格规范 (Coding Style)

### 1.1 Python (后端与 AI 服务)
*   **遵循标准**：遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范。
*   **格式化工具**：统一使用 `black` 进行自动格式化。
*   **类型检查**：必须使用 `mypy` 进行静态类型注解（Type Hinting）。
*   **命名约定**：
    *   类名：`PascalCase` (如 `DeviceManager`)
    *   函数与变量：`snake_case` (如 `get_device_status`)
    *   常量：`UPPER_SNAKE_CASE` (如 `MAX_RETRY_COUNT`)

### 1.2 C++ (设备模拟器)
*   **遵循标准**：[Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html)。
*   **标准版本**：使用 C++20 特性。
*   **格式化工具**：使用 `clang-format` (基于 Google 配置)。
*   **命名约定**：
    *   类名：`PascalCase`
    *   方法名：`camelCase` (如 `sendPayload`)
    *   私有成员：`snake_case_` (带下划线结尾，如 `device_id_`)

---

## 2. 接口规范 (API Specification)

项目采用 RESTful 风格的 API 设计，并由 FastAPI 自动生成文档。

*   **路径命名**：使用小写字母及中划线（kebab-case），如 `/api/v1/smart-lights/control`。
*   **版本控制**：所有 API 必须以前缀 `/api/v[n]/` 开头，避免破坏性变更影响旧客户端。
*   **请求与响应**：
    *   统一使用 JSON 格式。
    *   响应成功：HTTP 200/201，返回数据对象。
    *   响应失败：HTTP 4xx/5xx，返回统一格式：`{"error_code": 4001, "message": "Invalid device ID"}`。
*   **状态码建议**：
    *   200 (OK): 请求成功。
    *   201 (Created): 资源创建成功。
    *   400 (Bad Request): 参数错误。
    *   401 (Unauthorized): 鉴权失败。
    *   404 (Not Found): 资源不存在。

---

## 3. 注释规范 (Documentation - Doxygen)

所有核心头文件（C++）及核心逻辑（Python）必须包含符合 Doxygen 格式的文档注释。

### 3.1 C++ 示例 (Header File)
```cpp
/**
 * @brief 设备基类，定义通用控制接口
 * @author [姓名]
 * @date 2024-05-20
 */
class BaseDevice {
public:
    /**
     * @brief 发送控制指令
     * @param cmd 指令代码
     * @param value 指令参数
     * @return true 指令执行成功
     * @return false 指令执行失败
     */
    virtual bool sendCommand(int cmd, float value) = 0;
};
```

### 3.2 Python 示例 (FastAPI Controller)
```python
def control_light(light_id: str, brightness: float):
    \"\"\"
    控制灯光亮度的 API 接口
    
    :param light_id: 灯具的唯一标识符
    :param brightness: 亮度值 (0.0 - 1.0)
    :return: 执行状态结果字典
    \"\"\"
    pass
```

---

## 4. 测试规范 (Testing)

### 4.1 单元测试要求
*   **Python**: 使用 `pytest`。测试文件位于 `tests/` 目录，命名以 `test_` 开头。
*   **C++**: 使用 `Google Test (GTest)`。
*   **覆盖率**：核心业务逻辑的行覆盖率（Line Coverage）必须达到 **80%** 以上。

### 4.2 持续集成 (CI)
*   所有提交必须通过 Github Actions 的 CI 检查，包括：
    *   代码格式检查。
    *   静态类型检查。
    *   所有自动化测试用例通过。

---

## 5. PR 规范及基本流程 (Pull Request & Workflow)

项目采用 **Git Flow** 简化版流程。

### 5.1 分支策略
*   `main`: 稳定版分支，仅接受从 `develop` 合并的发布代码。
*   `develop`: 所有的集成测试分之。
*   `feat/[feature-name]`: 新功能开发。
*   `fix/[issue-number]`: Bug 修复。

### 5.2 提交说明 (Commit Message)
必须遵循 [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) 规范：
*   `feat`: 新增功能。
*   `fix`: 修复 Bug。
*   `docs`: 仅文档更新。
*   `style`: 格式调整（不改变逻辑）。
*   `refactor`: 重构代码。

**格式样例**：`feat: add speech recognition support for light control`

### 5.3 PR 提交流程
1.  **本地开发**：拉取最新的 `develop`，创建 `feat/xxx` 分支。
2.  **自测**：确保本地 `pytest` 或 `GTest` 全部通过。
3.  **提交 PR**：
    *   标题需描述清晰（如：实现空调节点模拟）。
    *   关联对应的 Issue（如果有）。
4.  **代码评审 (Code Review)**：至少由一名其他团队成员 Review 并在 GitHub 上批准（Approve）。
5.  **合并**：Review 通过后，由负责人合并入 `develop` 分支。
