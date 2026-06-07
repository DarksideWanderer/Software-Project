// 轻量中文语音指令解析 (NLU)
// 将识别到的自然语言文本解析为对家电的操控计划。
// 设计目标: 覆盖常见口语表达, 同时基于"能力模型"保持通用。
import { getCategory } from '../data/catalog'

// 分类关键词 -> 通用分类 type
const TYPE_WORDS = [
  ['灯光', 'light'], ['台灯', 'light'], ['吊灯', 'light'], ['电灯', 'light'], ['灯', 'light'],
  ['空调', 'ac'], ['冷气', 'ac'], ['暖气', 'ac'],
  ['窗帘', 'curtain'], ['帘', 'curtain'],
  ['电视', 'tv'],
  ['风扇', 'fan'], ['电扇', 'fan'],
  ['净化器', 'purifier'], ['空气', 'purifier'],
  ['扫地机器人', 'vacuum'], ['扫地机', 'vacuum'], ['扫地', 'vacuum'],
  ['门锁', 'lock'], ['锁', 'lock'], ['门', 'lock'],
  ['摄像头', 'camera'], ['监控', 'camera'], ['相机', 'camera'],
  ['插座', 'plug'],
  ['热水器', 'waterHeater'],
  ['传感器', 'sensor'], ['温湿度', 'sensor'],
]

// 情景模式关键词
const SCENES = [
  { key: 'home', words: ['回家模式', '回家', '我回来了', '到家'], label: '回家模式' },
  { key: 'away', words: ['离家模式', '离家', '出门', '我走了'], label: '离家模式' },
  { key: 'night', words: ['晚安模式', '晚安', '睡觉', '睡眠模式'], label: '晚安模式' },
  { key: 'allOff', words: ['全部关闭', '一键全关', '全关', '关闭所有', '关掉所有', '全部关掉'], label: '一键全关' },
]

const digits = { 零: 0, 一: 1, 二: 2, 两: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 }
const units = { 十: 10, 百: 100 }

/** @brief 中文数字串转数值 (支持 0-999) */
function zhToNum(str) {
  let section = 0
  let num = 0
  for (const ch of str) {
    if (ch in digits) num = digits[ch]
    else if (ch in units) {
      section += (num === 0 ? 1 : num) * units[ch]
      num = 0
    } else return null
  }
  return section + num
}

/** @brief 从文本中提取数值, 返回 {value, unit} 或 null */
function extractNumber(text) {
  const arabic = text.match(/(\d+(?:\.\d+)?)/)
  let value = null
  if (arabic) value = parseFloat(arabic[1])
  else {
    const zh = text.match(/[零一二两三四五六七八九十百]+/)
    if (zh) value = zhToNum(zh[0])
  }
  if (value === null || Number.isNaN(value)) return null
  let unit = ''
  if (/度|℃/.test(text)) unit = '℃'
  else if (/%|百分/.test(text)) unit = '%'
  else if (/音量|声音/.test(text)) unit = 'vol'
  return { value, unit }
}

/** @brief 在文本中识别分类 type */
function detectType(text) {
  for (const [word, type] of TYPE_WORDS) {
    if (text.includes(word)) return type
  }
  return null
}

/** @brief 在文本中识别房间 (依据现有设备的房间名) */
function detectRoom(text, devices) {
  const rooms = Array.from(new Set(devices.map((d) => d.room)))
  for (const r of rooms) {
    if (text.includes(r)) return r
  }
  // 常见别名: "卧室" 匹配主卧/次卧
  if (text.includes('卧室')) {
    const m = rooms.find((r) => r.includes('卧'))
    if (m) return m
  }
  return null
}

/** @brief 解析目标设备集合 */
function resolveTargets(text, devices, type) {
  // 1. 直接命名匹配
  const byName = devices.filter((d) => text.includes(d.name))
  if (byName.length) return byName

  const room = detectRoom(text, devices)
  const all = /所有|全部|全屋|都/.test(text)

  if (type && room) return devices.filter((d) => d.type === type && d.room === room)
  if (type) {
    const list = devices.filter((d) => d.type === type)
    return all ? list : list
  }
  if (room) return devices.filter((d) => d.room === room)
  return []
}

/** @brief 选取设备的主滑块能力 (用于数值/增减) */
function primarySlider(type, unit) {
  const caps = getCategory(type).capabilities.filter((c) => c.kind === 'slider')
  if (!caps.length) return null
  if (unit === '℃') return caps.find((c) => c.unit === '℃') || caps[0]
  if (unit === '%') return caps.find((c) => c.unit === '%') || caps[0]
  if (unit === 'vol') return caps.find((c) => c.key === 'volume') || caps[0]
  return caps.find((c) => c.summary) || caps[0]
}

function clamp(v, c) {
  return Math.max(c.min, Math.min(c.max, Math.round(v / (c.step || 1)) * (c.step || 1)))
}

/**
 * @brief 解析语音文本为操控计划
 * @param raw 识别到的文本
 * @param devices 当前设备列表
 * @return { ok, action, scene?, targets:[{id,name,patch}], summary, hint? }
 */
