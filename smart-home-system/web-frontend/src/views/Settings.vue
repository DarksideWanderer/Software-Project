<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTheme } from '../composables/useTheme'
import { useAIConfig } from '../composables/useAIConfig'
import { useDeviceStore } from '../stores/devices'

const { theme, set } = useTheme()
const { config } = useAIConfig()
const store = useDeviceStore()

const themes = [
  { value: 'light', label: '浅色', desc: '明亮留白' },
  { value: 'dark', label: '深色', desc: '科技质感' },
]

const conn = ref({
  apiBaseUrl: 'http://localhost:8000',
  mqttBroker: 'mqtt://localhost:1883',
  websocketUrl: 'ws://localhost:8000/ws',
})

const connecting = ref(false)
const sourceLabel = computed(() => (store.isLive ? '实时后端' : '本地演示'))

async function connectBackend() {
  if (store.isLive) return
  connecting.value = true
  const ok = await store.connectLive()
  connecting.value = false
  if (ok) ElMessage.success(`已连接实时后端，同步到 ${store.total} 台设备`)
  else ElMessage.error(store.live.error || '连接失败，请确认后端已启动')
}

function disconnectBackend() {
  store.disconnectLive()
  ElMessage.info('已切回本地演示数据')
}

function saveConn() {
  ElMessage.success('连接配置已保存')
}

const aiModes = [
  { value: 'backend', label: '后端 / ai-service' },
  { value: 'openai', label: 'OpenAI 兼容端点' },
]

async function resetDemo() {
  try {
    await ElMessageBox.confirm('将清空当前设备并恢复演示数据，确定继续吗？', '恢复演示数据', {
      confirmButtonText: '恢复',
      cancelButtonText: '取消',
      type: 'warning',
    })
    store.resetDemo()
    ElMessage.success('已恢复演示数据')
  } catch (e) {
    /* 取消 */
  }
}
</script>

<template>
  <div class="settings">
    <header class="head">
      <h1>设置</h1>
      <p>个性化你的中控体验</p>
    </header>

    <section class="panel glass">
      <h2 class="panel-title">数据源</h2>
      <p class="panel-note">
        本地演示模式数据保存在浏览器中；实时后端模式对接队友的 FastAPI 设备服务（当前支持灯光、空调、电视）。
      </p>
      <div class="source-row">
        <button class="source-card" :class="{ on: !store.isLive }" @click="disconnectBackend">
          <span class="src-title">本地演示</span>
          <span class="src-desc">内置模拟设备，离线可用</span>
        </button>
        <button
          class="source-card"
          :class="{ on: store.isLive }"
          :disabled="connecting"
          @click="connectBackend"
        >
          <span class="src-title">实时后端</span>
          <span class="src-desc">{{ connecting ? '连接中…' : '对接 DeviceHub 真实设备' }}</span>
        </button>
      </div>
      <div class="status-line">
        <span class="dot" :class="{ live: store.isLive }" />
        当前数据源：<b>{{ sourceLabel }}</b>
        <span v-if="store.live.error" class="err">· {{ store.live.error }}</span>
        <el-button v-if="store.isLive" link type="primary" @click="store.refreshLive()">刷新状态</el-button>
      </div>
    </section>

    <section class="panel glass">
      <div class="ai-head">
        <div>
          <h2 class="panel-title no-mb">AI 语义理解</h2>
          <p class="panel-note no-mb">
            开启后，语音/文本指令优先交给大模型解析（基于设备命令自省接地）；不可用时自动回退内置规则解析。
          </p>
        </div>
        <el-switch v-model="config.enabled" />
      </div>

      <div v-if="config.enabled" class="ai-form">
        <div class="seg">
          <button
            v-for="m in aiModes"
            :key="m.value"
            class="seg-btn"
            :class="{ on: config.mode === m.value }"
            @click="config.mode = m.value"
          >
            {{ m.label }}
          </button>
        </div>

        <el-form label-position="top" class="ai-fields">
          <el-form-item :label="config.mode === 'openai' ? '接口地址 (Chat Completions)' : 'NLU 接口地址（留空用默认 /api/v1/ai/voice-command）'">
            <el-input
              v-model="config.endpoint"
              :placeholder="config.mode === 'openai' ? 'https://api.openai.com/v1/chat/completions' : '/api/v1/ai/voice-command'"
            />
          </el-form-item>
          <template v-if="config.mode === 'openai'">
            <el-form-item label="模型">
              <el-input v-model="config.model" placeholder="gpt-4o-mini" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="config.apiKey" type="password" show-password placeholder="sk-..." />
            </el-form-item>
          </template>
        </el-form>
        <p class="ai-tip">
          提示：浏览器直连第三方模型需对方允许跨域（CORS）。生产建议走"后端 / ai-service"模式，由后端代理模型调用。
        </p>
      </div>
    </section>

    <section class="panel glass">
      <h2 class="panel-title">服务地址</h2>
      <el-form label-position="top" class="conn-form">
        <el-form-item label="API 服务地址">
          <el-input v-model="conn.apiBaseUrl" />
        </el-form-item>
        <el-form-item label="MQTT Broker">
          <el-input v-model="conn.mqttBroker" />
        </el-form-item>
        <el-form-item label="WebSocket 地址">
          <el-input v-model="conn.websocketUrl" />
        </el-form-item>
      </el-form>
      <el-button type="primary" round @click="saveConn">保存配置</el-button>
    </section>

    <section class="panel glass">
      <h2 class="panel-title">外观主题</h2>
      <div class="theme-row">
        <button
          v-for="t in themes"
          :key="t.value"
          class="theme-card"
          :class="[t.value, { on: theme === t.value }]"
          @click="set(t.value)"
        >
          <div class="preview">
            <span class="p-bar" />
            <span class="p-card" />
            <span class="p-card short" />
          </div>
          <div class="theme-meta">
            <span class="theme-label">{{ t.label }}</span>
            <span class="theme-desc">{{ t.desc }}</span>
          </div>
          <span class="radio" :class="{ on: theme === t.value }" />
        </button>
      </div>
    </section>

    <section class="panel glass">
      <h2 class="panel-title">数据管理</h2>
      <div class="data-row">
        <div>
          <p class="data-title">恢复演示数据</p>
          <p class="data-desc">重置为初始演示设备集合（仅本地模式）。</p>
        </div>
        <el-button round @click="resetDemo">恢复</el-button>
      </div>
    </section>

    <section class="panel glass">
      <h2 class="panel-title">关于</h2>
      <div class="info-row"><span>系统名称</span><b>全屋智能中控系统</b></div>
      <div class="info-row"><span>前端版本</span><b>v1.1.0</b></div>
      <div class="info-row"><span>技术栈</span><b>Vue 3 · Vite · Element Plus · Pinia</b></div>
    </section>
  </div>
