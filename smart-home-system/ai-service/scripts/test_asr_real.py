#!/usr/bin/env python3
"""ASR 真实语音转写测试（非 Mock）

方案：TTS 往返测试 (Round-Trip Test)
  1. pyttsx3 将已知中文文本合成为 WAV 音频
  2. 将 WAV 文件上传到 /internal/v1/asr/transcriptions
  3. 比较转写结果与原始文本

同时支持：
  - 直接上传已有的 WAV/OGG/WebM 音频文件进行测试
  - 不依赖任何 Mock 引擎

用法:
    # 方式 1：往返测试（需要 espeak-ng + pyttsx3）
    python scripts/test_asr_real.py --mode roundtrip

    # 方式 2：上传已有音频文件
    python scripts/test_asr_real.py --mode file --audio /path/to/audio.wav

    # 方式 3：启动服务后手动测试（输出 curl 命令）
    python scripts/test_asr_real.py --mode manual

前提：AI Service 需已在 8001 端口运行
    uvicorn src.main:app --port 8001
"""

import argparse
import io
import json
import os
import sys
import time
import urllib.request
import urllib.error
import wave

BASE_URL = "http://127.0.0.1:8001"

# ── 测试用例：要合成并转写的文本 ──────────────────────────────────────

ROUNDTRIP_TEXTS = [
    "打开客厅灯",
    "把空调调到二十六度",
    "关闭电视",
    "打开所有灯",
    "设置观影模式",
]

# pinyin 映射（espeak-ng 中文 TTS 质量有限，用拼音可获更好效果）
_PINYIN_MAP = {
    "打开客厅灯": "da kai ke ting deng",
    "把空调调到二十六度": "ba kong tiao tiao dao er shi liu du",
    "关闭电视": "guan bi dian shi",
    "打开所有灯": "da kai suo you deng",
    "设置观影模式": "she zhi guan ying mo shi",
}


def _post_asr(audio_bytes: bytes, filename: str = "test.wav", content_type: str = "audio/wav") -> dict:
    """向 ASR 端点发送音频，返回响应。"""
    boundary = "----TestBoundaryASR"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + audio_bytes + f"\r\n--{boundary}--\r\n".encode()

    url = f"{BASE_URL}/internal/v1/asr/transcriptions"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return {"status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return {"status": e.code, "body": body}


def _get_health() -> dict:
    """获取 ASR 健康状态。"""
    with urllib.request.urlopen(f"{BASE_URL}/ai/asr/health", timeout=5) as resp:
        return json.loads(resp.read())


def _generate_wav(text: str, use_pinyin: bool = False) -> bytes:
    """使用 pyttsx3 将文本合成为 WAV 音频字节。

    Args:
        text: 要合成的文本。
        use_pinyin: 如果为 True，使用拼音输入 + Pinyin 语音以获得更好的中文效果。
    """
    import pyttsx3
    import tempfile

    tmpdir = tempfile.mkdtemp()
    wav_path = os.path.join(tmpdir, "tts_output.wav")

    engine = pyttsx3.init()
    try:
        if use_pinyin:
            # 使用 Pinyin 语音（需要 espeak-ng 支持）
            for v in engine.getProperty("voices"):
                if "pinyin" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 120)
            speak_text = _PINYIN_MAP.get(text, text)
        else:
            # 尝试中文语音
            voices = engine.getProperty("voices")
            for v in voices:
                if "mandarin" in v.name.lower() and "pinyin" not in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 150)
            speak_text = text

        engine.save_to_file(speak_text, wav_path)
        engine.runAndWait()
    finally:
        pass

    if not os.path.isfile(wav_path) or os.path.getsize(wav_path) == 0:
        raise RuntimeError(f"TTS 合成失败: {text}")

    with open(wav_path, "rb") as f:
        audio_bytes = f.read()

    os.remove(wav_path)
    os.rmdir(tmpdir)

    return audio_bytes


def _simplify(text: str) -> str:
    """简化文本用于比较：去标点、去空格、数字转换。"""
    import re
    # 汉字数字转换
    cn_num = {"零": "0", "一": "1", "二": "2", "三": "3", "四": "4",
              "五": "5", "六": "6", "七": "7", "八": "8", "九": "9",
              "十": "10", "百": "100"}
    # 去掉标点和空格
    text = re.sub(r"[，,。！？、\s]", "", text)
    return text