export function parseCommand(raw, devices) {
  const text = (raw || '').trim()
  if (!text) return { ok: false, hint: '没有听清，请再说一次' }

  // 情景模式
  for (const sc of SCENES) {
    if (sc.words.some((w) => text.includes(w))) {
      return { ok: true, action: 'scene', scene: sc.key, summary: `执行情景：${sc.label}` }
    }
  }

  const type = detectType(text)
  const targets = resolveTargets(text, devices, type)
  const names = targets.map((t) => t.name).join('、')

  // 增减 (调亮/调暗/大一点/高一点...)
  const incWords = /(调亮|亮一点|亮点|调高|高一点|大一点|调大|增大|升高|提高|再亮)/
  const decWords = /(调暗|暗一点|暗点|调低|低一点|小一点|调小|减小|降低|再暗)/
  const isInc = incWords.test(text)
  const isDec = decWords.test(text)

  // 静音
  if (/静音/.test(text)) {
    const tvs = targets.length ? targets : devices.filter((d) => d.type === 'tv')
    if (!tvs.length) return { ok: false, hint: '没有找到可静音的设备' }
    const mute = !/取消静音|解除静音/.test(text)
    return {
      ok: true, action: 'mute',
      targets: tvs.map((d) => ({ id: d.id, name: d.name, patch: { mute } })),
      summary: `${mute ? '已静音' : '已取消静音'} ${tvs.map((d) => d.name).join('、')}`,
    }
  }

  // 门锁
  if (type === 'lock' || /锁门|上锁|开锁|解锁/.test(text)) {
    const locks = targets.length ? targets.filter((d) => d.type === 'lock') : devices.filter((d) => d.type === 'lock')
    if (!locks.length) return { ok: false, hint: '没有找到门锁设备' }
    const unlock = /开锁|解锁|开门/.test(text) && !/关门|上锁|锁门/.test(text)
    return {
      ok: true, action: unlock ? 'unlock' : 'lock',
      targets: locks.map((d) => ({ id: d.id, name: d.name, patch: { locked: !unlock } })),
      summary: `${unlock ? '已开锁' : '已上锁'} ${locks.map((d) => d.name).join('、')}`,
    }
  }

  if (!targets.length) {
    return { ok: false, hint: type ? '没有找到对应的设备' : '没有识别到设备，请说明要控制的家电' }
  }

  // 数值设定 / 增减
  const num = extractNumber(text)
  if (isInc || isDec || (num && /(调|设|到|成|为|至)/.test(text)) || (num && type)) {
    const built = []
    for (const d of targets) {
      const slider = primarySlider(d.type, num?.unit)
      if (!slider) continue
      let val
      if (isInc || isDec) {
        const delta = slider.max - slider.min >= 40 ? 10 : 1
        val = clamp((d.state[slider.key] ?? slider.min) + (isInc ? delta : -delta), slider)
      } else {
        val = clamp(num.value, slider)
      }
      const cat = getCategory(d.type)
      const patch = { [slider.key]: val }
      if (cat.powerKey) patch[cat.powerKey] = true // 调节即开机
      built.push({ id: d.id, name: d.name, patch, _label: slider.label, _val: val, _unit: slider.unit })
    }
    if (!built.length) return { ok: false, hint: '该设备不支持此调节' }
    const one = built.length === 1 ? built[0] : null
    return {
      ok: true, action: isInc || isDec ? 'adjust' : 'set',
      targets: built.map(({ id, name, patch }) => ({ id, name, patch })),
      summary: one
        ? `已将 ${one.name} 的${one._label}${isInc || isDec ? '调整为' : '设为'} ${one._val}${one._unit}`
        : `已调整 ${names} 的${built[0]._label}`,
    }
  }

  // 开 / 关
  const isOff = /(关闭|关掉|关上|关一下|关)/.test(text) && !/开/.test(text)
  const isOn = /(打开|开启|启动|开)/.test(text)
  if (isOff || isOn) {
    const on = isOn && !isOff
    const built = []
    for (const d of targets) {
      const cat = getCategory(d.type)
      let patch = null
      if (cat.powerKey) patch = { [cat.powerKey]: on }
      else if (d.type === 'curtain') patch = { position: on ? 100 : 0 }
      else if (d.type === 'vacuum') patch = on ? { running: true, action: 'clean' } : { running: false, action: 'idle' }
      else if (d.type === 'lock') patch = { locked: !on }
      if (patch) built.push({ id: d.id, name: d.name, patch })
    }
    if (!built.length) return { ok: false, hint: '该设备不支持开关操作' }
    return {
      ok: true, action: on ? 'on' : 'off',
      targets: built,
      summary: `${on ? '已开启' : '已关闭'} ${built.map((b) => b.name).join('、')}`,
    }
  }

  return { ok: false, hint: '没有理解这条指令，换种说法试试' }
}

// 示例指令 (用于界面引导与无麦克风时演示)
export const EXAMPLE_COMMANDS = [
  '打开客厅的灯',
  '把客厅空调调到26度',
  '客厅灯调亮一点',
  '关闭电视',
  '打开窗帘',
  '锁门',
  '电视音量调到30',
  '回家模式',
]
