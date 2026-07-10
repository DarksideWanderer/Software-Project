#!/usr/bin/env python3
"""
综合测试报告生成器
收集所有测试模块的 JUnit XML 结果和日志，生成统一报告

运行: python3 tests/generate_final_report.py
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATA_DIR = PROJECT_ROOT / "docs"
REPORT_FILE = TEST_DATA_DIR / "final_test_report.md"


def parse_junit_xml(filepath: str) -> dict:
    """解析 JUnit XML 测试结果"""
    if not os.path.exists(filepath):
        return {"status": "not_found", "tests": 0, "passed": 0, "failed": 0, "errors": 0, "time": 0}

    tree = ET.parse(filepath)
    root = tree.getroot()

    # 聚合所有 testsuite
    total = 0
    passed = 0
    failures = 0
    errors = 0
    total_time = 0.0
    suites = []

    for suite in root.iter("testsuite"):
        t = int(suite.attrib.get("tests", 0))
        f = int(suite.attrib.get("failures", 0))
        e = int(suite.attrib.get("errors", 0))
        time_val = float(suite.attrib.get("time", 0))
        total += t
        failures += f
        errors += e
        total_time += time_val

        suite_data = {
            "name": suite.attrib.get("name", "unknown"),
            "tests": t,
            "time": time_val,
        }
        cases = []
        for case in suite.findall("testcase"):
            case_data = {
                "name": case.attrib.get("name", ""),
                "classname": case.attrib.get("classname", ""),
                "time": float(case.attrib.get("time", 0)),
                "status": "passed"
            }
            if case.find("failure") is not None:
                case_data["status"] = "failed"
                case_data["message"] = case.find("failure").attrib.get("message", "")[:200]
            elif case.find("error") is not None:
                case_data["status"] = "error"
                case_data["message"] = case.find("error").attrib.get("message", "")[:200]
            cases.append(case_data)
        suite_data["cases"] = cases
        suites.append(suite_data)

    passed = total - failures - errors

    return {
        "status": "ok",
        "tests": total,
        "passed": passed,
        "failed": failures,
        "errors": errors,
        "time": round(total_time, 2),
        "suites": suites,
    }


def collect_module_detail(log_file: str) -> dict:
    """从日志文件中提取按测试类的分布信息"""
    if not os.path.exists(log_file):
        return {"classes": []}

    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()

    classes = {}
    for line in content.split("\n"):
        if "::" in line and ("PASSED" in line or "FAILED" in line):
            parts = line.split("::")
            if len(parts) >= 2:
                # Extract class name (before ::, after the last .)
                class_part = parts[0]
                class_name = class_part.rsplit(".", 1)[-1] if "." in class_part else class_part
                if class_name not in classes:
                    classes[class_name] = {"passed": 0, "failed": 0}
                if "PASSED" in line:
                    classes[class_name]["passed"] += 1
                elif "FAILED" in line:
                    classes[class_name]["failed"] += 1

    return {"classes": [{"name": k, **v} for k, v in classes.items()]}


def generate_report():
    """生成综合测试报告"""
    modules = {
        "backend-core": {
            "xml": str(TEST_DATA_DIR / "backend_core_results.xml"),
            "log": str(TEST_DATA_DIR / "backend_core_full.log"),
            "description": "FastAPI 后端核心服务 — 设备管理、场景编排、状态持久化"
        },
        "ai-service": {
            "xml": str(TEST_DATA_DIR / "ai_service_results.xml"),
            "log": str(TEST_DATA_DIR / "ai_service_full.log"),
            "description": "AI 服务 — NLU 意图解析、ASR 语音识别、TTS 语音合成"
        },
        "integration": {
            "xml": str(TEST_DATA_DIR / "integration_results.xml"),
            "log": str(TEST_DATA_DIR / "integration_full.log"),
            "description": "端到端集成测试 — 设备生命周期、场景流程、仪表盘、AI 助手"
        },
    }

    all_results = {}
    grand_total = 0
    grand_passed = 0
    grand_failed = 0
    grand_time = 0.0

    for mod_name, mod_info in modules.items():
        result = parse_junit_xml(mod_info["xml"])
        detail = collect_module_detail(mod_info["log"])
        result["detail"] = detail
        result["description"] = mod_info["description"]
        all_results[mod_name] = result
        grand_total += result["tests"]
        grand_passed += result["passed"]
        grand_failed += result["failed"]
        grand_time += result["time"]

    # Build markdown report
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report = f"""# 智能家居中控系统 — 综合测试报告

> **生成时间**: {now}
> **项目版本**: v2.0.0
> **测试框架**: pytest {sys.version.split()[0]}

---

## 📊 总体结果

