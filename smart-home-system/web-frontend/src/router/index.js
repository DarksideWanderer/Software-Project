import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/rooms',
    name: 'Rooms',
    component: () => import('../views/Rooms.vue'),
  },
  {
    path: '/voice',
    name: 'VoiceControl',
    component: () => import('../views/VoiceControl.vue'),
  },
  {
    path: '/device/:id',
    name: 'DeviceDetail',
    component: () => import('../views/DeviceDetail.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
