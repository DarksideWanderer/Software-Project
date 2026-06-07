import { defineStore } from 'pinia'
import { catalog, getCategory, defaultStateFor } from '../data/catalog'
import backend from '../api/backend'
import {
  typeFromBackend,
  stateFromBackend,
  commandsFromPatch,
  patchFromCommand,
} from '../utils/deviceMapping'

const STORAGE_KEY = 'shs.devices.v1'

function uid() {
  return 'dev_' + Math.random().toString(36).slice(2, 8) + Date.now().toString(36).slice(-3)
}

function loadDevices() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch (e) {
    console.warn('读取本地设备失败', e)
  }
  return null
}

function seedDevices() {
  const make = (type, name, room, patch = {}) => ({
    id: uid(),
    type,
    name,
    room,
    online: true,
    favorite: false,
    addedAt: Date.now(),
    state: { ...defaultStateFor(type), ...patch },
  })
  return [
    make('light', '客厅主灯', '客厅', { power: true, brightness: 75 }),
    make('light', '餐厅吊灯', '餐厅', { power: false }),
    make('ac', '客厅空调', '客厅', { power: true, targetTemp: 25, mode: 'cool' }),
    make('curtain', '客厅窗帘', '客厅', { position: 70 }),
    make('tv', '客厅电视', '客厅', { power: true, volume: 18 }),
    make('purifier', '卧室净化器', '主卧', { power: true, pm25: 14 }),
    make('lock', '入户门锁', '入户门', { locked: true }),
    make('sensor', '客厅环境', '客厅', { temp: 24, humidity: 52 }),
  ]
}

const DISCOVERY_POOL = [
  { type: 'light', model: 'LumiGlow 灯带', signal: 'strong' },
  { type: 'light', model: 'AuraBulb 球泡灯', signal: 'good' },
  { type: 'ac', model: 'ArcticPro 变频空调', signal: 'good' },
  { type: 'curtain', model: 'SlideMotion 电机', signal: 'weak' },
  { type: 'tv', model: 'VistaScreen 4K', signal: 'strong' },
  { type: 'fan', model: 'BreezeMax 塔扇', signal: 'good' },
  { type: 'purifier', model: 'PureFlow P3', signal: 'good' },
  { type: 'vacuum', model: 'RoboSweep S5', signal: 'weak' },
  { type: 'lock', model: 'GuardLock Pro', signal: 'strong' },
  { type: 'camera', model: 'SentryCam 2K', signal: 'good' },
  { type: 'plug', model: 'PowerDot 插座', signal: 'strong' },
  { type: 'waterHeater', model: 'AquaHeat 即热', signal: 'weak' },
  { type: 'sensor', model: 'EnviSense 多合一', signal: 'good' },
]

