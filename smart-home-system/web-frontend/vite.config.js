import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 业务后端 backend-core (FastAPI DeviceHub)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // AI 服务 ai-service (ASR / NLU), 默认端口 8100, 端点无 /api/v1 前缀
      '/ai': {
        target: 'http://localhost:8100',
        changeOrigin: true,
      },
      // 后端健康检查在根路径 /health (不带 /api/v1 前缀), 实时模式连接前会先探活
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    }
  }
})
