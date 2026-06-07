<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import DeviceIcon from './DeviceIcon.vue'
import { getCategory } from '../data/catalog'
import { useDeviceStore } from '../stores/devices'

const props = defineProps({
  device: { type: Object, required: true },
})

const router = useRouter()
const store = useDeviceStore()

const cat = computed(() => getCategory(props.device.type))
const status = computed(() => cat.value.status(props.device.state))
const accent = computed(() => cat.value.accent)

// 是否支持卡片上的快捷开关
const quickable = computed(() =>
  ['light', 'ac', 'tv', 'fan', 'purifier', 'plug', 'camera', 'waterHeater', 'curtain', 'lock', 'vacuum'].includes(
    props.device.type,
  ),
)

const open = () => router.push(`/device/${props.device.id}`)

const onQuick = () => {
  if (!props.device.online) return
  store.toggleQuick(props.device.id)
}
</script>

<template>
  <article
    class="card glass"
    :class="{ active: status.active, offline: !device.online }"
    :style="{ '--accent': accent }"
    @click="open"
  >
    <div class="glow" />
    <header class="row">
      <div class="icon-wrap">
        <DeviceIcon :type="device.type" :size="24" />
      </div>
      <span class="state-dot" :class="{ on: status.active }" />
    </header>

    <div class="body">
      <h3 class="name">{{ device.name }}</h3>
      <p class="meta">{{ cat.label }} · {{ device.room }}</p>
    </div>

    <footer class="foot">
      <span class="status">
        <template v-if="device.online">{{ status.text }}</template>
        <template v-else>离线</template>
      </span>
      <button
        v-if="quickable"
        class="quick"
        :class="{ on: status.active }"
        :disabled="!device.online"
        @click.stop="onQuick"
        :title="status.active ? '关闭' : '开启'"
      >
        <span class="knob" />
      </button>
    </footer>
  </article>
</template>

<style scoped>
.card {
  position: relative;
  padding: 18px;
  border-radius: 20px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 158px;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: color-mix(in srgb, var(--accent) 45%, transparent);
}
.card.offline {
  opacity: 0.62;
}

.glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(120px 80px at 80% 0%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}
.card.active .glow {
  opacity: 1;
}

.row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.icon-wrap {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 16%, transparent);
  transition: all 0.25s ease;
}
.card.active .icon-wrap {
  color: #fff;
  background: var(--accent);
  box-shadow: 0 8px 20px color-mix(in srgb, var(--accent) 50%, transparent);
}

.state-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--text-faint);
  margin-top: 6px;
}
.state-dot.on {
  background: var(--accent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 22%, transparent);
}

.body { flex: 1; }
.name {
  font-size: 16px;
  font-weight: 650;
  margin-bottom: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  font-size: 12.5px;
  color: var(--text-faint);
}

.foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.status {
  font-size: 13.5px;
  font-weight: 550;
  color: var(--text-soft);
}
.card.active .status {
  color: var(--accent);
}

/* 卡片快捷开关 */
.quick {
  width: 46px;
  height: 27px;
  border-radius: 20px;
  border: none;
  background: var(--border-strong);
  position: relative;
  cursor: pointer;
  transition: background 0.25s ease;
  flex-shrink: 0;
}
.quick.on {
  background: var(--accent);
}
.quick:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 21px;
  height: 21px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.quick.on .knob {
  transform: translateX(19px);
}
</style>
