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
        <button class="icon-btn" @click="toggle" :title="isDark ? '切换浅色' : 