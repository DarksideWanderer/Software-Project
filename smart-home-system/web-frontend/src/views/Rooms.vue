<script setup>
import { computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { useDeviceStore } from '../stores/devices'
import { getCategory } from '../data/catalog'
import { usePairing } from '../composables/usePairing'
import DeviceCard from '../components/DeviceCard.vue'

const store = useDeviceStore()
const { openPairing } = usePairing()

const grouped = computed(() => {
  const groups = store.byRoom
  return Object.keys(groups)
    .sort()
    .map((room) => {
      const devices = groups[room]
      const active = devices.filter((d) => getCategory(d.type).status(d.state).active).length
      return { room, devices, active }
    })
})
</script>

<template>
  <div class="rooms">
    <header class="head">
      <div>
        <h1>房间</h1>
        <p>按空间查看与管理你的设备</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openPairing">添加家电</el-button>
    </header>

    <template v-if="grouped.length">
      <section v-for="g in grouped" :key="g.room" class="room">
        <div class="room-head">
          <h2>{{ g.room }}</h2>
          <span class="room-meta">{{ g.devices.length }} 台设备 · {{ g.active }} 运行中</span>
        </div>
        <div class="grid">
          <DeviceCard v-for="d in g.devices" :key="d.id" :device="d" />
        </div>
      </section>
    </template>

    <section v-else class="empty glass">
      <h3>暂无设备</h3>
      <p>添加设备后将按房间自动归类。</p>
      <el-button type="primary" :icon="Plus" @click="openPairing">配对新设备</el-button>
    </section>
  </div>
</template>

<style scoped>
.rooms { display: flex; flex-direction: column; gap: 26px; }
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.head h1 { font-size: 28px; font-weight: 800; }
.head p { color: var(--text-faint); font-size: 14px; margin-top: 4px; }

.room { display: flex; flex-direction: column; gap: 14px; }
.room-head { display: flex; align-items: baseline; gap: 12px; }
.room-head h2 {
  font-size: 17px;
  font-weight: 800;
  background: var(--ink);
  color: var(--p4-yellow);
  padding: 5px 16px;
  border-radius: var(--r-sm);
  box-shadow: 3px 3px 0 var(--p4-yellow);
}
.room-meta { font-size: 13px; color: var(--text-faint); }

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(216px, 1fr));
  gap: 16px;
}

.empty {
  text-align: center;
  padding: 60px 30px;
}
.empty h3 { font-size: 19px; margin-bottom: 8px; }
.empty p { color: var(--text-faint); margin-bottom: 20px; }
</style>
