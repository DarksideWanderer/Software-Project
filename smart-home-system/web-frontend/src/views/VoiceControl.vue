<script setup>
import { ref, computed } from 'vue'
import { Microphone, Check, Warning, Promotion, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useDeviceStore } from '../stores/devices'
import { useSpeech } from '../composables/useSpeech'
import { useAIConfig } from '../composables/useAIConfig'
import { parseCommand, EXAMPLE_COMMANDS } from '../utils/nlu'
import { parseWithAI } from '../api/aiCommand'

const store = useDeviceStore()
const { supported, listening, interim, start, stop } = useSpeech()
const { config } = useAIConfig()

const manualText = ref('')
const lastResult = ref(null)
const history = ref([])
const busy = ref(false)

const engineLabel = computed(() => (config.enabled ? 'AI 语义理解' : '内置规则解析'))

const orbHint = computed(() => {
  if (listening.value) return interim.value || '请说出指令…'
  if (busy.value) return '正在理解指令…'
  if (lastResult.value) return lastResult.value.text
  return supported ? '点击麦克风开始说话' : '点击下方文本框输入指令'
})

function fmtTime(d) {
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function record(text, ok, summary, engine) {
  const result = { ok, text, summary, engine }
  lastResult.value = result
  history.value.unshift({ ...result, time: new Date() })
  if (history.value.length > 12) history.value.pop()
  ok ? ElMessage.success(summary) : ElMessage.warning(summary)
}

function applyRulePlan(plan) {
  if (plan.action === 'scene') store.runScene(plan.scene)
  else (plan.targets || []).forEach((tg) => store.patchState(tg.id, tg.patch))
}

function runRule(text, engine) {
  const rp = parseCommand(text, store.devices)
  if (rp.ok) {
    applyRulePlan(rp)
    record(text, true, rp.summary, engine)
  } else {
    record(text, false, rp.hint, engine)
  }
}

async function execute(text) {
  const t = (text || '').trim()
  if (!t || busy.value) return

  if (config.enabled) {
    busy.value = true
    try {
      const plan = await parseWithAI(t, store.devices, config)
      if (plan.actions.length) {
        for (const a of plan.actions) {
          await store.applyAICommand(a.deviceId, a.command, a.params)
        }
        const names = plan.actions
          .map((a) => store.getById(a.deviceId)?.name)
          .filter(Boolean)
          .join('、')
        record(t, true, plan.reply || `已执行：${names}`, 'AI')
        busy.value = false
        return
      }
      // 无 actions 但 AI 已给出回复 (澄清/天气/提醒/场景): 直接展示, 不回退规则
      if (plan.handled && plan.reply) {
        record(t, !plan.needClarification, plan.reply, 'AI')
        busy.value = false
        return
      }
      runRule(t, '规则 (AI 未匹配)')
    } catch (e) {
      runRule(t, '规则 (AI 回退)')
    } finally {
      busy.value = false
    }
    return
  }

  runRule(t, '规则')
}

function onMic() {
  if (!supported) {
    ElMessage.info('当前浏览器不支持语音识别，请使用下方文本输入（建议 Chrome / Edge）')
    return
  }
  if (listening.value) stop()
  else start(execute)
}

function submitManual() {
  if (!manualText.value.trim()) return
  execute(manualText.value)
  manualText.value = ''
}

function runExample(cmd) {
  execute(cmd)
}
</script>

<template>
  <div class="voice">
    <header class="head">
      <div>
        <h1>语音控制</h1>
        <p>说出指令，自动识别并执行对应的家电操作</p>
      </div>
      <span class="engine-badge" :class="{ ai: config.enabled }">
        <span class="ed" /> {{ engineLabel }}
      </span>
    </header>

    <section class="stage glass">
      <button class="orb" :class="{ listening, busy }" @click="onMic" :title="listening ? '停止' : '开始'">
        <span class="ring r1" /><span class="ring r2" /><span class="ring r3" />
        <span class="orb-core">
          <el-icon :size="40"><Microphone /></el-icon>
        </span>
        <span v-if="listening" class="eq">
          <i v-for="n in 5" :key="n" />
        </span>
      </button>

      <p class="orb-status" :class="{ live: listening || busy }">{{ orbHint }}</p>

      <transition name="fade">
        <div v-if="lastResult" class="result" :class="lastResult.ok ? 'ok' : 'fail'">
          <el-icon :size="18"><component :is="lastResult.ok ? Check : Warning" /></el-icon>
          <span>{{ lastResult.summary }}</span>
          <span class="result-engine">{{ lastResult.engine }}</span>
        </div>
      </transition>

      <p v-if="!supported" class="unsupported">
        当前浏览器未提供语音识别能力，可直接使用下方文本输入框模拟语音指令。
      </p>

      <div class="manual">
        <el-input
          v-model="manualText"
          size="large"
          placeholder="或输入指令，例如：把客厅空调调到26度"
          @keyup.enter="submitManual"
        >
          <template #prefix><el-icon><MagicStick /></el-icon></template>
        </el-input>
        <el-button type="primary" size="large" :icon="Promotion" :loading="busy" @click="submitManual">执行</el-button>
      </div>
    </section>

    <section class="examples">
      <h2 class="block-title">试试这些指令</h2>
      <div class="chips">
        <button v-for="c in EXAMPLE_COMMANDS" :key="c" class="ex-chip" @click="runExample(c)">
          {{ c }}
        </button>
      </div>
    </section>

    <section v-if="history.length" class="history glass">
      <h2 class="block-title">指令记录</h2>
      <ul class="hist-list">
        <li v-for="(h, i) in history" :key="i" class="hist">
          <span class="hist-dot" :class="h.ok ? 'ok' : 'fail'">
            <el-icon :size="13"><component :is="h.ok ? Check : Warning" /></el-icon>
          </span>
          <div class="hist-body">
            <span class="hist-text">“{{ h.text }}”</span>
            <span class="hist-sum">{{ h.summary }}</span>
          </div>
          <span class="hist-engine">{{ h.engine }}</span>
          <span class="hist-time">{{ fmtTime(h.time) }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.voice { display: flex; flex-direction: column; gap: 24px; }
.head { display: flex; justify-content: space-between; align-items: flex-start; }
.head h1 { font-size: 28px; font-weight: 720; }
.head p { color: var(--text-faint); font-size: 14px; margin-top: 4px; }
.engine-badge {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 7px 14px; border-radius: 11px;
  font-size: 12.5px; font-weight: 600;
  color: var(--text-soft); background: var(--surface-2); border: 1px solid var(--border);
}
.engine-badge.ai { color: var(--brand); border-color: color-mix(in srgb, var(--brand) 40%, transparent); }
.engine-badge .ed { width: 7px; height: 7px; border-radius: 50%; background: var(--text-faint); }
.engine-badge.ai .ed { background: var(--brand); box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 22%, transparent); }

.stage { border-radius: 24px; padding: 40px 32px 30px; display: flex; flex-direction: column; align-items: center; gap: 22px; }

.orb { position: relative; width: 150px; height: 150px; border: none; background: transparent; cursor: pointer; display: grid; place-items: center; }
.orb-core {
  position: relative; z-index: 3; width: 104px; height: 104px; border-radius: 50%;
  background: var(--brand-grad); color: #fff; display: grid; place-items: center;
  box-shadow: 0 14px 38px rgba(91, 108, 255, 0.45); transition: transform 0.2s ease;
}
.orb:hover .orb-core { transform: scale(1.05); }
.orb.listening .orb-core, .orb.busy .orb-core { animation: corePulse 1.1s ease-in-out infinite; }
@keyframes corePulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.08); } }
.ring { position: absolute; border-radius: 50%; inset: 0; border: 1.5px solid color-mix(in srgb, var(--brand) 40%, transparent); opacity: 0; }
.orb.listening .ring { animation: ripple 1.8s ease-out infinite; }
.orb.listening .r2 { animation-delay: 0.45s; }
.orb.listening .r3 { animation-delay: 0.9s; }
@keyframes ripple { 0% { transform: scale(0.7); opacity: 0.8; } 100% { transform: scale(1.25); opacity: 0; } }
.eq { position: absolute; z-index: 4; bottom: 30px; display: flex; align-items: flex-end; gap: 3px; height: 22px; }
.eq i { width: 4px; border-radius: 2px; background: rgba(255, 255, 255, 0.9); animation: bounce 0.9s ease-in-out infinite; }
.eq i:nth-child(1) { animation-delay: 0s; }
.eq i:nth-child(2) { animation-delay: 0.15s; }
.eq i:nth-child(3) { animation-delay: 0.3s; }
.eq i:nth-child(4) { animation-delay: 0.45s; }
.eq i:nth-child(5) { animation-delay: 0.6s; }
@keyframes bounce { 0%, 100% { height: 6px; } 50% { height: 20px; } }

