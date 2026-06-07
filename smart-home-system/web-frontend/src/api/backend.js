// 与队友后端 (FastAPI DeviceHub) 对接的真实接口封装。
// 端点契约 (proj/feature-cpp 分支):
//   GET  /api/v1/devices                      列出已注册设备
//   GET  /api/v1/devices/{id}/state           查询设备状态
//   POST /api/v1/devices/{id}/command         发送命令 {command, params}
//   GET  /api/v1/devices/{id}/commands/count  设备支持的命令清单
//   GET  /api/v1/devices/{id}/commands/{name} 单条命令的调用 schema
//   GET  /health                              健康检查
import api from './index'

/** @brief 健康检查 (注意 /health 在根路径, 不带 /api/v1 前缀) */
export function health() {
  return api.get('/health', { baseURL: '/' })
}

/** @brief 列出全部已注册设备 */
export function listDevices() {
  return api.get('/devices')
}

/** @brief 查询单个设备状态 */
export function getState(deviceId) {
  return api.get(`/devices/${deviceId}/state`)
}

/** @brief 发送命令到设备 */
export function sendCommand(deviceId, command, params = {}) {
  return api.post(`/devices/${deviceId}/command`, { command, params })
}

/** @brief 查询设备支持的命令清单 */
export function getCommandCount(deviceId) {
  return api.get(`/devices/${deviceId}/commands/count`)
}

/** @brief 查询某条命令的调用格式 (参数定义) */
export function getCommandSchema(deviceId, commandName) {
  return api.get(`/devices/${deviceId}/commands/${commandName}`)
}

export default {
  health,
  listDevices,
  getState,
  sendCommand,
  getCommandCount,
  getCommandSchema,
}
