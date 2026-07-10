#!/usr/bin/env python3
"""
测试数据生成器 — 生成测试数据、运行测试并收集日志输出

功能:
1. 生成标准测试数据文件 (home_state.json, NLU 测试数据等)
2. 运行 pytest 并收集测试报告
3. 生成 log 输出文件

运行方式:
  cd smart-home-system
  python tests/generate_test_data.py [--all] [--output-dir=./tests/test_data]
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ======================== 配置 ========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "docs"
LOG_FILE = OUTPUT_DIR / "test_run.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("test-data-generator")


# ======================== 测试数据生成 ========================


def generate_home_state() -> dict:
    """生成标准家庭状态数据"""
    return {
        "bound_devices": {
            "ac-003": {
                "id": "ac-003",
                "type": "air_conditioner",
                "name": "客厅空调",
                "room": "客厅",
                "original_name": "ac-003"
            },
            "ac-004": {
                "id": "ac-004",
                "type": "air_conditioner",
                "name": "主卧空调",
                "room": "主卧",
                "original_name": "ac-004"
            },
            "light-001": {
                "id": "light-001",
                "type": "light",
                "name": "客厅主灯",
                "room": "客厅",
                "original_name": "light-001"
            },
            "light-002": {
                "id": "light-002",
                "type": "light",
                "name": "卧室氛围灯",
                "room": "卧室",
                "original_name": "light-002"
            },
            "tv-001": {
                "id": "tv-001",
                "type": "tv",
                "name": "客厅电视",
                "room": "客厅",
                "original_name": "tv-001"
            },
            "fridge-001": {
                "id": "fridge-001",
                "type": "fridge",
                "name": "厨房冰箱",
                "room": "厨房",
                "original_name": "fridge-001"
            },
            "washer-001": {
                "id": "washer-001",
                "type": "washer",
                "name": "阳台洗衣机",
                "room": "阳台",
                "original_name": "washer-001"
            },
            "heater-001": {
                "id": "heater-001",
                "type": "water_heater",
                "name": "浴室热水器",
                "room": "浴室",
                "original_name": "heater-001"
            },
            "purifier-001": {
                "id": "purifier-001",
                "type": "air_purifier",
                "name": "客厅净化器",
                "room": "客厅",
                "original_name": "purifier-001"
            },
            "curtain-001": {
                "id": "curtain-001",
                "type": "curtain",
                "name": "卧室窗帘",
                "room": "卧室",
                "original_name": "curtain-001"
            },
            "socket-001": {
                "id": "socket-001",
                "type": "socket",
                "name": "书房插座",
                "room": "书房",
                "original_name": "socket-001"
            },
            "robot-001": {
                "id": "robot-001",
                "type": "robot_vacuum",
                "name": "扫地机器人",
                "room": "全屋",
                "original_name": "robot-001"
            }
        },
        "device_states": {
            "ac-003": {"device_id": "ac-003", "device_type": "air_conditioner",
                        "is_on": True, "temperature": 24},
            "ac-004": {"device_id": "ac-004", "device_type": "air_conditioner",
                        "is_on": False, "temperature": 26},
            "light-001": {"device_id": "light-001", "device_type": "light",
                          "is_on": True, "brightness": 80, "color": "daylight"},
            "light-002": {"device_id": "light-002", "device_type": "light",
                          "is_on": False, "brightness": 50, "color": "warm"},
            "tv-001": {"device_id": "tv-001", "device_type": "tv",
                       "is_on": True, "channel": 5, "volume": 35},
            "fridge-001": {"device_id": "fridge-001", "device_type": "fridge",
                           "is_on": True, "temperature": 4},
            "washer-001": {"device_id": "washer-001", "device_type": "washer",
                           "is_on": False, "progress": 0},
            "heater-001": {"device_id": "heater-001", "device_type": "water_heater",
                           "is_on": False, "temperature": 45},
            "purifier-001": {"device_id": "purifier-001", "device_type": "air_purifier",
                             "is_on": True, "speed": 3, "air_quality": 42},
            "curtain-001": {"device_id": "curtain-001", "device_type": "curtain",
                            "is_on": True, "percent": 75},
            "socket-001": {"device_id": "socket-001", "device_type": "socket",
                           "is_on": False},
            "robot-001": {"device_id": "robot-001", "device_type": "robot_vacuum",
                          "is_on": False, "battery": 82},
        },
        "user_scenes": {
            "user-abc12345": {
                "id": "user-abc12345",
                "name": "晚安模式",
                "description": "关闭客厅所有设备",
                "commands": [
                    {"device_id": "light-001", "command": "turn_off", "params": {}},
                    {"device_id": "tv-001", "command": "turn_off", "params": {}},
                    {"device_id": "ac-003", "command": "turn_off", "params": {}},
                ],
                "builtin": False,
            },
            "user-def67890": {
                "id": "user-def67890",
                "name": "阅读模式",
                "description": "调暗灯光，舒适温度",
                "commands": [
                    {"device_id": "light-001", "command": "turn_on", "params": {}},
                    {"device_id": "light-001", "command": "set_brightness",
                     "params": {"brightness": 40}},
                    {"device_id": "ac-003", "command": "set_temperature",
                     "params": {"temperature": 25}},
                ],
                "builtin": False,
            }
        }
    }


def generate_nlu_test_cases() -> list[dict]:
    """生成 NLU 测试用例"""
    return [
        {
            "id": "NLU-001",
            "text": "打开客厅灯",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "light-001",
                     "command": "turn_on", "params": {}}
                ]
            }
        },
        {
            "id": "NLU-002",
            "text": "把空调调到26度",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "ac-003",
                     "command": "set_temperature", "params": {"temperature": 26}}
                ]
            }
        },
        {
            "id": "NLU-003",
            "text": "关闭电视",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "tv-001",
                     "command": "turn_off", "params": {}}
                ]
            }
        },
        {
            "id": "NLU-004",
            "text": "进入观影模式",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "scene", "scene_id": "movie"}
                ]
            }
        },
        {
            "id": "NLU-005",
            "text": "打开客厅灯并关闭电视",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "light-001",
                     "command": "turn_on", "params": {}},
                    {"kind": "device_command", "device_id": "tv-001",
                     "command": "turn_off", "params": {}}
                ]
            }
        },
        {
            "id": "NLU-006",
            "text": "打开所有灯",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "light-001",
                     "command": "turn_on", "params": {}},
                    {"kind": "device_command", "device_id": "light-002",
                     "command": "turn_on", "params": {}}
                ]
            }
        },
        {
            "id": "NLU-007",
            "text": "把卧室灯调到50",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "light-002",
                     "command": "set_brightness", "params": {"brightness": 50}}
                ]
            }
        },
        {
            "id": "NLU-008",
            "text": "帮我弄一下那个东西",
            "expected": {
                "understood": False,
                "actions": []
            }
        },
        {
            "id": "NLU-009",
            "text": "把冰箱温度调到零下18度",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "fridge-001",
                     "command": "set_temperature", "params": {"temperature": -18}}
                ]
            }
        },
        {
            "id": "NLU-010",
            "text": "窗帘开到一半",
            "expected": {
                "understood": True,
                "actions": [
                    {"kind": "device_command", "device_id": "curtain-001",
                     "command": "set_open_percent", "params": {"percent": 50}}
                ]
            }
        },
    ]


def generate_device_command_test_data() -> list[dict]:
    """生成设备命令测试数据"""
    return [
        # 空调
        {"device_id": "ac-003", "command": "turn_on", "params": {},
         "expected_success": True},
        {"device_id": "ac-003", "command": "turn_off", "params": {},
         "expected_success": True},
        {"device_id": "ac-003", "command": "set_temperature", "params": {"temperature": 22},
         "expected_success": True},
        {"device_id": "ac-003", "command": "set_temperature", "params": {"temperature": 100},
         "expected_success": True, "note": "clamped to 30"},
        {"device_id": "ac-003", "command": "set_temperature", "params": {"temperature": -5},
         "expected_success": True, "note": "clamped to 16"},

        # 灯
        {"device_id": "light-001", "command": "turn_on", "params": {},
         "expected_success": True},
        {"device_id": "light-001", "command": "set_brightness", "params": {"brightness": 60},
         "expected_success": True},
        {"device_id": "light-001", "command": "set_color", "params": {"color": "warm"},
         "expected_success": True},

        # 电视
        {"device_id": "tv-001", "command": "set_channel", "params": {"channel": 8},
         "expected_success": True},
        {"device_id": "tv-001", "command": "set_volume", "params": {"volume": 45},
         "expected_success": True},

        # 窗帘
        {"device_id": "curtain-001", "command": "set_open_percent",
         "params": {"percent": 50}, "expected_success": True},
    ]


def generate_edge_case_data() -> dict:
    """生成边界条件测试数据"""
    return {
        "binding_conflicts": [
            {"device_id": "ac-003", "attempt": "rebind", "expected_status": 409},
            {"device_id": "ac-003", "attempt": "bind with type mismatch",
             "expected_status": 409, "note": "type conflict"},
        ],
        "invalid_device_ids": [
            "nonexistent-999",
            "",
            "invalid!@#",
            "ac" + "x" * 100,
        ],
        "invalid_params": [
            {"command": "set_temperature", "params": {}},
            {"command": "set_temperature", "params": {"not_a_param": 1}},
            {"command": "unknown_command", "params": {}},
        ],
        "boundary_values": {
            "ac_temperature": {"min": 16, "max": 30, "below": -999, "above": 999},
            "light_brightness": {"min": 0, "max": 100, "below": -999, "above": 999},
            "tv_volume": {"min": 0, "max": 100, "below": -999, "above": 999},
            "tv_channel": {"min": 1, "max": 999, "below": -999, "above": 9999},
        }
    }


# ======================== 数据写入 ========================


def write_json(data, filename: str):
    """写入 JSON 文件"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Wrote: %s (%d bytes)", filepath, filepath.stat().st_size)