| 指标 | 数值 |
|------|------|
| **测试模块数** | {len(modules)} |
| **测试用例总数** | {grand_total} |
| **✅ 通过** | {grand_passed} |
| **❌ 失败** | {grand_failed} |
| **📈 通过率** | {grand_passed / grand_total * 100:.1f}% |
| **⏱ 总耗时** | {grand_time:.2f}s |

```mermaid
pie title 测试结果分布 ({grand_total} cases)
    "通过" : {grand_passed}
    "失败" : {grand_failed}
```

---

## 📋 各模块详情

"""

    for mod_name, result in all_results.items():
        pass_rate = result["passed"] / result["tests"] * 100 if result["tests"] > 0 else 0
        report += f"""### {mod_name}
> {result['description']}

| 指标 | 数值 |
|------|------|
| 用例总数 | {result['tests']} |
| 通过 | {result['passed']} |
| 失败 | {result['failed']} |
| 通过率 | {pass_rate:.1f}% |
| 耗时 | {result['time']:.2f}s |

"""

        # Class-level breakdown
        classes = result.get("detail", {}).get("classes", [])
        if classes:
            report += "| 测试类 | 通过 | 失败 |\n"
            report += "|--------|------|------|\n"
            for cls in classes:
                report += f"| {cls['name']} | {cls['passed']} | {cls['failed']} |\n"
            report += "\n"

        # All test cases
        suites = result.get("suites", [])
        if suites:
            report += "<details>\n<summary>📝 全部用例详情</summary>\n\n"
            report += "| 测试类 | 用例 | 状态 | 耗时 |\n"
            report += "|--------|------|------|------|\n"
            for suite in suites:
                for case in suite.get("cases", []):
                    status_icon = "✅" if case["status"] == "passed" else "❌"
                    report += f"| {case['classname']} | {case['name']} | {status_icon} | {case['time']:.3f}s |\n"
            report += "\n</details>\n\n"

    # Data files section
    data_files = sorted(TEST_DATA_DIR.glob("*.json"))
    report += """---

## 📦 生成的测试数据文件

| 文件 | 大小 | 说明 |
|------|------|------|
"""
    for df in data_files:
        size_kb = df.stat().st_size / 1024
        report += f"| `{df.name}` | {size_kb:.1f} KB | 测试数据文件 |\n"

    log_files = sorted(TEST_DATA_DIR.glob("*.log"))
    for lf in log_files:
        size_kb = lf.stat().st_size / 1024
        report += f"| `{lf.name}` | {size_kb:.1f} KB | 测试执行日志 |\n"

    xml_files = sorted(TEST_DATA_DIR.glob("*.xml"))
    for xf in xml_files:
        size_kb = xf.stat().st_size / 1024
        report += f"| `{xf.name}` | {size_kb:.1f} KB | JUnit XML 报告 |\n"

    report += f"""
---

## 🗂 测试文件清单

### backend-core (`backend-core/tests/`)
| 文件 | 测试内容 |
|------|----------|
| `test_schemas.py` | Pydantic 数据模型 (CommandRequest/Response) |
| `test_orchestrator.py` | 业务编排层：状态读写、设备发现/绑定/控制、参数校验、场景管理、动作排序 |
| `test_device_hub.py` | DeviceHub TCP：连接管理、命令转发、命令查询 |
| `test_api.py` | REST API：Dashboard/Devices/Scenes/Assistant/CORS |

### ai-service (`ai-service/tests/`)
| 文件 | 测试内容 |
|------|----------|
| `test_nlu_rules.py` | NLU：设备匹配、批量匹配、命令识别、Interpret 端点、LLM 引擎 |
| `test_asr.py` | ASR：MIME 校验、WAV 解析、错误响应、转录端点 |
| `test_tts.py` | TTS：模型验证、MIME 映射、音频清理、健康检查 |

### device-simulator (`device-simulator/tests/`)
| 文件 | 测试内容 |
|------|----------|
| `test_core.cpp` | GTest：CommandRegistry、Light/AC/TV/GenericDevice、Adapter 注册 |

### web-console (`web-console/tests/`)
| 文件 | 测试内容 |
|------|----------|
| `test_app.test.js` | Jest：HTML 转义、API 请求、设备归一化、语音处理、DOM 渲染 |

### 集成测试 (`tests/integration/`)
| 文件 | 测试内容 |
|------|----------|
| `test_e2e_flow.py` | E2E：设备生命周期、场景 CRUD、仪表盘、AI 助手流程 |

---

*本报告由 `generate_final_report.py` 自动生成*
"""
    # Write report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 综合测试报告已生成: {REPORT_FILE}")
    print(f"   总计: {grand_total} 用例, {grand_passed} 通过, {grand_failed} 失败")
    return all_results


if __name__ == "__main__":
    generate_report()
