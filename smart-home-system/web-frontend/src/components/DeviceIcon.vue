<script setup>
// 通用家电线性图标组件 (纯 SVG, 无任何 Emoji)
// 通过 type 选择对应分类图标, stroke 跟随 currentColor。
import { computed } from 'vue'

const props = defineProps({
  type: { type: String, default: 'light' },
  size: { type: [Number, String], default: 24 },
  stroke: { type: [Number, String], default: 1.6 },
})

const paths = {
  light: 'M12 3a6 6 0 0 0-3.5 10.9c.6.4.9 1 .9 1.7V16h5.2v-.4c0-.7.3-1.3.9-1.7A6 6 0 0 0 12 3Z|M9.5 19h5|M10.5 21.5h3',
  ac: 'M3 5.5h18a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1v-5a1 1 0 0 1 1-1Z|M5 9.5h14|M7 15.5c0 1.4 1 1.4 1 3|M12 15.5c0 1.4 1 1.4 1 3|M17 15.5c0 1.4 1 1.4 1 3',
  curtain: 'M3 4.5h18|M6 5v9.5c0 1.7-.7 2.6-1.7 3.6|M6 5v9.5c0 1.7.7 2.6 1.7 3.6|M12 5v9.5c0 1.7-.7 2.6-1.7 3.6|M12 5v9.5c0 1.7.7 2.6 1.7 3.6|M18 5v9.5c0 1.7-.7 2.6-1.7 3.6|M18 5v9.5c0 1.7.7 2.6 1.7 3.6',
  tv: 'M3 5h18a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z|M9 21h6|M12 17v4',
  fan: 'M12 12.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z|M12 9.5C12 6 13 3.5 15.5 4.5S16 9 12 9.5|M14.5 12c3.5 0 6 1 5-1.5S14 11 14.5 12|M10.5 13.5c-1 3.4-.5 6-2.5 5.4S9 14 10.5 13.5',
  purifier: 'M7 3.5h10a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2Z|M8.5 8h7|M8.5 11h7|M10 15c0 1.4 1 1.4 1 2.8|M14 15c0 1.4 1 1.4 1 2.8',
  vacuum: 'M12 20a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z|M12 15.4a2.4 2.4 0 1 0 0-4.8 2.4 2.4 0 0 0 0 4.8Z|M12 6V4',
  lock: 'M6 11h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1Z|M8.5 11V8a3.5 3.5 0 0 1 7 0v3|M12 15v2.5',
  camera: 'M3 8a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8Z|M15 10.5l6-3.5v10l-6-3.5Z',
  plug: 'M9 3v4|M15 3v4|M6 7h12v3a6 6 0 0 1-12 0V7Z|M12 16v5',
  waterHeater: 'M7 3.5h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-10a2 2 0 0 1 2-2Z|M9 21h2|M13 21h2|M12 7.5c-1.6 2-2.6 3.2-2.6 4.5a2.6 2.6 0 0 0 5.2 0c0-1.3-1-2.5-2.6-4.5Z',
  sensor: 'M4 15a8 8 0 0 1 16 0|M12 15l3.5-3.5|M12 16.2a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4Z',
  default: 'M7 6h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Z|M9.5 3v3|M14.5 3v3|M9.5 18v3|M14.5 18v3|M3 9.5h3|M3 14.5h3|M18 9.5h3|M18 14.5h3',
}

const segments = computed(() => (paths[props.type] || paths.default).split('|'))
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    :stroke-width="stroke"
    stroke="currentColor"
    stroke-linecap="square"
    stroke-linejoin="miter"
    aria-hidden="true"
  >
    <path v-for="(d, i) in segments" :key="i" :d="d" />
  </svg>
</template>
