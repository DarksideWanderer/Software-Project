// AI 语义理解客户端 (LLM NLU)
// 将语音文本交给 AI, 返回可执行的结构化操控指令。
// 支持两种后端:
//   backend  -> 队友 ai-service 的 NLU 路由 (POST /ai/nlu, 返回 intent+slots)
//   openai   -> 任意 OpenAI 兼容的 /chat/completions 端点 (function/JSON, 直接返回 actions)
//
// ⚠ 契约说明 (proj/feature/ai 分支, ai-service):
//   POST /ai/nlu   请求 { text, context? }
//                  响应 { success, intent, confidence, slots, need_clarification, reply }
//   slots = { device_type, location, action, value, unit, city, datetime, content }
//   注意: ai-service 只做"槽位填充", 不认识具体 device_id / 命令名。
//   因此 backend 模式下, 由本文件的 resolveSlotsToActions() 把
//   (device_type + location + action + value) 解析为本地设备上的 {deviceId, command, params}。
import axios from 'axios'
import { commandContextFor, typeFromBackend } from '../utils/deviceMapping'

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

  // backend 模式: 交给队友的 ai-service NLU 路由 (POST /ai/nlu)
  // 该服务默认运行在 8100 端口, 经 vite 代理 /ai -> http://localhost:8100。
  const url = config.endpoint || '/ai/nlu'
  const resp = await axios.post(
    url,
    { text, context: config.context || undefined },
    { timeout: 15000, headers: { 'Content-Type': 'application/json' } },
  )
  const nlu = resp?.data || {}
  const slots = nlu.slots || {}
  const isDevice = nlu.intent === 'device_control' || nlu.intent === 'device_query'

  // 需要澄清, 或非设备类意图 (天气/提醒/场景/未知): 不生成 actions, 仅回传 reply。
  if (!isDevice || nlu.need_clarification) {
    return {
      ok: true,
      engine: 'ai',
      actions: [],
      reply: nlu.reply || '',
      handled: Boolean(nlu.reply), // 已被 AI 处理 (有回复), 调用方据此决定是否回退规则
      needClarification: Boolean(nlu.need_clarification),
    }
  }

  return {
    ok: true,
    engine: 'ai',
    actions: resolveSlotsToActions(slots, devices),
    reply: nlu.reply || '',
    handled: true,
  }
}

// ai-service 的 location 枚举 (英文) -> 前端房间名包含的关键字
const LOCATION_TO_ROOM = {
  living_room: '客厅',
  bedroom: '卧',
  study: '书房',
  kitchen: '厨房',
  balcony: '阳台',
}

function clampPct(v) {
  return Math.max(0, Math.min(100, Math.round(v)))
}

/**
 * @brief 把单个 NLU 动作映射到前端命令 (沿用 deviceMapping 的命令词表)
 * @details 相对动作 (increase/decrease) 基于该设备当前状态计算绝对值。
 * @return { command, params } 或 null (无需下发命令, 如 query_status)
 */
function actionToCommand(action, value, device) {
  const st = (device && device.state) || {}
  switch (action) {
    case 'turn_on':
      return { command: 'turn_on', params: {} }
    case 'turn_off':
      return { command: 'turn_off', params: {} }
    case 'set_temperature':
      return { command: 'set_temperature', params: { temperature: value } }
    case 'increase_temperature':
      return { command: 'set_temperature', params: { temperature: (st.targetTemp ?? 26) + (value || 1) } }
    case 'decrease_temperature':
      return { command: 'set_temperature', params: { temperature: (st.targetTemp ?? 26) - (value || 1) } }
    case 'set_brightness':
      return { command: 'set_brightness', params: { brightness: clampPct(value ?? 100) } }
    case 'increase_brightness':
      return { command: 'set_brightness', params: { brightness: clampPct((st.brightness ?? 50) + (value || 10)) } }
    case 'decrease_brightness':
      return { command: 'set_brightness', params: { brightness: clampPct((st.brightness ?? 50) - (value || 10)) } }
    case 'open':
      return { command: 'set_position', params: { position: 100 } }
    case 'close':
      return { command: 'set_position', params: { position: 0 } }
    case 'set_open_percent':
      return { command: 'set_position', params: { position: clampPct(value ?? 50) } }
    case 'query_status':
    default:
      return null // 查询类无需下发命令, 由 reply 呈现
  }
}

/**
 * @brief 把 ai-service 的槽位解析为本地设备上的可执行 actions
 * @param slots  { device_type, location, action, value }
 * @param devices 当前设备列表 (store.devices)
 * @return [{ deviceId, command, params }]
 * @details 选择策略: 按 device_type 过滤; 指定 location 时再按房间过滤;
 *          未指定房间则作用于该类型全部设备 (支持"打开所有灯")。
 */
export function resolveSlotsToActions(slots, devices) {
  if (!slots || !slots.action || !slots.device_type) return []
  const feType = typeFromBackend(slots.device_type)
  if (!feType) return []

  let targets = devices.filter((d) => d.type === feType)
  const roomKey = slots.location ? LOCATION_TO_ROOM[slots.location] : null
  if (roomKey) {
    const inRoom = targets.filter((d) => (d.room || '').includes(roomKey))
    if (inRoom.length) targets = inRoom // 房间无匹配时退回该类型全部, 避免空操作
  }

  const out = []
  for (const d of targets) {
    const c = actionToCommand(slots.action, slots.value, d)
    if (c) out.push({ deviceId: d.id, command: c.command, params: c.params })
  }
  return out
}
