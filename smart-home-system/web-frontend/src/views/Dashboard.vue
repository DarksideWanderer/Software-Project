<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useDeviceStore } from '../stores/devices'
import { categoryList, getCategory } from '../data/catalog'
import { usePairing } from '../composables/usePairing'
import DeviceCard from '../components/DeviceCard.vue'
import DeviceIcon from '../components/DeviceIcon.vue'

const store = useDeviceStore()
const { openPairing } = usePairing()

const keyword = ref('')
const activeFilter = ref('all')

// 顶部问候语
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// 概览统计
const stats = computed(() => [
  { label: '设备总数', value: store.total, suffix: '台' },
  { label: '在线', value: store.onlineCount, suffix: '台' },
  { label: '运行中', value: store.activeCount, suffix: '台' },
  { label: '房间', value: store.rooms.length, suffix: '个' },
])

// 室内环境 (取第一个传感器)
const env = computed(() => {
  const s = store.devices.find((d) => d.type === 'sensor')
  return s ? s.state : null
})

// 分类筛选项 (仅显示已拥有的分类)
const ownedTypes = computed(() => {
  const set = new Set(store.devices.map((d) => d.type))
  return categoryList.filter((c) => set.has(c.type))
})

const filtered = computed(() => {
  let list = store.devices
  if (activeFilter.value !== 'all') {
    list = list.filter((d) => d.type === activeFilter.value)
  }
  const kw = keyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter(
      (d) =>
        d.name.toLowerCase().includes(kw) ||
        d.room.toLowerCase().includes(kw) ||
        getCategory(d.type).label.includes(kw),
    )
  }
  return [...list].sort((a, b) => Number(b.favorite) - Number(a.favorite))
})

// 快捷场景
const scenes = [
  { key: 'home', label: '回家模式', desc: '开客厅灯与空调' },
  { key: 'away', label: '离家模式', desc: '关电断电并落锁' },
  { key: 'night', label: '晚安模式', desc: '关灯锁门' },
  { key: 'allOff', label: '一键全关', desc: '关闭所有电源' },
]

function runScene(key) {
  store.runScene(key)
  const name = scenes.find((s) => s.key === key)?.label
  ElMessage.success(`已执行「${name}」`)
}

