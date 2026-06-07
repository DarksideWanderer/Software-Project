// AI 语义理解客户端 (LLM NLU)
// 将语音文本 + 设备能力上下文交给大模型, 返回结构化操控指令。
// 支持两种后端:
//   backend  -> 队友 ai-service / 后端 NLU 路由 (POST {text, devices})
//   openai   -> 任意 OpenAI 兼容的 /chat/completions 端点 (function/JSON)
// 关键点: 用设备的"命令自省" schema 作为接地上下文, 让模型只生成合法命令。
import axios from 'axios'
import { commandContextFor } from '../utils/deviceMapping'

/** @brief 构建喂给模型的设备上下文 (精简, 含可用命令) */
export function buildDeviceContext(devices) {
  return devices.map((d) => ({
    device_id: d.id,
    name: d.name,
    type: d.type,
    room: d.room,
    commands: commandContextFor(d),
  }))
}

const SYSTEM_PROMPT = `你是智能家居语音助手的语义解析器。
根据用户的中文指令和给定的设备清单, 输出严格的 JSON, 不要任何多余文字。
JSON 格式:
{"actions":[{"device_id":"<清单中的id>","command":"<该设备commands中的命令>","params":{}}],"reply":"<简短中文回应>"}
规则:
- device_id 必须来自设备清单; command 必须来自该设备的 commands 列表。
- 数值类命令把数字放进 params, 例如 set_temperature -> {"temperature":26}; set_brightness -> {"brightness":80}; set_volume -> {"volume":30}。
- 可一次输出多条 actions (如"打开所有灯")。
- 无法匹配时返回 {"actions":[],"reply":"原因"}。`

/** @brief 归一化模型返回的 actions */
function normalizeActions(arr, devices) {
  if (!Array.isArray(arr)) return []
  const ids = new Set(devices.map((d) => d.id))
  return arr
    .map((a) => ({
      deviceId: a.device_id || a.deviceId || a.id,
      command: a.command,
      params: a.params || {},
    }))
    .filter((a) => a.deviceId && a.command && ids.has(a.deviceId))
}

/**
 * @brief 调用 AI 解析指令
 * @param text 语音文本
 * @param devices 当前设备列表
 * @param config useAIConfig 的配置对象
 * @return { ok, engine:'ai', actions:[{deviceId,command,params}], reply }
 * @throws 网络错误或未配置时抛出, 由调用方回退规则解析
 */
export async function parseWithAI(text, devices, config) {
  const context = buildDeviceContext(devices)

  if (config.mode === 'openai') {
    const url = config.endpoint || 'https://api.openai.com/v1/chat/completions'
    const resp = await axios.post(
      url,
      {
        model: config.model || 'gpt-4o-mini',
        temperature: 0,
        response_format: { type: 'json_object' },
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          {
            role: 'user',
            content: `设备清单:\n${JSON.stringify(context)}\n\n用户指令: ${text}`,
          },
        ],
      },
      {
        headers: {
          'Content-Type': 'application/json',
          ...(config.apiKey ? { Authorization: `Bearer ${config.apiKey}` } : {}),
        },
        timeout: 15000,
      },
    )
    const content = resp?.data?.choices?.[0]?.message?.content || '{}'
    const parsed = typeof content === 'string' ? JSON.parse(content) : content
    return {
      ok: true,
      engine: 'ai',
      actions: normalizeActions(parsed.actions, devices),
      reply: parsed.reply || '',
    }
  }

  // backend 模式: 交给队友的 ai-service / NLU 路由
  const url = config.endpoint || '/api/v1/ai/voice-command'
  const resp = await axios.post(
    url,
    { text, devices: context },
    { timeout: 15000, headers: { 'Content-Type': 'application/json' } },
  )
  const data = resp?.data || {}
  return {
    ok: true,
    engine: 'ai',
    actions: normalizeActions(data.actions || data.commands, devices),
    reply: data.reply || data.message || '',
  }
}
