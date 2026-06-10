<script setup>
import { ref, watch, computed } from 'vue'
import { Refresh, Back, Check, Connection } from '@element-plus/icons-vue'
import { useDeviceStore } from '../stores/devices'
import { getCategory, roomPresets } from '../data/catalog'
import { usePairing } from '../composables/usePairing'
import DeviceIcon from './DeviceIcon.vue'

const store = useDeviceStore()
const { pairingOpen, closePairing } = usePairing()

const step = ref('scan') // scan | configure | connecting | done
const selected = ref(null)
const form = ref({ name: '', room: '' })
const progress = ref(0)
const lastAdded = ref(null)

const signalBars = { strong: 3, good: 2, weak: 1 }

const discovered = computed(() => store.discovered)
const scanning = computed(() => store.scanning)

function reset() {
  step.value = 'scan'
  selected.value = null
  progress.value = 0
  lastAdded.value = null
  store.startScan()
}

watch(pairingOpen, (open) => {
  if (open) reset()
  else store.stopScan()
})

function pick(item) {
  selected.value = item
  const cat = getCategory(item.type)
  form.value = { name: cat.label, room: cat.defaultRoom }
  step.value = 'configure'
}

function backToScan() {
  selected.value = null
  step.value = 'scan'
  if (!discovered.value.length) store.startScan()
}

function startPairing() {
  step.value = 'connecting'
  progress.value = 0
  const iv = setInterval(() => {
    progress.value += Math.random() * 16 + 6
    if (progress.value >= 100) {
      progress.value = 100
      clearInterval(iv)
      const dev = store.confirmPair({
        tempId: selected.value.tempId,
        name: form.value.name.trim() || getCategory(selected.value.type).label,
        room: form.value.room.trim() || getCategory(selected.value.type).defaultRoom,
      })
      lastAdded.value = dev
      setTimeout(() => (step.value = 'done'), 350)
    }
  }, 220)
}

function addAnother() {
  reset()
}

function finish() {
  closePairing()
}

const selectedCat = computed(() => (selected.value ? getCategory(selected.value.type) : null))
</script>

