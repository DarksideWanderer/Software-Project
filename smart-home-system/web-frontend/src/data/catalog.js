// 通用家电分类目录 (Generic Device Catalog)
// 采用"能力驱动"模型: 每个分类由一组 capabilities 描述,
// 同一套控件渲染逻辑即可适配所有家电, 通用且易扩展。
//
// capability.kind 取值:
//   toggle  - 开关 (boolean)
//   slider  - 连续数值 (亮度/温度/音量/开合度)
//   mode    - 互斥选项 (制冷/制热...)
//   action  - 触发型按钮 (回充/启动)
//   metric  - 只读读数 (PM2.5/电量/功率)

/**
 * @brief 家电分类定义表
 * @details key 为通用分类标识, 不绑定具体型号
 */
export const catalog = {
  light: {
    type: 'light',
    label: '智能灯',
    tagline: '照明 · 调光调色',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '客厅',
    powerKey: 'power',
    state: { power: true, brightness: 80, colorTemp: 4000, scene: 'reading' },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      { key: 'brightness', kind: 'slider', label: '亮度', min: 1, max: 100, step: 1, unit: '%', needPower: true, summary: true },
      { key: 'colorTemp', kind: 'slider', label: '色温', min: 2700, max: 6500, step: 100, unit: 'K', needPower: true },
      {
        key: 'scene', kind: 'mode', label: '灯光场景', needPower: true,
        options: [
          { value: 'reading', label: '阅读' },
          { value: 'warm', label: '温馨' },
          { value: 'movie', label: '影院' },
          { value: 'party', label: '聚会' },
        ],
      },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已关闭' }
      return { active: true, text: `亮度 ${s.brightness}%` }
    },
  },

  ac: {
    type: 'ac',
    label: '空调',
    tagline: '温控 · 多模式',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '卧室',
    powerKey: 'power',
    state: { power: false, targetTemp: 26, mode: 'cool', fan: 'auto', currentTemp: 28 },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      { key: 'targetTemp', kind: 'slider', label: '目标温度', min: 16, max: 30, step: 1, unit: '℃', needPower: true, summary: true },
      {
        key: 'mode', kind: 'mode', label: '运行模式', needPower: true,
        options: [
          { value: 'cool', label: '制冷' },
          { value: 'heat', label: '制热' },
          { value: 'fan', label: '送风' },
          { value: 'dry', label: '除湿' },
          { value: 'auto', label: '自动' },
        ],
      },
      {
        key: 'fan', kind: 'mode', label: '风速', needPower: true,
        options: [
          { value: 'auto', label: '自动' },
          { value: 'low', label: '低' },
          { value: 'mid', label: '中' },
          { value: 'high', label: '高' },
        ],
      },
      { key: 'currentTemp', kind: 'metric', label: '室温', unit: '℃' },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已关闭' }
      const m = { cool: '制冷', heat: '制热', fan: '送风', dry: '除湿', auto: '自动' }[s.mode]
      return { active: true, text: `${m} ${s.targetTemp}℃` }
    },
  },

  curtain: {
    type: 'curtain',
    label: '智能窗帘',
    tagline: '电动 · 开合控制',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '客厅',
    powerKey: null,
    state: { position: 60 },
    capabilities: [
      { key: 'position', kind: 'slider', label: '开合度', min: 0, max: 100, step: 1, unit: '%', summary: true },
    ],
    status(s) {
      if (s.position <= 0) return { active: false, text: '已闭合' }
      if (s.position >= 100) return { active: true, text: '全开' }
      return { active: true, text: `开启 ${s.position}%` }
    },
  },

  tv: {
    type: 'tv',
    label: '智能电视',
    tagline: '影音 · 信号源',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '客厅',
    powerKey: 'power',
    state: { power: false, volume: 25, mute: false, source: 'tv' },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      { key: 'volume', kind: 'slider', label: '音量', min: 0, max: 100, step: 1, unit: '', needPower: true, summary: true },
      { key: 'mute', kind: 'toggle', label: '静音', needPower: true },
      {
        key: 'source', kind: 'mode', label: '信号源', needPower: true,
        options: [
          { value: 'tv', label: '电视' },
          { value: 'hdmi1', label: 'HDMI 1' },
          { value: 'hdmi2', label: 'HDMI 2' },
          { value: 'cast', label: '投屏' },
        ],
      },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已关闭' }
      return { active: true, text: s.mute ? '静音' : `音量 ${s.volume}` }
    },
  },

  fan: {
    type: 'fan',
    label: '电风扇',
    tagline: '送风 · 摇头',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '书房',
    powerKey: 'power',
    state: { power: false, speed: 2, swing: true, mode: 'normal' },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      { key: 'speed', kind: 'slider', label: '风速档位', min: 1, max: 5, step: 1, unit: '档', needPower: true, summary: true },
      { key: 'swing', kind: 'toggle', label: '左右摇头', needPower: true },
      {
        key: 'mode', kind: 'mode', label: '送风模式', needPower: true,
        options: [
          { value: 'normal', label: '标准' },
          { value: 'natural', label: '自然风' },
          { value: 'sleep', label: '睡眠' },
        ],
      },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已关闭' }
      return { active: true, text: `${s.speed} 档` }
    },
  },

  purifier: {
    type: 'purifier',
    label: '空气净化器',
    tagline: '净化 · 空气质量',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '卧室',
    powerKey: 'power',
    state: { power: true, mode: 'auto', pm25: 16, filter: 86 },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      {
        key: 'mode', kind: 'mode', label: '运行模式', needPower: true,
        options: [
          { value: 'auto', label: '自动' },
          { value: 'sleep', label: '睡眠' },
          { value: 'turbo', label: '强力' },
        ],
      },
      { key: 'pm25', kind: 'metric', label: 'PM2.5', unit: 'μg' },
      { key: 'filter', kind: 'metric', label: '滤芯寿命', unit: '%' },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已关闭' }
      return { active: true, text: `PM2.5 ${s.pm25}` }
    },
  },

  vacuum: {
    type: 'vacuum',
    label: '扫地机器人',
    tagline: '清扫 · 自动回充',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '客厅',
    powerKey: null,
    state: { running: false, mode: 'standard', battery: 78, action: 'idle' },
    capabilities: [
      {
        key: 'mode', kind: 'mode', label: '清扫模式',
        options: [
          { value: 'quiet', label: '安静' },
          { value: 'standard', label: '标准' },
          { value: 'strong', label: '强力' },
        ],
      },
      {
        key: 'action', kind: 'action', label: '操作',
        actions: [
          { value: 'clean', label: '开始清扫', set: { running: true, action: 'clean' } },
          { value: 'pause', label: '暂停', set: { running: false, action: 'idle' } },
          { value: 'dock', label: '回充', set: { running: false, action: 'dock' } },
        ],
      },
      { key: 'battery', kind: 'metric', label: '电量', unit: '%' },
    ],
    status(s) {
      const map = { clean: '清扫中', dock: '回充中', idle: '待机' }
      return { active: s.running, text: map[s.action] || '待机' }
    },
  },

  lock: {
    type: 'lock',
    label: '智能门锁',
    tagline: '安防 · 远程开锁',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '入户门',
    powerKey: null,
    state: { locked: true, battery: 92 },
    capabilities: [
      { key: 'locked', kind: 'toggle', label: '上锁状态', onLabel: '已上锁', offLabel: '已开锁' },
      { key: 'battery', kind: 'metric', label: '电量', unit: '%' },
    ],
    status(s) {
      return { active: s.locked, text: s.locked ? '已上锁' : '已开锁' }
    },
  },

  camera: {
    type: 'camera',
    label: '摄像头',
    tagline: '监控 · 移动侦测',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '玄关',
    powerKey: 'power',
    state: { power: true, recording: true, motion: true },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      { key: 'recording', kind: 'toggle', label: '录像', needPower: true },
      { key: 'motion', kind: 'toggle', label: '移动侦测', needPower: true },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已关闭' }
      return { active: true, text: s.recording ? '监控中' : '已待机' }
    },
  },

  plug: {
    type: 'plug',
    label: '智能插座',
    tagline: '通断 · 功率计量',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '书房',
    powerKey: 'power',
    state: { power: true, watt: 120 },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      { key: 'watt', kind: 'metric', label: '实时功率', unit: 'W' },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已断电' }
      return { active: true, text: `${s.watt} W` }
    },
  },

  waterHeater: {
    type: 'waterHeater',
    label: '热水器',
    tagline: '恒温 · 即热',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '卫生间',
    powerKey: 'power',
    state: { power: false, targetTemp: 55, currentTemp: 32 },
    capabilities: [
      { key: 'power', kind: 'toggle', label: '电源' },
      { key: 'targetTemp', kind: 'slider', label: '设定水温', min: 35, max: 75, step: 1, unit: '℃', needPower: true, summary: true },
      { key: 'currentTemp', kind: 'metric', label: '当前水温', unit: '℃' },
    ],
    status(s) {
      if (!s.power) return { active: false, text: '已关闭' }
      return { active: true, text: `设定 ${s.targetTemp}℃` }
    },
  },

  sensor: {
    type: 'sensor',
    label: '环境传感器',
    tagline: '温湿度 · 空气',
    accent: 'var(--brand)',
    onAccent: 'var(--on-brand)',
    defaultRoom: '客厅',
    powerKey: null,
    state: { temp: 24, humidity: 55, pm25: 18 },
    capabilities: [
      { key: 'temp', kind: 'metric', label: '温度', unit: '℃' },
      { key: 'humidity', kind: 'metric', label: '湿度', unit: '%' },
      { key: 'pm25', kind: 'metric', label: 'PM2.5', unit: 'μg' },
    ],
    status(s) {
      return { active: true, text: `${s.temp}℃ · ${s.humidity}%` }
    },
  },
}

/** @brief 分类列表 (供添加/筛选使用) */
export const categoryList = Object.values(catalog)

/** @brief 房间预设 */
export const roomPresets = ['客厅', '主卧', '次卧', '书房', '厨房', '卫生间', '玄关', '阳台', '餐厅', '入户门']

/**
 * @brief 取得分类定义, 不存在时回退到灯光
 */
export function getCategory(type) {
  return catalog[type] || catalog.light
}

/**
 * @brief 深拷贝某分类的默认状态
 */
export function defaultStateFor(type) {
  return JSON.parse(JSON.stringify(getCategory(type).state))
}
