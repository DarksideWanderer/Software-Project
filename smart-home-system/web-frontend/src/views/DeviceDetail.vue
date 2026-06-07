<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Star, StarFilled, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useDeviceStore } from '../stores/devices'
import { getCategory, roomPresets } from '../data/catalog'
import DeviceIcon from '../components/DeviceIcon.vue'

const route = useRoute()
const router = useRouter()
const store = useDeviceStore()

const device = computed(() => store.getById(route.params.id))
const cat = computed(() => (device.value ? getCategory(device.value.type) : null))
const status = computed(() => (device.value ? cat.value.status(device.value.state) : null))
const accent = computed(() => cat.value?.accent || 'var(--brand)')

// 是否断电(用于禁用从属控件)
const powered = computed(() => {
  if (!cat.value?.powerKey) return true
  return !!device.value.state[cat.value.powerKey]
})

// 主控开关配置(电源 / 开合 / 门锁 / 清扫)
const primary = computed(() => {
  if (!device.value) return null
  const t = device.value.type
  const s = device.value.state
  if (cat.value.powerKey) {
    return { label: '电源', on: !!s[cat.value.powerKey], toggle: () => store.patchState(device.value.id, { [cat.value.powerKey]: !s[cat.value.powerKey] }) }
  }
  if (t === 'curtain') {
    const on = s.position > 0
    return { label: on ? '已开启' : '已闭合', on, toggle: () => store.patchState(device.value.id, { position: on ? 0 : 100 }) }
  }
  if (t === 'lock') {
    return { label: s.locked ? '已上锁' : '已开锁', on: s.locked, toggle: () => store.patchState(device.value.id, { locked: !s.locked }) }
  }
  if (t === 'vacuum') {
    return { label: s.running ? '清扫中' : '待机', on: s.running, toggle: () => store.toggleQuick(device.value.id) }
  }
  return null
})

// 主视觉环形(取 summary 滑块容量)
const dial = computed(() => {
  if (!device.value) return null
  const c = cat.value.capabilities.find((x) => x.kind === 'slider' && x.summary)
  if (!c) return null
  const v = device.value.state[c.key]
  const pct = Math.round(((v - c.min) / (c.max - c.min)) * 100)
  return { value: v, unit: c.unit, pct: Math.max(0, Math.min(100, pct)), label: c.label }
})

// 可控容量(滑块/模式/开关-非主电源/动作)
const controls = computed(() => {
  if (!device.value) return []
  return cat.value.capabilities.filter((c) => {
    if (c.kind === 'metric') return false
    if (cat.value.powerKey && c.key === cat.value.powerKey) return false
    return true
  })
})

const metrics = computed(() =>
  device.value ? cat.value.capabilities.filter((c) => c.kind === 'metric') : [],
)

function setVal(key, val) {
  store.patchState(device.value.id, { [key]: val })
}
function runAction(action) {
  store.patchState(device.value.id, action.set)
  ElMessage.success(`已执行：${action.label}`)
}
function capDisabled(c) {
  return c.needPower && !powered.value
}