</template>

<style scoped>
.settings { display: flex; flex-direction: column; gap: 20px; max-width: 760px; }
.head h1 { font-size: 28px; font-weight: 720; }
.head p { color: var(--text-faint); font-size: 14px; margin-top: 4px; }

.panel { padding: 24px 26px; border-radius: 22px; }
.panel-title { font-size: 15px; font-weight: 650; margin-bottom: 16px; color: var(--text-soft); }
.panel-title.no-mb { margin-bottom: 4px; }
.panel-note { font-size: 13px; color: var(--text-faint); margin-bottom: 18px; margin-top: -6px; }
.panel-note.no-mb { margin-bottom: 0; max-width: 460px; }

.source-row { display: flex; gap: 14px; flex-wrap: wrap; }
.source-card {
  flex: 1; min-width: 200px; text-align: left; padding: 16px 18px; border-radius: 14px;
  border: 1.5px solid var(--border); background: var(--surface-2); cursor: pointer;
  display: flex; flex-direction: column; gap: 4px; transition: all 0.2s ease;
}
.source-card:hover { border-color: var(--brand); }
.source-card.on { border-color: var(--brand); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 16%, transparent); }
.source-card:disabled { opacity: 0.6; cursor: wait; }
.src-title { font-weight: 650; font-size: 15px; }
.src-desc { font-size: 12.5px; color: var(--text-faint); }
.status-line { margin-top: 16px; font-size: 13px; color: var(--text-soft); display: flex; align-items: center; gap: 8px; }
.status-line .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-faint); }
.status-line .dot.live { background: var(--ok); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 25%, transparent); }
.status-line .err { color: var(--danger); }

.ai-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.ai-form { margin-top: 18px; }
.seg { display: flex; gap: 8px; margin-bottom: 16px; }
.seg-btn {
  padding: 9px 16px; border-radius: 11px; border: 1px solid var(--border);
  background: var(--surface-2); color: var(--text-soft); font-size: 13.5px; font-weight: 550;
  cursor: pointer; transition: all 0.18s ease;
}
.seg-btn:hover { color: var(--text); border-color: var(--brand); }
.seg-btn.on { color: #fff; background: var(--brand); border-color: var(--brand); }
.ai-tip { font-size: 12px; color: var(--text-faint); margin-top: 4px; }

.conn-form { margin-bottom: 6px; }

.theme-row { display: flex; gap: 16px; flex-wrap: wrap; }
.theme-card {
  flex: 1; min-width: 200px; display: flex; align-items: center; gap: 14px; padding: 16px;
  border-radius: 16px; border: 1.5px solid var(--border); background: var(--surface-2);
  cursor: pointer; transition: all 0.2s ease;
}
.theme-card:hover { border-color: var(--brand); }
.theme-card.on { border-color: var(--brand); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 18%, transparent); }
.preview { width: 64px; height: 48px; border-radius: 10px; padding: 8px; display: flex; flex-direction: column; gap: 4px; flex-shrink: 0; }
.theme-card.light .preview { background: #eef1f8; }
.theme-card.dark .preview { background: #0a0c16; }
.p-bar { height: 6px; border-radius: 3px; background: var(--brand); width: 70%; }
.p-card { height: 10px; border-radius: 4px; }
.theme-card.light .p-card { background: #ffffff; box-shadow: 0 1px 2px rgba(0,0,0,0.08); }
.theme-card.dark .p-card { background: rgba(255,255,255,0.12); }
.p-card.short { width: 60%; }
.theme-meta { flex: 1; display: flex; flex-direction: column; }
.theme-label { font-weight: 650; font-size: 15px; }
.theme-desc { font-size: 12.5px; color: var(--text-faint); }
.radio { width: 20px; height: 20px; border-radius: 50%; border: 2px solid var(--border-strong); flex-shrink: 0; transition: all 0.2s ease; }
.radio.on { border-color: var(--brand); background: var(--brand); box-shadow: inset 0 0 0 4px var(--surface-solid); }

.data-row { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.data-title { font-weight: 600; font-size: 14.5px; }
.data-desc { font-size: 12.5px; color: var(--text-faint); margin-top: 3px; }

.info-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
.info-row:last-child { border-bottom: none; }
.info-row span { color: var(--text-faint); }
.info-row b { font-weight: 600; }
</style>
