#!/usr/bin/env python3
"""本地音频 → ASR → NLU 流水线测试"""
import json, sys, urllib.request, urllib.error

BASE = "http://127.0.0.1:8001"
AUDIO_FILE = "./output.wav"

# 测试设备列表（需与 backend-core 中的设备注册表一致）
DEVICES = [
    {"id":"ac-living-001","type":"air_conditioner","name":"中央空调","room":"客厅","online":True,
     "commands":[{"name":"turn_on","params":{}},{"name":"turn_off","params":{}},
                 {"name":"set_temperature","params":{"temperature":{"type":"integer","min":16,"max":30}}}]},
    {"id":"light-living-001","type":"light","name":"客厅主灯","room":"客厅","online":True,
     "commands":[{"name":"turn_on","params":{}},{"name":"turn_off","params":{}},
                 {"name":"set_brightness","params":{"brightness":{"type":"integer","min":0,"max":100}}}]},
    {"id":"tv-living-001","type":"tv","name":"智能电视","room":"客厅","online":True,
     "commands":[{"name":"turn_on","params":{}},{"name":"turn_off","params":{}}]},
]
SCENES = [{"id":"home","name":"回家"},{"id":"movie","name":"观影"},{"id":"sleep","name":"睡眠"}]

def post_json(path, data):
    req = urllib.request.Request(f"{BASE}{path}",
        data=json.dumps(data).encode(), headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def post_audio(path, audio_bytes, content_type="audio/wav"):
    boundary = "----PipelineTest"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"test.wav\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n").encode() + audio_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

# Step 1: ASR 转写
with open(AUDIO_FILE, "rb") as f:
    audio = f.read()

asr = post_audio("/internal/v1/asr/transcriptions", audio)
text = asr["text"]
print(f"[ASR] 转写文本: \"{text}\"  (引擎: {asr.get('engine')}, 置信度: {asr.get('confidence')})")

# Step 2: NLU 意图解析
nlu = post_json("/internal/v1/nlu/interpret", {
    "text": text,
    "devices": DEVICES,
    "scenes": SCENES,
})
print(f"[NLU] 理解: {'是' if nlu['understood'] else '否'} | 回复: \"{nlu['reply']}\"")
for action in nlu.get("actions", []):
    if action.get("kind") == "device_command":
        print(f"  → 设备: {action['device_id']}, 命令: {action['command']}, 参数: {action.get('params', {})}")
    elif action.get("kind") == "scene":
        print(f"  → 场景: {action['scene_id']}")

print(f"\n✅ 流水线完成: 音频 → \"{text}\" → {len(nlu['actions'])} 个动作")