.orb-status { font-size: 16px; color: var(--text-soft); text-align: center; min-height: 24px; max-width: 520px; font-weight: 500; }
.orb-status.live { color: var(--brand); }

.result { display: inline-flex; align-items: center; gap: 10px; padding: 10px 18px; border-radius: 12px; font-size: 14px; font-weight: 550; }
.result.ok { color: var(--ok); background: color-mix(in srgb, var(--ok) 14%, transparent); }
.result.fail { color: var(--warn); background: color-mix(in srgb, var(--warn) 14%, transparent); }
.result-engine { font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 7px; background: var(--surface-2); color: var(--text-faint); }

.unsupported { font-size: 12.5px; color: var(--text-faint); text-align: center; max-width: 440px; }

.manual { display: flex; gap: 10px; width: 100%; max-width: 560px; }
.manual .el-input { flex: 1; }

.block-title { font-size: 15px; font-weight: 650; color: var(--text-soft); margin-bottom: 14px; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; }
.ex-chip {
  padding: 9px 16px; border-radius: 11px; border: 1px solid var(--border);
  background: var(--surface-2); color: var(--text-soft); font-size: 13.5px; font-weight: 500;
  cursor: pointer; transition: all 0.18s ease;
}
.ex-chip:hover { color: var(--brand); border-color: var(--brand); transform: translateY(-2px); }

.history { border-radius: 22px; padding: 24px 26px; }
.hist-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.hist { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }
.hist:last-child { border-bottom: none; }
.hist-dot { width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; flex-shrink: 0; }
.hist-dot.ok { color: var(--ok); background: color-mix(in srgb, var(--ok) 16%, transparent); }
.hist-dot.fail { color: var(--warn); background: color-mix(in srgb, var(--warn) 16%, transparent); }
.hist-body { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.hist-text { font-size: 14px; font-weight: 550; }
.hist-sum { font-size: 12.5px; color: var(--text-faint); margin-top: 2px; }
.hist-engine { font-size: 11px; color: var(--text-faint); padding: 2px 8px; border-radius: 7px; background: var(--surface-2); white-space: nowrap; }
.hist-time { font-size: 12px; color: var(--text-faint); font-variant-numeric: tabular-nums; }

@media (max-width: 600px) {
  .manual { flex-direction: column; }
  .hist-engine { display: none; }
}
</style>