def generate_all_test_data():
    """生成所有测试数据文件"""
    logger.info("=" * 60)
    logger.info("Generating Test Data")
    logger.info("=" * 60)

    # 1. 家庭状态数据
    home_state = generate_home_state()
    write_json(home_state, "home_state.json")
    logger.info("  - 12 bound devices")
    logger.info("  - 12 device states")
    logger.info("  - 2 user scenes")

    # 2. NLU 测试用例
    nlu_cases = generate_nlu_test_cases()
    write_json(nlu_cases, "nlu_test_cases.json")
    logger.info("  - %d NLU test cases", len(nlu_cases))

    # 3. 设备命令测试数据
    cmd_data = generate_device_command_test_data()
    write_json(cmd_data, "device_command_test_data.json")
    logger.info("  - %d command test cases", len(cmd_data))

    # 4. 边界条件数据
    edge_cases = generate_edge_case_data()
    write_json(edge_cases, "edge_cases.json")

    # 5. 测试报告模板
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "Smart Home Hub v2.0.0",
        "test_data_files": [
            "home_state.json",
            "nlu_test_cases.json",
            "device_command_test_data.json",
            "edge_cases.json",
        ],
        "modules": {
            "backend-core": "tests/test_*.py (3 files)",
            "ai-service": "tests/test_*.py (3 files)",
            "device-simulator": "tests/test_core.cpp (GTest)",
            "web-console": "tests/test_app.test.js (Jest)",
        }
    }
    write_json(report, "test_report_meta.json")

    logger.info("All test data generated in: %s", OUTPUT_DIR)


