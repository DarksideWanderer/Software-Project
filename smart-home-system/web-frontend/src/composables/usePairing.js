import { ref } from 'vue'

// 全局共享的"配对向导"开关, 让顶栏与面板都能唤起同一个配对流程。
const pairingOpen = ref(false)

export function usePairing() {
  const openPairing = () => {
    pairingOpen.value = true
  }
  const closePairing = () => {
    pairingOpen.value = false
  }
  return { pairingOpen, openPairing, closePairing }
}