<template>
  <el-dialog
    v-model="pairingOpen"
    width="520"
    top="10vh"
    :close-on-click-modal="false"
    class="pair-dialog"
    @closed="store.stopScan()"
  >
    <template #header>
      <div class="ph">
        <el-icon :size="18"><Connection /></el-icon>
        <span>设备配对向导</span>
      </div>
    </template>

    <!-- 步骤指示 -->
    <div class="steps">
      <span class="step-dot" :class="{ on: ['scan'].includes(step), done: step !== 'scan' }">1</span>
      <span class="step-line" :class="{ done: step !== 'scan' }" />
      <span class="step-dot" :class="{ on: step === 'configure', done: ['connecting', 'done'].includes(step) }">2</span>
      <span class="step-line" :class="{ done: ['connecting', 'done'].includes(step) }" />
      <span class="step-dot" :class="{ on: ['connecting', 'done'].includes(step) }">3</span>
    </div>
    <div class="step-labels">
      <span>发现设备</span><span>命名分配</span><span>完成连接</span>
    </div>

    <!-- 步骤一: 扫描 -->
    <div v-if="step === 'scan'" class="scan">
      <div class="radar" :class="{ active: scanning }">
        <span class="ring r1" /><span class="ring r2" /><span class="ring r3" />
        <span class="radar-core"><el-icon :size="20"><Connection /></el-icon></span>
        <span v-if="scanning" class="sweep" />
      </div>
      <p class="scan-tip">
        {{ scanning ? '正在搜索附近的智能设备…' : `搜索完成，发现 ${discovered.length} 台设备` }}
      </p>

      <transition-group name="fade" tag="div" class="found-list">
        <button
          v-for="item in discovered"
          :key="item.tempId"
          class="found"
          :style="{ '--accent': getCategory(item.type).accent, '--on-accent': getCategory(item.type).onAccent }"
          @click="pick(item)"
        >
          <span class="found-icon"><DeviceIcon :type="item.type" :size="20" /></span>
          <span class="found-info">
            <span class="found-model">{{ item.model }}</span>
            <span class="found-type">{{ getCategory(item.type).label }}</span>
          </span>
          <span class="signal">
            <i v-for="n in 3" :key="n" :class="{ lit: n <= signalBars[item.signal] }" />
          </span>
        </button>
      </transition-group>

      <el-button :icon="Refresh" :loading="scanning" class="rescan" @click="store.startScan()">
        {{ scanning ? '搜索中' : '重新扫描' }}
      </el-button>
    </div>

    <!-- 步骤二: 配置 -->
    <div v-else-if="step === 'configure'" class="configure">
      <div class="sel-card" :style="{ '--accent': selectedCat.accent, '--on-accent': selectedCat.onAccent }">
        <span class="sel-icon"><DeviceIcon :type="selected.type" :size="26" /></span>
        <div>
          <p class="sel-model">{{ selected.model }}</p>
          <p class="sel-type">{{ selectedCat.label }} · {{ selectedCat.tagline }}</p>
        </div>
      </div>

      <el-form label-position="top" class="cfg-form">
        <el-form-item label="设备名称">
          <el-input v-model="form.name" maxlength="20" placeholder="给设备起个名字" />
        </el-form-item>
        <el-form-item label="所在房间">
          <el-select v-model="form.room" placeholder="选择或输入房间" filterable allow-create style="width: 100%">
            <el-option v-for="r in roomPresets" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="cfg-actions">
        <el-button :icon="Back" @click="backToScan">返回</el-button>
        <el-button type="primary" :icon="Connection" @click="startPairing">开始配对</el-button>
      </div>
    </div>

    <!-- 步骤三: 连接中 -->
    <div v-else-if="step === 'connecting'" class="connecting">
      <div class="conn-icon" :style="{ '--accent': selectedCat.accent, '--on-accent': selectedCat.onAccent }">
        <DeviceIcon :type="selected.type" :size="34" />
      </div>
      <p class="conn-title">正在与「{{ form.name }}」建立连接</p>
      <el-progress :percentage="Math.min(100, Math.round(progress))" :stroke-width="8" :show-text="false" />
      <p class="conn-sub">正在握手、同步设备影子状态…</p>
    </div>

    <!-- 步骤四: 完成 -->
    <div v-else class="done">
      <div class="done-badge"><el-icon :size="34"><Check /></el-icon></div>
      <h3>配对成功</h3>
      <p class="done-sub">「{{ lastAdded?.name }}」已加入 {{ lastAdded?.room }}，并显示在总控面板。</p>
      <div class="done-actions">
        <el-button @click="addAnother">继续添加</el-button>
        <el-button type="primary" @click="finish">完成</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.ph {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 650;
  font-size: 16px;
}

/* 步骤指示 */
.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 4px 0 6px;
}
.step-dot {
  box-sizing: border-box;
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
  background: var(--surface-2);
  color: var(--text-faint);
  border: 2px solid var(--border);
  transition: background 0.25s ease, color 0.25s ease, border-color 0.25s ease;
}
.step-dot.on {
  background: var(--brand);
  color: var(--on-brand);
  border-color: var(--brand);
}
.step-dot.done {
  background: var(--p4-yellow);
  color: #111;
  border-color: var(--ink);
}
.step-line {
  width: 48px;
  height: 2px;
  background: var(--border);
  transition: background 0.25s ease;
}
.step-line.done {
  background: var(--brand);
}
.step-labels {
  display: flex;
  justify-content: center;
  gap: 38px;
  font-size: 11.5px;
  color: var(--text-faint);
  margin-bottom: 18px;
}

