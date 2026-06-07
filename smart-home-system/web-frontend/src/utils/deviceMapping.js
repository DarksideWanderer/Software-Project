// 前端模型 <-> 后端模型 的双向映射层。
// 后端 (C++ 设备) 使用 snake_case 类型与 is_on/temperature 等字段;
// 前端使用通用分类 (ac/light/tv...) 与 power/targetTemp 等字段。
// 这一层把二者解耦, 便于联调时灰度对接。
import { defaultStateFor, getCategory } from '../data/catalog'

// 后端 device_type -> 前端 type
const TYPE_FROM_BACKEND = {
  air_conditioner: 'ac',
  ac: 'ac',
  light: 'light',
  tv: 'tv',
  curtain: 'curtain',
  fan: 'fan',
  air_purifier: 'purifier',
  purifier: 'purifier',
  vacuum: 'vacuum',
  lock: 'lock',
  camera: 'camera',
  plug: 'plug',
  water_heater: 'waterHeater',
  sensor: 'sensor',
}

/** @brief 后端类型 -> 前端类型 */
export function typeFromBackend(backendType) {
  return TYPE_FROM_BACKEND[backendType] || 'light'
}

/**
 * @brief 后端原始状态 -> 前端状态对象
 * @details 以前端默认状态为底, 覆盖后端提供的已知字段, 保证 UI 字段完整。
 */
export function stateFromBackend(type, raw = {}) {
  const s = defaultStateFor(type)
  if ('is_on' in raw) s.power = !!raw.is_on
  if ('power' in raw) s.power = !!raw.power

  switch (type) {
    case 'ac':
      if ('temperature' in raw) s.targetTemp = raw.temperature
      if ('target_temp' in raw) s.targetTemp = raw.target_temp
      if ('current_temp' in raw) s.currentTemp = raw.current_temp
      if ('mode' in raw) s.mode = raw.mode
      if ('fan' in raw) s.fan = raw.fan
      break
    case 'light':
      if ('brightness' in raw) s.brightness = raw.brightness
      if ('color_temp' in raw) s.colorTemp = raw.color_temp
      if ('scene' in raw) s.scene = raw.scene
      break
    case 'tv':
      if ('volume' in raw) s.volume = raw.volume
      if ('muted' in raw) s.mute = !!raw.muted
      if ('mute' in raw) s.mute = !!raw.mute
      if ('source' in raw) s.source = raw.source
      break
    case 'curtain':
      if ('position' in raw) s.position = raw.position
      break
    case 'lock':
      if ('locked' in raw) s.locked = !!raw.locked
      break
    default:
      // 其余字段同名直接拷贝
      for (const k of Object.keys(s)) if (k in raw) s[k] = raw[k]
  }
  return s
}

// 前端状态字段 -> 后端命令构造器
// 每项返回 { command, params } 或 null
const FIELD_TO_COMMAND = {
  power: (v) => ({ command: v ? 'turn_on' : 'turn_off', params: {} }),
  targetTemp: (v) => ({ command: 'set_temperature', params: { temperature: v } }),
  brightness: (v) => ({ command: 'set_brightness', params: { brightness: v } }),
  colorTemp: (v) => ({ command: 'set_color_temp', params: { color_temp: v } }),
  scene: (v) => ({ command: 'set_scene', params: { scene: v } }),
  volume: (v) => ({ command: 'set_volume', params: { volume: v } }),
  mute: (v) => ({ command: v ? 'mute' : 'unmute', params: {} }),
  source: (v) => ({ command: 'set_source', params: { source: v } }),
  mode: (v) => ({ command: 'set_mode', params: { mode: v } }),
  fan: (v) => ({ command: 'set_fan', params: { fan: v } }),
  position: (v) => ({ command: 'set_position', params: { position: v } }),
  locked: (v) => ({ command: v ? 'lock' : 'unlock', params: {} }),
  speed: (v) => ({ command: 'set_speed', params: { speed: v } }),
}

/**
 * @brief 前端状态补丁 -> 后端命令序列
 * @param patch 形如 { power:true, targetTemp:26 }
 * @param available 可选, 设备实际支持的命令名数组; 提供则过滤掉不支持的命令
 * @return [{command, params}]
 */
export function commandsFromPatch(patch, available = null) {
  const cmds = []
  // 先处理开机, 再处理参数, 关机最后 (避免"先关再设"无效)
  const order = Object.keys(patch).sort((a, b) => {
    const score = (k) => (k === 'power' && patch[k] ? -1 : k === 'power' && !patch[k] ? 1 : 0)
    return score(a) - score(b)
  })
  for (const key of order) {
    const build = FIELD_TO_COMMAND[key]
    if (!build) continue
    const c = build(patch[key])
    if (available && !available.includes(c.command)) continue
    cmds.push(c)
  }
  return cmds
}

/**
 * @brief 后端命令 -> 前端状态补丁 (本地模式下执行 AI/语音命令时使用)
 */
export function patchFromCommand(command, params = {}) {
  switch (command) {
    case 'turn_on': return { power: true }
    case 'turn_off': return { power: false }
    case 'set_temperature': return { targetTemp: params.temperature }
    case 'set_brightness': return { brightness: params.brightness }
    case 'set_color_temp': return { colorTemp: params.color_temp }
    case 'set_scene': return { scene: params.scene }
    case 'set_volume': return { volume: params.volume }
    case 'mute': return { mute: true }
    case 'unmute': return { mute: false }
    case 'set_source': return { source: params.source }
    case 'set_mode': return { mode: params.mode }
    case 'set_fan': return { fan: params.fan }
    case 'set_position': return { position: params.position }
    case 'set_speed': return { speed: params.speed }
    case 'lock': return { locked: true }
    case 'unlock': return { locked: false }
    case 'get_state': return {}
    default: return {}
  }
}

/**
 * @brief 为某设备生成"可用命令上下文" (供 AI 接地)
 * @details 实时模式优先用后端自省得到的命令; 否则由前端能力模型推导。
 */
export function commandContextFor(device) {
  if (device._commands && device._commands.length) {
    return device._commands
  }
  // 由 catalog 能力推导伪命令列表
  const caps = getCategory(device.type).capabilities
  const out = []
  if (getCategory(device.type).powerKey) {
    out.push('turn_on', 'turn_off')
  }
  for (const c of caps) {
    if (c.kind === 'slider') out.push(FIELD_TO_COMMAND[c.key] ? FIELD_TO_COMMAND[c.key](c.min).command : `set_${c.key}`)
    if (c.kind === 'mode') out.push(FIELD_TO_COMMAND[c.key] ? FIELD_TO_COMMAND[c.key](c.options[0].value).command : `set_${c.key}`)
  }
  return Array.from(new Set(out))
}