# ======================== 测试运行 ========================


def run_pytest(module_dir: str, test_pattern: str = "tests/test_*.py") -> dict:
    """运行 pytest 并收集结果"""
    dir_path = PROJECT_ROOT / module_dir
    if not dir_path.exists():
        return {"module": module_dir, "status": "skipped",
                "reason": f"Directory not found: {dir_path}"}

    # 查找测试文件
    test_files = list(dir_path.glob(test_pattern))
    if not test_files:
        return {"module": module_dir, "status": "skipped",
                "reason": "No test files found"}

    logger.info("Running tests in: %s", module_dir)
    cmd = [
        sys.executable, "-m", "pytest",
        str(dir_path / "tests"),
        "-v",
        "--tb=short",
        "--no-header",
        f"--rootdir={dir_path}",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(dir_path),
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONPATH": str(dir_path)},
        )
        return {
            "module": module_dir,
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout[-5000:],  # 保留最后 5000 字符
            "stderr": result.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"module": module_dir, "status": "timeout", "reason": "Test timed out"}
    except FileNotFoundError:
        return {"module": module_dir, "status": "skipped",
                "reason": "pytest not found"}


def run_all_tests() -> dict:
    """运行所有测试并返回汇总"""
    logger.info("=" * 60)
    logger.info("Running All Tests")
    logger.info("=" * 60)

    results = {}

    # backend-core 测试
    results["backend-core"] = run_pytest("backend-core", "tests/test_*.py")

    # ai-service 测试
    results["ai-service"] = run_pytest("ai-service", "tests/test_*.py")

    # 集成测试
    results["integration"] = run_pytest(".", "tests/integration/test_*.py")

    # 汇总
    total = len(results)
    passed = sum(1 for r in results.values() if r["status"] == "passed")
    failed = sum(1 for r in results.values() if r["status"] == "failed")
    skipped = sum(1 for r in results.values() if r["status"] == "skipped")

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_modules": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }

    write_json(summary, "test_results_summary.json")

    logger.info("--- Test Summary ---")
    logger.info("  Total:  %d", total)
    logger.info("  Passed: %d", passed)
    logger.info("  Failed: %d", failed)
    logger.info("  Skipped: %d", skipped)

    return summary


