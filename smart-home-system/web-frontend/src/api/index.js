import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // TODO: 添加认证 token
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// 设备相关 API
// ⚠ 真实端点以 backend-core (proj/feature-cpp) 为准, 见 ./backend.js。
// 此处保留简易封装并已对齐契约: 状态为 /state, 命令为 /command {command, params}。
export const deviceApi = {
  // 获取设备列表 -> { devices: [{ device_id, device_type, description, connected }] }
  getDevices() {
    return api.get('/devices')
  },
  // 获取设备状态
  getDeviceStatus(deviceId) {
    return api.get(`/devices/${deviceId}/state`)
  },
  // 控制设备: body 必须为 { command, params }
  controlDevice(deviceId, command, params = {}) {
    return api.post(`/devices/${deviceId}/command`, { command, params })
  }
}

// 健康检查
export const healthApi = {
  check() {
    return api.get('/health')
  }
}

export default api
