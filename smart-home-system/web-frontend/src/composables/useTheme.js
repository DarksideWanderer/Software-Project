import { ref, watch } from 'vue'

// 深浅双主题管理: 同步切换自定义 CSS 变量与 Element Plus 暗色主题。
const THEME_KEY = 'shs.theme'

function initial() {
  const saved = localStorage.getItem(THEME_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  // 跟随系统
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

const theme = ref(initial())

function apply(value) {
  const root = document.documentElement
  if (value === 'dark') {
    root.classList.add('dark')
    root.setAttribute('data-theme', 'dark')
  } else {
    root.classList.remove('dark')
    root.setAttribute('data-theme', 'light')
  }
}

apply(theme.value)

watch(theme, (v) => {
  apply(v)
  localStorage.setItem(THEME_KEY, v)
})

export function useTheme() {
  const toggle = () => {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }
  const set = (v) => {
    theme.value = v
  }
  return { theme, toggle, set }
}