# ======================== Log 导出 ========================


def export_logs(summary: dict):
    """导出测试日志为可读格式"""
    log_text_path = OUTPUT_DIR / "test_run_report.txt"
    with open(log_text_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  智能家居中控系统 - 测试运行报告\n")
        f.write(f"  生成时间: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"模块总数: {summary['total_modules']}\n")
        f.write(f"通过:     {summary['passed']}\n")
        f.write(f"失败:     {summary['failed']}\n")
        f.write(f"跳过:     {summary['skipped']}\n\n")

        for module, result in summary.get("results", {}).items():
            f.write(f"--- {module} ---\n")
            f.write(f"  状态: {result['status']}\n")
            if result["status"] == "failed":
                f.write(f"  返回码: {result.get('returncode')}\n")
            if result.get("reason"):
                f.write(f"  原因: {result['reason']}\n")
            if result.get("stdout"):
                f.write(f"\n  标准输出:\n{result['stdout']}\n")
            if result.get("stderr"):
                f.write(f"\n  标准错误:\n{result['stderr']}\n")
            f.write("\n")

    logger.info("Log report written: %s", log_text_path)


# ======================== 主入口 ========================


def main():
    global OUTPUT_DIR
    import argparse
    parser = argparse.ArgumentParser(description="测试数据生成与测试运行")
    parser.add_argument("--all", action="store_true",
                        help="生成数据 + 运行所有测试")
    parser.add_argument("--data-only", action="store_true",
                        help="仅生成测试数据")
    parser.add_argument("--test-only", action="store_true",
                        help="仅运行测试")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR),
                        help="输出目录")
    args = parser.parse_args()

    OUTPUT_DIR = Path(args.output_dir)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info("Test Data Generator for Smart Home Hub v2.0.0")
    logger.info("Output directory: %s", OUTPUT_DIR)

    if args.data_only or args.all:
        generate_all_test_data()

    if args.test_only or args.all:
        summary = run_all_tests()
        export_logs(summary)

    if not (args.data_only or args.test_only or args.all):
        # 默认：仅生成数据
        generate_all_test_data()

    logger.info("Done.")


if __name__ == "__main__":
    main()
