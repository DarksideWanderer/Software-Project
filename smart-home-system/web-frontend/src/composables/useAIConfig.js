import { reactive, watch } from 'vue'

// AI 语义理解 (LLM NLU) 的可配置项, 持久化到 localStorage。
// 未启用或未配置端点时, 语音页会自动回退到内置规则解析。
const KEY = 'shs.ai.config'

const defaults = {
  enabled: false,
  // backend = 走队友的 ai-service / 后端 NLU 路由
  // openai  = 走任意 OpenAI 兼容的 /chat/completions 端点
  mode: 'backend',
  endpoint: '',
  model: 'gpt-4o-mini',
  apiKey: '',
}

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return { ...defaults, ...JSON.parse(raw) }
  } catch (e) {
    /* ignore */
  }
  return { ...defaults }
}

const config = reactive(load())

watch(
  config,
  (v) => {
    try {
      localStorage.setItem(KEY, JSON.stringify(v))
    } catch (e) {
      /* ignore */
    }
  },
  { deep: true },
)

export function useAIConfig() {
  return { config }
}
