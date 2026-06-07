<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Moon, Sunny, Plus, Microphone } from '@element-plus/icons-vue'
import { useTheme } from './composables/useTheme'
import { usePairing } from './composables/usePairing'
import PairingDialog from './components/PairingDialog.vue'

const route = useRoute()
const router = useRouter()
const { theme, toggle } = useTheme()
const { openPairing } = usePairing()

const nav = [
  { path: '/', label: '总控面板' },
  { path: '/rooms', label: '房间' },
  { path: '/voice', label: '语音控制' },
  { path: '/settings', label: '设置' },
]

const isDark = computed(() => theme.value === 'dark')
</script>

<template>
  <div class="layout">
    <header class="topbar glass">
      <div class="brand">
        <div class="brand-mark">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none"
               stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 11.5 12 4l9 7.5" />
            <path d="M5.5 10v9.5h13V10" />
            <path d="M10 19.5v-5h4v5" />
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-title">智能中控</span>
          <span class="brand-sub">Whole-Home Control</span>
        </div>
      </div>

      <nav class="nav">
        <router-link
          v-for="item in nav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="actions">
        <button class="icon-btn" @click="router.push('/voice')" title="语音控制">
          <el-icon :size="18"><Microphone /></el-icon>
        </button>
        <button class="icon-btn" @click="toggle" :title="isDark ? '切换浅色' : '切换深色'">
          <el-icon :size="18"><component :is="isDark ? Sunny : Moon" /></el-icon>
        </button>
        <el-button type="primary" :icon="Plus" round class="add-btn" @click="openPairing">
          添加家电
        </el-button>
      </div>
    </header>

    <main class="content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <PairingDialog />
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 24px;
  height: 68px;
  padding: 0 28px;
  margin: 14px 18px 0;
  border-radius: 18px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 180px;
}
.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  background: var(--brand-grad);
  display: grid;
  place-items: center;
  box-shadow: 0 6px 18px rgba(91, 108, 255, 0.4);
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.brand-title {
  font-weight: 700;
  font-size: 16px;
  color: var(--text);
}
.brand-sub {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-faint);
}

.nav {
  display: flex;
  gap: 6px;
  margin: 0 auto;
}
.nav-item {
  padding: 9px 18px;
  border-radius: 11px;
  font-size: 14.5px;
  font-weight: 550;
  color: var(--text-soft);
  transition: all 0.2s ease;
}
.nav-item:hover {
  color: var(--text);
  background: var(--surface-2);
}
.nav-item.active {
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 14%, transparent);
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 11px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-soft);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.2s ease;
}
.icon-btn:hover {
  color: var(--brand);
  border-color: var(--brand);
  transform: translateY(-1px);
}
.add-btn {
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(91, 108, 255, 0.35);
}

.content {
  flex: 1;
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 26px 24px 48px;
}

@media (max-width: 720px) {
  .topbar {
    flex-wrap: wrap;
    height: auto;
    padding: 14px;
    gap: 12px;
  }
  .nav {
    order: 3;
    width: 100%;
    margin: 0;
    justify-content: center;
  }
  .brand-sub { display: none; }
}
</style>
