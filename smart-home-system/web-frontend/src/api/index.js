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
export const deviceApi = {
  // 获取设备列表
  getDevices() {
    return api.get('/devices')
  },
  // 获取设备状态
  getDeviceStatus(deviceId) {
    return api.get(`/devices/${deviceId}/status`)
  },
  // 控制设备
  controlDevice(deviceId, command) {
    return api.post(`/devices/${deviceId}/control`, command)
  }
}

// 健康检查
export const healthApi = {
  check() {
    return api.get('/health')
  }
}

export default api
