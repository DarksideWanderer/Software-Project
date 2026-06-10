<script setup>
import { useRoute, useRouter } from 'vue-router'
import { Plus, Microphone } from '@element-plus/icons-vue'
import { usePairing } from './composables/usePairing'
import PairingDialog from './components/PairingDialog.vue'

const route = useRoute()
const router = useRouter()
const { openPairing } = usePairing()

const nav = [
  { path: '/', label: '总控面板', en: 'DASHBOARD' },
  { path: '/rooms', label: '房间', en: 'ROOMS' },
  { path: '/voice', label: '语音控制', en: 'VOICE' },
  { path: '/settings', label: '设置', en: 'CONFIG' },
]
</script>

<template>
  <div class="layout">
    <header class="topbar">
      <nav class="nav">
        <router-link
          v-for="item in nav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-en">{{ item.en }}</span>
        </router-link>
      </nav>

      <div class="actions">
        <button class="icon-btn" @click="router.push('/voice')" title="语音控制">
          <el-icon :size="18"><Microphone /></el-icon>
        </button>
        <el-button type="primary" :icon="Plus" class="add-btn" @click="openPairing">
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

/* 黑色通栏顶栏 (P4RE: 黑底 + 黄色高亮) */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 24px;
  height: 64px;
  padding: 0 28px;
  background: #111;
  color: #f5f5f0;
  border-bottom: 3px solid var(--p4-yellow);
}


.nav {
  display: flex;
  gap: 4px;
  margin-right: auto;
}
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.1;
  padding: 7px 16px;
  font-size: 14px;
  font-weight: 700;
  color: #b5b5ad;
  border-radius: var(--r-sm);
  font-weight: 700;
  transition: all 0.15s ease;
}
.nav-en {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.14em;
  opacity: 0.6;
}
.nav-item:hover {
  color: #fff;
  background: #2a2a2a;
}
.nav-item.active {
  color: #111;
  background: var(--p4-yellow);
  box-shadow: 3px 3px 0 rgba(255, 255, 255, 0.25);
}
.nav-item.active .nav-en {
  opacity: 0.85;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.icon-btn {
  width: 38px;
  height: 38px;
  border: 2px solid #f5f5f0;
  border-radius: 50%;
  background: transparent;
  color: #f5f5f0;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.15s ease;
}
.icon-btn:hover {
  color: #111;
  background: var(--p4-yellow);
  border-color: var(--p4-yellow);
}
.add-btn {
  font-weight: 800;
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
}
</style>