def _text_match(original: str, transcribed: str) -> tuple[bool, float]:
    """检查转写文本是否与原文匹配。

    返回 (是否完全匹配, 相似度百分比)。
    由于 TTS→ASR 过程中可能有同音字差异，使用宽松比较。
    """
    orig = _simplify(original)
    trans = _simplify(transcribed)

    if orig == trans:
        return True, 100.0

    # 计算字符重叠率
    orig_set = set(orig)
    trans_set = set(trans)
    if not orig_set:
        return False, 0.0
    overlap = len(orig_set & trans_set) / len(orig_set) * 100
    return False, round(overlap, 1)


def test_roundtrip():
    """往返测试：TTS 合成 → ASR 转写 → 文本对比。"""
    print("=" * 60)
    print("  ASR 真实语音转写测试 — TTS 往返测试")
    print(f"  服务地址: {BASE_URL}")
    print("=" * 60)

    # 检查引擎
    health = _get_health()
    engine = health.get("engine", "unknown")
    print(f"\n  ASR 引擎: {engine}")
    if engine == "mock":
        print("  ⚠️  当前为 Mock 引擎（讯飞 API 未配置或不可用）")
        print("  配置方法：在 .env 中设置 IFLYTEK_APP_ID, IFLYTEK_API_KEY, IFLYTEK_API_SECRET")
    print()

    results = []
    total_start = time.perf_counter()

    for i, text in enumerate(ROUNDTRIP_TEXTS, 1):
        print(f"  [{i}/{len(ROUNDTRIP_TEXTS)}] 原文: \"{text}\"")

        try:
            # 1. TTS 合成音频（使用拼音模式以获得更好中文效果）
            tts_start = time.perf_counter()
            audio_bytes = _generate_wav(text, use_pinyin=True)
            tts_ms = int((time.perf_counter() - tts_start) * 1000)
            print(f"       TTS 合成: {len(audio_bytes)} bytes ({tts_ms}ms)")

            # 2. ASR 转写
            asr_start = time.perf_counter()
            resp = _post_asr(audio_bytes, filename=f"tts_{i}.wav", content_type="audio/wav")
            asr_ms = int((time.perf_counter() - asr_start) * 1000)

            if resp["status"] != 200:
                print(f"       ❌ ASR 失败: HTTP {resp['status']} {resp['body']}")
                results.append((text, False))
                continue

            body = resp["body"]
            transcribed = body.get("text", "")
            confidence = body.get("confidence", 0)
            used_engine = body.get("engine", "?")

            # 3. 对比
            matched, similarity = _text_match(text, transcribed)
            status_icon = "✅" if matched else "⚠️"
            print(f"       转写: \"{transcribed}\" ({used_engine}, 置信度={confidence}, {asr_ms}ms)")
            print(f"       {status_icon} 匹配: {'完全匹配' if matched else f'相似度 {similarity}%'}")
            results.append((text, matched))

        except Exception as e:
            print(f"       ❌ 错误: {e}")
            results.append((text, False))

    # ── 汇总 ──────────────────────────────────────────────────────
    total_ms = int((time.perf_counter() - total_start) * 1000)
    print(f"\n{'=' * 60}")
    print(f"  测试汇总 ({total_ms}ms)")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for text, ok in results:
        print(f"  {'✅' if ok else '⚠️'} \"{text}\"")
    print(f"\n  完全匹配: {passed}/{total}")
    if engine == "iflytek":
        if passed >= total * 0.6:
            print("  🎉 真实 ASR 引擎工作正常！")
        else:
            print("  ⚠️  匹配率较低，可能是 TTS 发音或 ASR 模型导致")
    print()