// 模拟实时数据
let timer = null
onMounted(() => {
  timer = setInterval(() => (store.isLive ? store.refreshLive() : store.simulateTick()), 4000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="dash">
    <!-- 概览头部 -->
    <section class="hero glass">
      <div class="hero-left">
        <p class="hero-greet">{{ greeting }}，欢迎回家</p>
        <h1 class="hero-title">全屋设备一览</h1>
        <div class="stat-row">
          <div v-for="s in stats" :key="s.label" class="stat">
            <span class="stat-val">{{ s.value }}<i>{{ s.suffix }}</i></span>
            <span class="stat-label">{{ s.label }}</span>
          </div>
        </div>
      </div>
      <div v-if="env" class="env">
        <div class="env-item">
          <span class="env-num">{{ env.temp }}<i>℃</i></span>
          <span class="env-cap">室内温度</span>
        </div>
        <div class="env-divider" />
        <div class="env-item">
          <span class="env-num">{{ env.humidity }}<i>%</i></span>
          <span class="env-cap">湿度</span>
        </div>
        <div class="env-divider" />
        <div class="env-item">
          <span class="env-num">{{ env.pm25 }}</span>
          <span class="env-cap">PM2.5</span>
        </div>
      </div>
    </section>

    <!-- 快捷场景 -->
    <section class="scenes">
      <button v-for="sc in scenes" :key="sc.key" class="scene glass" @click="runScene(sc.key)">
        <span class="scene-title">{{ sc.label }}</span>
        <span class="scene-desc">{{ sc.desc }}</span>
      </button>
    </section>

    <!-- 工具栏 -->
    <section class="toolbar">
      <div class="filters">
        <button class="chip" :class="{ on: activeFilter === 'all' }" @click="activeFilter = 'all'">
          全部
        </button>
        <button
          v-for="c in ownedTypes"
          :key="c.type"
          class="chip"
          :class="{ on: activeFilter === c.type }"
          :style="{ '--accent': c.accent, '--on-accent': c.onAccent }"
          @click="activeFilter = c.type"
        >
          <DeviceIcon :type="c.type" :size="15" />
          {{ c.label }}
        </button>
      </div>
      <el-input
        v-model="keyword"
        :prefix-icon="Search"
        placeholder="搜索设备或房间"
        class="search"
        clearable
      />
    </section>

    <!-- 设备网格 -->
    <section v-if="filtered.length" class="grid">
      <DeviceCard v-for="d in filtered" :key="d.id" :device="d" />
      <button class="add-card" @click="openPairing">
        <el-icon :size="26"><Plus /></el-icon>
        <span>添加家电</span>
      </button>
    </section>

    <!-- 空状态 -->
    <section v-else class="empty glass">
      <div class="empty-icon"><el-icon :size="34"><Plus /></el-icon></div>
      <h3>还没有匹配的设备</h3>
      <p>通过配对添加你的第一台智能家电，开始打造全屋智能。</p>
      <el-button type="primary" :icon="Plus" @click="openPairing">配对新设备</el-button>
    </section>
  </div>
</template>

<style scoped>
.dash {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

/* Hero */
.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 30px 32px;
  flex-wrap: wrap;
  background:
    radial-gradient(rgba(17, 17, 17, 0.08) 1.2px, transparent 1.2px) 0 0 / 12px 12px,
    var(--p4-yellow);
  border-color: var(--ink);
  color: #111;
  box-shadow: 6px 6px 0 var(--ink);
}
.hero-greet {
  color: rgba(17, 17, 17, 0.62);
  font-size: 14px;
  margin-bottom: 4px;
}
.hero-title {
  font-size: 32px;
  font-weight: 900;
  margin-bottom: 22px;
  color: #111;
  display: inline-block;
  text-shadow: 3px 3px 0 #fff;
}
.stat-row {
  display: flex;
  gap: 34px;
  flex-wrap: wrap;
}
.stat {
  display: flex;
  flex-direction: column;
}
.stat-val {
  font-size: 26px;
  font-weight: 800;
  color: #111;
}
.stat-val i {
  font-size: 14px;
  font-weight: 500;
  color: rgba(17, 17, 17, 0.55);
  font-style: normal;
  margin-left: 3px;
}
.stat-label {
  font-size: 12.5px;
  color: rgba(17, 17, 17, 0.62);
  margin-top: 2px;
}

.env {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 18px 26px;
  background: var(--brand-grad);
  color: #fff;
  border: 2px solid var(--ink);
  border-radius: var(--r-md);
  box-shadow: 4px 4px 0 rgba(17, 17, 17, 0.85);
}
.env-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.env-num {
  font-size: 24px;
  font-weight: 800;
  color: var(--p4-yellow);
}
.env-num i {
  font-size: 13px;
  font-style: normal;
  font-weight: 500;
  opacity: 0.85;
  margin-left: 2px;
}
.env-cap {
  font-size: 11.5px;
  opacity: 0.85;
  margin-top: 2px;
}
.env-divider {
  width: 1px;
  height: 38px;
  background: rgba(255, 255, 255, 0.3);
}

/* 场景 */
.scenes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.scene {
  text-align: left;
  padding: 16px 18px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.scene:hover {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 var(--p4-yellow-deep);
  border-color: var(--ink);
}
.scene-title {
  font-weight: 650;
  font-size: 15px;
}
.scene-desc {
  font-size: 12px;
  color: var(--text-faint);
}

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.chip {
  --accent: var(--brand);
  --on-accent: var(--on-brand);
  border-radius: var(--r-full);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-soft);
  font-size: 13.5px;
  font-weight: 550;
  cursor: pointer;
  transition: all 0.18s ease;
}
.chip:hover {
  color: var(--text);
  border-color: var(--accent);
}
.chip.on {
  color: var(--on-accent);
  background: var(--accent);
  border-color: var(--accent);
}
.search {
  width: 240px;
}

/* 网格 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(216px, 1fr));
  gap: 16px;
}
.add-card {
  border: 1.5px dashed var(--border-strong);
  background: transparent;
  color: var(--text-faint);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 158px;
  font-size: 14px;
  font-weight: 550;
  transition: all 0.2s ease;
}
.add-card:hover {
  color: var(--brand);
  border-color: var(--brand);
  background: color-mix(in srgb, var(--brand) 6%, transparent);
}

/* 空状态 */
.empty {
  text-align: center;
  padding: 60px 30px;
}
.empty-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 18px;
  display: grid;
  place-items: center;
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 14%, transparent);
}
.empty h3 {
  font-size: 19px;
  margin-bottom: 8px;
}
.empty p {
  color: var(--text-faint);
  margin-bottom: 20px;
  max-width: 380px;
  margin-inline: auto;
}

@media (max-width: 900px) {
  .scenes { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .search { width: 100%; }
  .stat-row { gap: 22px; }
}
</style>