export const useDeviceStore = defineStore('devices', {
  state: () => ({
    devices: loadDevices() || seedDevices(),
    scanning: false,
    discovered: [],
    source: 'local',
    live: { connected: false, error: '', lastSync: 0 },
    _localBackup: null,
  }),

  getters: {
    total: (s) => s.devices.length,
    onlineCount: (s) => s.devices.filter((d) => d.online).length,
    activeCount: (s) =>
      s.devices.filter((d) => getCategory(d.type).status(d.state).active).length,
    isLive: (s) => s.source === 'live',
    rooms: (s) => {
      const set = new Set(s.devices.map((d) => d.room))
      return Array.from(set)
    },
    byRoom: (s) => {
      const groups = {}
      for (const d of s.devices) {
        ;(groups[d.room] = groups[d.room] || []).push(d)
      }
      return groups
    },
    getById: (s) => (id) => s.devices.find((d) => d.id === id),
  },

  actions: {
    persist() {
      if (this.source === 'live') return
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.devices))
      } catch (e) {
        console.warn('保存设备失败', e)
      }
    },

    patchState(id, patch) {
      const d = this.getById(id)
      if (!d) return
      d.state = { ...d.state, ...patch }
      if (this.source === 'live' && d._live) {
        this._dispatchLive(d, patch)
      } else {
        this.persist()
      }
    },

    async _dispatchLive(device, patch) {
      const cmds = commandsFromPatch(patch, device._commands)
      for (const c of cmds) {
        try {
          const resp = await backend.sendCommand(device.id, c.command, c.params)
          if (resp && resp.state) {
            device.state = { ...device.state, ...stateFromBackend(device.type, resp.state) }
          }
          this.live.error = ''
        } catch (e) {
          this.live.error = '命令下发失败: ' + (e && e.message ? e.message : e)
        }
      }
    },

    toggleQuick(id) {
      const d = this.getById(id)
      if (!d) return
      const cat = getCategory(d.type)
      if (cat.powerKey) {
        this.patchState(id, { [cat.powerKey]: !d.state[cat.powerKey] })
      } else if (d.type === 'curtain') {
        this.patchState(id, { position: d.state.position > 0 ? 0 : 100 })
      } else if (d.type === 'lock') {
        this.patchState(id, { locked: !d.state.locked })
      } else if (d.type === 'vacuum') {
        const running = !d.state.running
        this.patchState(id, { running, action: running ? 'clean' : 'idle' })
      }
    },

    renameDevice(id, name, room) {
      const d = this.getById(id)
      if (!d) return
      if (name) d.name = name
      if (room) d.room = room
      this.persist()
    },

    toggleFavorite(id) {
      const d = this.getById(id)
      if (!d) return
      d.favorite = !d.favorite
      this.persist()
    },

    setOnline(id, online) {
      const d = this.getById(id)
      if (!d) return
      d.online = online
      this.persist()
    },

    removeDevice(id) {
      this.devices = this.devices.filter((d) => d.id !== id)
      this.persist()
    },

    addDevice({ type, name, room }) {
      const cat = getCategory(type)
      const device = {
        id: uid(),
        type,
        name: name || cat.label,
        room: room || cat.defaultRoom,
        online: true,
        favorite: false,
        addedAt: Date.now(),
        state: defaultStateFor(type),
      }
      this.devices.push(device)
      this.persist()
      return device
    },

    startScan() {
      this.scanning = true
      this.discovered = []
      const shuffled = [...DISCOVERY_POOL].sort(() => Math.random() - 0.5)
      const picks = shuffled.slice(0, 5 + Math.floor(Math.random() * 3))
      picks.forEach((item, i) => {
        setTimeout(() => {
          if (!this.scanning) return
          this.discovered.push({
            tempId: 'scan_' + i + '_' + Date.now(),
            type: item.type,
            model: item.model,
            signal: item.signal,
          })
        }, 500 + i * 650)
      })
      setTimeout(() => {
        this.scanning = false
      }, 600 + picks.length * 650)
    },

    stopScan() {
      this.scanning = false
    },

    confirmPair({ tempId, name, room }) {
      const found = this.discovered.find((x) => x.tempId === tempId)
      if (!found) return null
      const device = this.addDevice({ type: found.type, name, room })
      this.discovered = this.discovered.filter((x) => x.tempId !== tempId)
      return device
    },

    async connectLive() {
      try {
        await backend.health()
      } catch (e) {
        this.live = { connected: false, error: '无法连接后端服务', lastSync: 0 }
        return false
      }
      try {
        const res = await backend.listDevices()
        const list = (res && res.devices) || []
        if (this.source === 'local') this._localBackup = this.devices
        const built = []
        for (const item of list) {
          const type = typeFromBackend(item.device_type)
          let raw = {}
          let commands = []
          try {
            const st = await backend.getState(item.device_id)
            raw = (st && st.state) || st || {}
          } catch (e) {
            /* 状态拉取失败时用默认值 */
          }
          try {
            const cc = await backend.getCommandCount(item.device_id)
            commands = (cc && cc.commands) || []
          } catch (e) {
            /* 命令清单可选 */
          }
          built.push({
            id: item.device_id,
            type,
            name: item.description || getCategory(type).label,
            room: getCategory(type).defaultRoom,
            online: item.connected !== false,
            favorite: false,
            addedAt: Date.now(),
            state: stateFromBackend(type, raw),
            _live: true,
            _commands: commands,
            _backendType: item.device_type,
          })
        }
        this.devices = built
        this.source = 'live'
        this.live = { connected: true, error: '', lastSync: Date.now() }
        return true
      } catch (e) {
        this.live = { connected: false, error: '拉取设备失败', lastSync: 0 }
        return false
      }
    },

    async refreshLive() {
      if (this.source !== 'live') return
      for (const d of this.devices) {
        try {
          const st = await backend.getState(d.id)
          const raw = (st && st.state) || st || {}
          d.state = { ...d.state, ...stateFromBackend(d.type, raw) }
        } catch (e) {
          /* 单设备失败忽略 */
        }
      }
      this.live.lastSync = Date.now()
    },

    disconnectLive() {
      this.source = 'local'
      this.live = { connected: false, error: '', lastSync: 0 }
      if (this._localBackup) {
        this.devices = this._localBackup
        this._localBackup = null
      } else {
        this.devices = loadDevices() || seedDevices()
      }
    },

    async applyAICommand(deviceId, command, params = {}) {
      const d = this.getById(deviceId)
      if (!d) return { ok: false, error: '设备不存在' }
      if (this.source === 'live' && d._live) {
        try {
          const resp = await backend.sendCommand(deviceId, command, params)
          if (resp && resp.state) {
            d.state = { ...d.state, ...stateFromBackend(d.type, resp.state) }
          }
          return { ok: resp ? resp.success !== false : true }
        } catch (e) {
          return { ok: false, error: e && e.message ? e.message : String(e) }
        }
      }
      const patch = patchFromCommand(command, params)
      if (Object.keys(patch).length) this.patchState(deviceId, patch)
      return { ok: true }
    },

    runScene(key) {
      let count = 0
      const set = (id, patch) => {
        this.patchState(id, patch)
        count++
      }
      for (const d of this.devices) {
        const cat = getCategory(d.type)
        if (key === 'allOff') {
          if (cat.powerKey) set(d.id, { [cat.powerKey]: false })
          if (d.type === 'curtain') set(d.id, { position: 0 })
        }
        if (key === 'home') {
          if (d.type === 'light' && d.room === '客厅') set(d.id, { power: true })
          if (d.type === 'ac' && d.room === '客厅') set(d.id, { power: true })
          if (d.type === 'curtain') set(d.id, { position: 100 })
          if (d.type === 'lock') set(d.id, { locked: false })
        }
        if (key === 'away') {
          if (cat.powerKey) set(d.id, { [cat.powerKey]: false })
          if (d.type === 'lock') set(d.id, { locked: true })
          if (d.type === 'curtain') set(d.id, { position: 0 })
          if (d.type === 'camera') set(d.id, { power: true, recording: true })
        }
        if (key === 'night') {
          if (d.type === 'light') set(d.id, { power: false })
          if (d.type === 'tv') set(d.id, { power: false })
          if (d.type === 'curtain') set(d.id, { position: 0 })
          if (d.type === 'lock') set(d.id, { locked: true })
        }
      }
      return count
    },

    simulateTick() {
      if (this.source === 'live') return
      let changed = false
      for (const d of this.devices) {
        const s = d.state
        if (d.type === 'ac' && s.power) {
          const target = s.targetTemp
          if (Math.abs(s.currentTemp - target) > 0.4) {
            s.currentTemp += s.currentTemp > target ? -0.3 : 0.3
            s.currentTemp = Math.round(s.currentTemp * 10) / 10
            changed = true
          }
        }
        if (d.type === 'waterHeater' && s.power && s.currentTemp < s.targetTemp) {
          s.currentTemp = Math.min(s.targetTemp, s.currentTemp + 0.6)
          s.currentTemp = Math.round(s.currentTemp * 10) / 10
          changed = true
        }
        if ((d.type === 'purifier' || d.type === 'sensor') && 'pm25' in s) {
          const drift = Math.round((Math.random() - 0.5) * 3)
          s.pm25 = Math.max(2, Math.min(180, s.pm25 + drift))
          changed = true
        }
        if (d.type === 'sensor') {
          s.temp = Math.round((s.temp + (Math.random() - 0.5) * 0.3) * 10) / 10
          s.humidity = Math.max(20, Math.min(90, s.humidity + Math.round((Math.random() - 0.5) * 2)))
          changed = true
        }
        if (d.type === 'vacuum') {
          if (s.running && s.battery > 0) {
            s.battery = Math.max(0, s.battery - 1)
            changed = true
          } else if (s.action === 'dock' && s.battery < 100) {
            s.battery = Math.min(100, s.battery + 1)
            changed = true
          }
        }
        if (d.type === 'plug' && s.power) {
          s.watt = Math.max(0, s.watt + Math.round((Math.random() - 0.5) * 12))
          changed = true
        }
      }
      if (changed) this.persist()
    },

    resetDemo() {
      this.devices = seedDevices()
      this.persist()
    },
  },
})
