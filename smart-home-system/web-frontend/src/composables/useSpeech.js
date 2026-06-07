import { ref } from 'vue'

// 封装浏览器 Web Speech API (语音识别 ASR)。
// 在 Chrome / Edge 等支持的浏览器中可调用麦克风实时识别中文。
// 不支持时 supported 为 false, 界面会回退到文本输入。
export function useSpeech() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  const supported = !!SR

  const listening = ref(false)
  const interim = ref('')
  const error = ref('')

  let rec = null
  let onFinal = null

  function ensure() {
    if (!SR || rec) return
    rec = new SR()
    rec.lang = 'zh-CN'
    rec.interimResults = true
    rec.continuous = false
    rec.maxAlternatives = 1

    rec.onresult = (e) => {
      let finalText = ''
      let interimText = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i]
        if (r.isFinal) finalText += r[0].transcript
        else interimText += r[0].transcript
      }
      interim.value = interimText
      if (finalText) {
        interim.value = ''
        onFinal && onFinal(finalText.trim())
      }
    }
    rec.onerror = (e) => {
      error.value = e.error || '识别出错'
      listening.value = false
    }
    rec.onend = () => {
      listening.value = false
      interim.value = ''
    }
  }

  function start(cb) {
    if (!supported) {
      error.value = 'unsupported'
      return
    }
    onFinal = cb
    ensure()
    error.value = ''
    try {
      rec.start()
      listening.value = true
    } catch (e) {
      // start 可能在已运行时抛错, 先停后重启
      try {
        rec.stop()
      } catch (_) {
        /* noop */
      }
    }
  }

  function stop() {
    if (rec) {
      try {
        rec.stop()
      } catch (e) {
        /* noop */
      }
    }
    listening.value = false
  }

  return { supported, listening, interim, error, start, stop }
}