def test_file(audio_path: str):
    """上传已有音频文件进行 ASR 测试。"""
    print("=" * 60)
    print("  ASR 真实语音转写测试 — 文件上传")
    print(f"  服务地址: {BASE_URL}")
    print(f"  音频文件: {audio_path}")
    print("=" * 60)

    if not os.path.isfile(audio_path):
        print(f"\n  ❌ 文件不存在: {audio_path}")
        sys.exit(1)

    file_size = os.path.getsize(audio_path)
    print(f"\n  文件大小: {file_size} bytes ({file_size / 1024:.1f} KB)")

    # 推断 content-type
    ext = os.path.splitext(audio_path)[1].lower()
    mime_map = {
        ".wav": "audio/wav", ".wave": "audio/wav",
        ".webm": "audio/webm", ".ogg": "audio/ogg", ".opus": "audio/ogg",
    }
    content_type = mime_map.get(ext, "audio/wav")
    print(f"  Content-Type: {content_type}")

    # 检查引擎
    health = _get_health()
    print(f"  ASR 引擎: {health.get('engine', 'unknown')}")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    print(f"\n  正在上传...")
    start = time.perf_counter()
    resp = _post_asr(audio_bytes, filename=os.path.basename(audio_path), content_type=content_type)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if resp["status"] != 200:
        print(f"  ❌ HTTP {resp['status']}: {resp['body']}")
        sys.exit(1)

    body = resp["body"]
    print(f"\n  转写结果:")
    print(f"    文本:     \"{body.get('text', '')}\"")
    print(f"    置信度:   {body.get('confidence', 0)}")
    print(f"    语言:     {body.get('language', '?')}")
    print(f"    引擎:     {body.get('engine', '?')}")
    print(f"    处理时间: {elapsed_ms}ms")
    print(f"    音频时长: {body.get('duration_ms', '?')}ms")
    print(f"    Request:  {body.get('request_id', '?')}")


def test_manual():
    """打印手动测试用的 curl 命令。"""
    print("=" * 60)
    print("  ASR 手动测试指南")
    print("=" * 60)

    health = _get_health()
    print(f"\n  引擎状态: {health.get('engine', 'unknown')}")
    print(f"  服务地址: {BASE_URL}")
    print()
    print("  # 1. 使用 curl 上传 WAV 文件:")
    print(f"  curl -X POST {BASE_URL}/internal/v1/asr/transcriptions \\")
    print(f"    -F \"audio=@/path/to/audio.wav;type=audio/wav\"")
    print()
    print("  # 2. 检查 ASR 引擎:")
    print(f"  curl {BASE_URL}/ai/asr/health")
    print()
    print("  # 3. 用 Python requests 上传:")
    print("  import requests")
    print(f"  resp = requests.post('{BASE_URL}/internal/v1/asr/transcriptions',")
    print("      files={'audio': ('test.wav', open('test.wav', 'rb'), 'audio/wav')})")
    print("  print(resp.json())")
    print()
    print("  # 4. 生成测试音频 (TTS → ASR):")
    print("  #   pip install pyttsx3")
    print("  #   python -c \"import pyttsx3; e=pyttsx3.init(); e.save_to_file('打开客厅灯', 'test.wav'); e.runAndWait()\"")
    print(f"  #   curl -X POST {BASE_URL}/internal/v1/asr/transcriptions -F \"audio=@test.wav;type=audio/wav\"")
    print()


def main():
    parser = argparse.ArgumentParser(description="ASR 真实语音转写测试")
    parser.add_argument("--mode", choices=["roundtrip", "file", "manual"], default="roundtrip",
                        help="测试模式: roundtrip(TTS→ASR往返), file(上传音频文件), manual(打印命令)")
    parser.add_argument("--audio", type=str, help="音频文件路径 (mode=file 时必需)")
    args = parser.parse_args()

    # 检查服务
    try:
        _get_health()
    except Exception as e:
        print(f"❌ 无法连接 AI Service ({BASE_URL})")
        print(f"   请先启动: uvicorn src.main:app --port 8001")
        print(f"   错误: {e}")
        sys.exit(1)

    if args.mode == "roundtrip":
        test_roundtrip()
    elif args.mode == "file":
        if not args.audio:
            print("❌ --mode file 需要指定 --audio 参数")
            sys.exit(1)
        test_file(args.audio)
    elif args.mode == "manual":
        test_manual()


if __name__ == "__main__":
    main()