// 收藏 / 在线 / 重命名 / 删除
function toggleFav() {
  store.toggleFavorite(device.value.id)
}
const renaming = ref(false)
const form = ref({ name: '', room: '' })
function openRename() {
  form.value = { name: device.value.name, room: device.value.room }
  renaming.value = true
}
function saveRename() {
  store.renameDevice(device.value.id, form.value.name, form.value.room)
  renaming.value = false
  ElMessage.success('已更新')
}
async function remove() {
  try {
    await ElMessageBox.confirm(`确定要移除「${device.value.name}」吗？`, '移除设备', {
      confirmButtonText: '移除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    store.removeDevice(device.value.id)
    ElMessage.success('已移除')
    router.push('/')
  } catch (e) {
    /* 取消 */
  }
}

let timer = null
onMounted(() => {
  timer = setInterval(() => (store.isLive ? store.refreshLive() : store.simulateTick()), 3000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div v-if="device" class="detail" :style="{ '--accent': accent }">
    <!-- 顶部操作条 -->
    <div class="topline">
      <button class="back" @click="router.back()">
        <el-icon :size="18"><ArrowLeft /></el-icon> 返回
      </button>
      <div class="top-actions">
        <button class="ico" :class="{ fav: device.favorite }" @click="toggleFav" title="收藏">
          <el-icon :size="17"><component :is="device.favorite ? StarFilled : Star" /></el-icon>
        </button>
        <button class="ico" @click="openRename" title="重命名"><el-icon :size="17"><Edit /></el-icon></button>
        <button class="ico danger" @click="remove" title="移除"><el-icon :size="17"><Delete /></el-icon></button>
      </div>
    </div>

    <!-- 聚光主控卡 -->
    <section class="spotlight glass" :class="{ active: status.active }">
      <div class="spot-glow" />
      <div class="spot-main">
        <div class="spot-icon" :class="{ on: status.active }">
          <DeviceIcon :type="device.type" :size="40" :stroke="1.5" />
        </div>
        <div class="spot-info">
          <h1>{{ device.name }}</h1>
          <p class="spot-sub">{{ cat.label }} · {{ device.room }}</p>
          <div class="spot-tags">
            <span class="tag" :class="{ on: status.active }">{{ status.text }}</span>
            <span class="tag plain">
              <i class="dot" :class="{ online: device.online }" />
              {{ device.online ? '在线' : '离线' }}
            </span>
          </div>
        </div>

        <!-- 环形数值 -->
        <div v-if="dial" class="dial">
          <svg viewBox="0 0 120 120">
            <circle class="dial-bg" cx="60" cy="60" r="52" />
            <circle
              class="dial-fg"
              cx="60" cy="60" r="52"
              :stroke-dasharray="326.7"
              :stroke-dashoffset="326.7 * (1 - dial.pct / 100)"
            />
          </svg>
          <div class="dial-text">
            <span class="dial-val">{{ dial.value }}<i>{{ dial.unit }}</i></span>
            <span class="dial-label">{{ dial.label }}</span>
          </div>
        </div>
      </div>

      <!-- 主开关 -->
      <div v-if="primary" class="spot-power">
        <span class="power-label">{{ primary.label }}</span>
        <button class="big-switch" :class="{ on: primary.on }" :disabled="!device.online" @click="primary.toggle">
          <span class="bs-knob" />
        </button>
      </div>
    </section>

    <!-- 控制区 -->
    <section v-if="controls.length" class="panel glass">
      <h2 class="panel-title">控制</h2>
      <div class="ctrl-list">
        <div v-for="c in controls" :key="c.key" class="ctrl" :class="{ disabled: capDisabled(c) }">
          <!-- 开关 -->
          <template v-if="c.kind === 'toggle'">
            <div class="ctrl-head">
              <span class="ctrl-label">{{ c.label }}</span>
              <el-switch
                :model-value="device.state[c.key]"
                :disabled="capDisabled(c)"
                @update:model-value="(v) => setVal(c.key, v)"
              />
            </div>
            <span v-if="c.onLabel" class="ctrl-hint">{{ device.state[c.key] ? c.onLabel : c.offLabel }}</span>
          </template>

          <!-- 滑块 -->
          <template v-else-if="c.kind === 'slider'">
            <div class="ctrl-head">
              <span class="ctrl-label">{{ c.label }}</span>
              <span class="ctrl-value">{{ device.state[c.key] }}{{ c.unit }}</span>
            </div>
            <el-slider
              :model-value="device.state[c.key]"
              :min="c.min" :max="c.max" :step="c.step"
              :disabled="capDisabled(c)"
              @update:model-value="(v) => setVal(c.key, v)"
            />
          </template>

          <!-- 模式 -->
          <template v-else-if="c.kind === 'mode'">
            <span class="ctrl-label">{{ c.label }}</span>
            <div class="seg">
              <button
                v-for="o in c.options"
                :key="o.value"
                class="seg-btn"
                :class="{ on: device.state[c.key] === o.value }"
                :disabled="capDisabled(c)"
                @click="setVal(c.key, o.value)"
              >
                {{ o.label }}
              </button>
            </div>
          </template>

          <!-- 动作 -->
          <template v-else-if="c.kind === 'action'">
            <span class="ctrl-label">{{ c.label }}</span>
            <div class="seg actions">
              <button
                v-for="a in c.actions"
                :key="a.value"
                class="seg-btn"
                @click="runAction(a)"
              >
                {{ a.label }}
              </button>
            </div>
          </template>
        </div>
      </div>
    </section>

    <!-- 读数区 -->
    <section v-if="metrics.length" class="panel glass">
      <h2 class="panel-title">实时读数</h2>
      <div class="metric-grid">
        <div v-for="m in metrics" :key="m.key" class="metric">
          <span class="metric-label">{{ m.label }}</span>
          <span class="metric-val">{{ device.state[m.key] }}<i>{{ m.unit }}</i></span>
          <div
            v-if="['battery', 'filter', 'pm25', 'humidity'].includes(m.key)"
            class="metric-bar"
          >
            <span :style="{ width: (m.key === 'pm25' ? Math.min(100, device.state[m.key] / 1.5) : device.state[m.key]) + '%' }" />
          </div>
        </div>
      </div>
    </section>

    <!-- 设备信息 -->
    <section class="panel glass info">
      <h2 class="panel-title">设备信息</h2>
      <div class="info-row"><span>设备类型</span><b>{{ cat.label }}</b></div>
      <div class="info-row"><span>所在房间</span><b>{{ device.room }}</b></div>
      <div class="info-row"><span>设备 ID</span><b class="mono">{{ device.id }}</b></div>
      <div class="info-row"><span>连接状态</span>
        <el-switch
          :model-value="device.online"
          active-text="在线" inactive-text="离线"
          inline-prompt
          @update:model-value="(v) => store.setOnline(device.id, v)"
        />
      </div>
    </section>

    <!-- 重命名对话框 -->
    <el-dialog v-model="renaming" title="编辑设备" width="420" align-center>
      <el-form label-position="top">
        <el-form-item label="设备名称">
          <el-input v-model="form.name" maxlength="20" />
        </el-form-item>
        <el-form-item label="所在房间">
          <el-select v-model="form.room" filterable allow-create style="width: 100%">
            <el-option v-for="r in roomPresets" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="renaming = false">取消</el-button>
        <el-button type="primary" round @click="saveRename">保存</el-button>
      </template>
    </el-dialog>
  </div>

  <!-- 设备不存在 -->
  <div v-else class="missing glass">
    <h3>设备不存在</h3>
    <p>该设备可能已被移除。</p>
    <el-button type="primary" round @click="router.push('/')">返回总控面板</el-button>
  </div>
</template>

<style scoped>
.detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  color: var(--text-soft);
  font-size: 14.5px;
  font-weight: 550;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 10px;
  transition: all 0.18s ease;
}
.back:hover { color: var(--brand); background: var(--surface-2); }
.top-actions { display: flex; gap: 8px; }
.ico {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-soft);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.18s ease;
}
.ico:hover { color: var(--brand); border-color: var(--brand); }
.ico.fav { color: var(--warn); border-color: var(--warn); }
.ico.danger:hover { color: var(--danger); border-color: var(--danger); }

/* 聚光卡 */
.spotlight {
  position: relative;
  padding: 30px 32px;
  border-radius: 24px;
  overflow: hidden;
}
.spot-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(300px 200px at 18% 0%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
}
.spotlight.active .spot-glow { opacity: 1; }
.spot-main {
  position: relative;
  display: flex;
  align-items: center;
  gap: 22px;
}
.spot-icon {
  width: 84px;
  height: 84px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  transition: all 0.3s ease;
  flex-shrink: 0;
}
.spot-icon.on {
  color: #fff;
  background: var(--accent);
  box-shadow: 0 12px 30px color-mix(in srgb, var(--accent) 50%, transparent);
}
.spot-info { flex: 1; }
.spot-info h1 { font-size: 26px; font-weight: 720; }
.spot-sub { color: var(--text-faint); font-size: 13.5px; margin-top: 4px; }
.spot-tags { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
.tag {
  font-size: 12.5px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 9px;
  background: var(--surface-2);
  color: var(--text-soft);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.tag.on { color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, transparent); }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-faint); }
.dot.online { background: var(--ok); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 25%, transparent); }

/* 环形 */
.dial { position: relative; width: 116px; height: 116px; flex-shrink: 0; }
.dial svg { transform: rotate(-90deg); width: 116px; height: 116px; }
.dial-bg { fill: none; stroke: var(--border); stroke-width: 9; }
.dial-fg {
  fill: none;
  stroke: var(--accent);
  stroke-width: 9;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.5s ease;
}
.dial-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.dial-val { font-size: 24px; font-weight: 720; color: var(--text); }
.dial-val i { font-size: 12px; font-style: normal; font-weight: 500; color: var(--text-faint); }
.dial-label { font-size: 11.5px; color: var(--text-faint); }

/* 主开关 */
.spot-power {
  position: relative;
  margin-top: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 22px;
  border-top: 1px solid var(--border);
}
.power-label { font-weight: 600; font-size: 15px; }
.big-switch {
  width: 62px;
  height: 34px;
  border-radius: 22px;
  border: none;
  background: var(--border-strong);
  position: relative;
  cursor: pointer;
  transition: background 0.25s ease;
}
.big-switch.on { background: var(--accent); }
.big-switch:disabled { opacity: 0.5; cursor: not-allowed; }
.bs-knob {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.big-switch.on .bs-knob { transform: translateX(28px); }

/* 面板 */
.panel { padding: 24px 26px; border-radius: 22px; }
.panel-title { font-size: 15px; font-weight: 650; margin-bottom: 18px; color: var(--text-soft); }

.ctrl-list { display: flex; flex-direction: column; gap: 22px; }
.ctrl { transition: opacity 0.2s ease; }
.ctrl.disabled { opacity: 0.45; }
.ctrl-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ctrl-label { font-weight: 550; font-size: 14.5px; }
.ctrl-value { font-weight: 650; color: var(--accent); font-size: 14.5px; }
.ctrl-hint { font-size: 12.5px; color: var(--text-faint); }

/* 分段控件 */
.seg {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.seg-btn {
  padding: 9px 16px;
  border-radius: 11px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-soft);
  font-size: 13.5px;
  font-weight: 550;
  cursor: pointer;
  transition: all 0.18s ease;
}
.seg-btn:hover:not(:disabled) { color: var(--text); border-color: var(--accent); }
.seg-btn.on { color: #fff; background: var(--accent); border-color: var(--accent); }
.seg-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.seg.actions .seg-btn { background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent); border-color: transparent; }
.seg.actions .seg-btn:hover { background: var(--accent); color: #fff; }

/* 读数 */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
}
.metric {
  padding: 16px 18px;
  border-radius: 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
}
.metric-label { font-size: 12.5px; color: var(--text-faint); }
.metric-val { display: block; font-size: 26px; font-weight: 720; margin-top: 6px; }
.metric-val i { font-size: 13px; font-style: normal; font-weight: 500; color: var(--text-faint); margin-left: 3px; }
.metric-bar {
  margin-top: 10px;
  height: 6px;
  border-radius: 4px;
  background: var(--border);
  overflow: hidden;
}
.metric-bar span {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: var(--accent);
  transition: width 0.5s ease;
}

/* 信息 */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.info-row:last-child { border-bottom: none; }
.info-row span { color: var(--text-faint); }
.info-row b { font-weight: 600; }
.mono { font-family: ui-monospace, Consolas, monospace; font-size: 12.5px; }

.missing {
  text-align: center;
  padding: 70px 30px;
  border-radius: 24px;
}
.missing h3 { font-size: 20px; margin-bottom: 8px; }
.missing p { color: var(--text-faint); margin-bottom: 20px; }

@media (max-width: 640px) {
  .spot-main { flex-wrap: wrap; }
 