/* 扫描 */
.scan { text-align: center; }
.radar {
  position: relative;
  width: 116px;
  height: 116px;
  margin: 6px auto 14px;
  display: grid;
  place-items: center;
}
.ring {
  position: absolute;
  border: 1.5px solid var(--border-strong);
  border-radius: 50%;
  inset: 0;
}
.r2 { inset: 18px; }
.r3 { inset: 36px; }
.radar-core {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--brand-grad);
  color: var(--p4-yellow);
  border: 2px solid var(--ink);
  display: grid;
  place-items: center;
  z-index: 2;
}
.sweep {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  overflow: hidden;
  /* 雷达波束: 带亮边的扇形扫掠 */
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    color-mix(in srgb, var(--p4-yellow) 10%, transparent) 38deg,
    color-mix(in srgb, var(--p4-yellow-deep) 55%, transparent) 68deg,
    var(--p4-yellow-deep) 72deg,
    transparent 72.5deg
  );
  animation: spin 1.6s linear infinite;
}
.radar.active .ring {
  animation: pulse 1.8s ease-out infinite;
}
.r2 { animation-delay: 0.3s; }
.r3 { animation-delay: 0.6s; }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse {
  0% { opacity: 0.7; }
  100% { opacity: 0.2; }
}
.scan-tip {
  font-size: 13.5px;
  color: var(--text-soft);
  margin-bottom: 14px;
}

.found-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  max-height: 230px;
  overflow-y: auto;
}
.found {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  cursor: pointer;
  text-align: left;
  transition: all 0.18s ease;
}
.found:hover {
  border-color: var(--accent);
  transform: translateX(2px);
}
.found-icon {
  width: 38px;
  height: 38px;
  border-radius: var(--r-sm);
  display: grid;
  place-items: center;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 15%, transparent);
}
.found-info { flex: 1; display: flex; flex-direction: column; }
.found-model { font-weight: 600; font-size: 14px; color: var(--text); }
.found-type { font-size: 12px; color: var(--text-faint); }
.signal { display: flex; align-items: flex-end; gap: 3px; height: 16px; }
.signal i {
  width: 4px;
  background: var(--border-strong);
}
.signal i:nth-child(1) { height: 6px; }
.signal i:nth-child(2) { height: 11px; }
.signal i:nth-child(3) { height: 16px; }
.signal i.lit { background: var(--accent); }
.rescan { width: 100%; }

/* 配置 */
.sel-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  margin-bottom: 18px;
}
.sel-icon {
  width: 52px;
  height: 52px;
  border-radius: var(--r-md);
  display: grid;
  place-items: center;
  color: var(--on-accent, var(--on-brand));
  background: var(--accent);
}
.sel-model { font-weight: 650; font-size: 15px; }
.sel-type { font-size: 12.5px; color: var(--text-faint); margin-top: 2px; }
.cfg-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

/* 连接中 */
.connecting { text-align: center; padding: 12px 8px 4px; }
.conn-icon {
  width: 74px;
  height: 74px;
  border-radius: 50%;
  margin: 0 auto 18px;
  display: grid;
  place-items: center;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 16%, transparent);
  animation: breathe 1.2s ease-in-out infinite;
}
@keyframes breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}
.conn-title { font-weight: 600; margin-bottom: 18px; }
.conn-sub { font-size: 12.5px; color: var(--text-faint); margin-top: 12px; }

/* 完成 */
.done { text-align: center; padding: 14px 8px 6px; }
.done-badge {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 3px solid #fff;
  margin: 0 auto 18px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--p4-blue);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--p4-blue) 22%, transparent);
  animation: pop 0.4s cubic-bezier(0.2, 1.4, 0.4, 1);
}
@keyframes pop {
  0% { transform: scale(0.4); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
.done h3 { font-size: 20px; margin-bottom: 8px; }
.done-sub { color: var(--text-faint); margin-bottom: 22px; }
.done-actions { display: flex; justify-content: center; gap: 12px; }
</style>
