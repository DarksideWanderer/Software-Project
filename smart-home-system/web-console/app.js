const API_BASE = window.SMART_HOME_API_BASE || "http://127.0.0.1:8000/api/v1";

const dom = {
  deviceGrid: document.querySelector("#deviceGrid"),
  onlineCount: document.querySelector("#onlineCount"),
  activeCount: document.querySelector("#activeCount"),
  drawer: document.querySelector("#deviceDrawer"),
  drawerContent: document.querySelector("#drawerContent"),
  drawerBackdrop: document.querySelector("#drawerBackdrop"),
  assistantWrap: document.querySelector("#assistantWrap"),
  chatPanel: document.querySelector("#chatPanel"),
  messages: document.querySelector("#messages"),
  form: document.querySelector("#assistantForm"),
  input: document.querySelector("#assistantInput"),
  voiceButton: document.querySelector("#voiceButton"),
  voiceFeedback: document.querySelector("#voiceFeedback"),
  assistantStatus: document.querySelector("#assistantStatus"),
  toastRegion: document.querySelector("#toastRegion"),
};

let devices = {};
let scenes = [];
let activeDeviceId = null;
let isRecording = false;
let recordingTimer = null;
let recordingSession = null;

function iconMarkup(icon) {
  return `<svg aria-hidden="true"><use href="#${icon}"></use></svg>`;
}

function escapeHtml(text) {
  const element = document.createElement("div");
  element.textContent = text;
  return element.innerHTML;
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: options.body instanceof FormData
      ? options.headers
      : { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "服务暂时不可用";
    throw new Error(detail);
  }
  return data;
}

function normalizeDeviceList(list) {
  devices = Object.fromEntries(list.map((device) => [device.id, device]));
}

async function loadDashboard(options = {}) {
  try {
    const dashboard = await apiRequest("/dashboard");
    normalizeDeviceList(dashboard.devices || []);
    scenes = dashboard.scenes || [];
    renderDevices();
    renderScenes();
    if (!options.silent) {
      showToast("设备状态已同步");
    }
  } catch (error) {
    renderOfflineState(error.message);
    showToast(`无法连接 backend-core：${error.message}`);
  }
}

function renderOfflineState(message) {
  dom.deviceGrid.innerHTML = `
    <article class="device-card" tabindex="0">
      <div class="device-info">
        <span class="device-location">BACKEND</span>
        <h3>后端未连接</h3>
      </div>
      <div class="device-card-bottom">
        <span class="device-state"><strong>离线</strong></span>
        <span class="device-status-label">${escapeHtml(message)}</span>
      </div>
    </article>
  `;
  dom.onlineCount.textContent = "0";
  dom.activeCount.textContent = "0";
}

function renderScenes() {
  const knownSceneIds = new Set(scenes.map((scene) => scene.id));
  document.querySelectorAll(".scene-chip").forEach((chip) => {
    chip.hidden = !knownSceneIds.has(chip.dataset.scene);
  });
}

function renderDevices() {
  const list = Object.values(devices);
  dom.deviceGrid.innerHTML = list
    .map((device) => {
      const reading = device.reading || { value: "未知", unit: "", label: "未同步" };
      return `
        <article
          class="device-card ${device.power ? "is-on" : ""}"
          data-device-id="${device.id}"
          tabindex="0"
          role="button"
          aria-label="查看${device.name}详情"
          style="--device-color:${device.color};--device-soft:${device.soft};--device-glow:${device.glow}"
        >
          <div class="device-card-top">
            <span class="device-icon">${iconMarkup(device.icon)}</span>
            <button
              class="toggle device-toggle"
              type="button"
              role="switch"
              aria-label="${device.power ? "关闭" : "打开"}${device.name}"
              aria-checked="${device.power}"
              data-toggle-id="${device.id}"
              ${device.online ? "" : "disabled"}
            ></button>
          </div>
          <div class="device-info">
            <span class="device-location">${device.room} · ${device.online ? "在线" : "未连接"}</span>
            <h3>${device.name}</h3>
          </div>
          <div class="device-card-bottom">
            <span class="device-state"><strong>${reading.value}</strong>${reading.unit}</span>
            <span class="device-status-label">${device.power ? reading.label : "已关闭"}</span>
          </div>
        </article>
      `;
    })
    .join("");

  dom.onlineCount.textContent = String(list.filter((device) => device.online).length);
  dom.activeCount.textContent = String(list.filter((device) => device.power).length);
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  dom.toastRegion.appendChild(toast);
  window.setTimeout(() => toast.remove(), 3200);
}

function openDrawer(deviceId) {
  const device = devices[deviceId];
  if (!device) return;
  activeDeviceId = deviceId;
  renderDrawer(device);
  dom.drawer.classList.add("open");
  dom.drawerBackdrop.classList.add("visible");
  dom.drawer.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeDrawer() {
  dom.drawer.classList.remove("open");
  dom.drawerBackdrop.classList.remove("visible");
  dom.drawer.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  window.setTimeout(() => {
    activeDeviceId = null;
  }, 360);
}

function renderDrawer(device) {
  const reading = device.reading || { value: "未知", unit: "", label: "未同步" };
  const controls = getDeviceControls(device);
  dom.drawerContent.innerHTML = `
    <div class="drawer-hero" style="background:linear-gradient(145deg, ${device.color}, #254f42)">
      <div class="drawer-topline">
        <span class="drawer-room">${device.room.toUpperCase()} · ${device.online ? "在线" : "未连接"}</span>
        <button class="icon-button drawer-close" type="button" aria-label="关闭设备详情">
          ${iconMarkup("icon-close")}
        </button>
      </div>
      <div class="drawer-device-summary">
        <div>
          <span class="drawer-device-icon">${iconMarkup(device.icon)}</span>
          <h2>${device.name}</h2>
          <p>${device.power ? `${reading.value}${reading.unit} · ${reading.label}` : "设备当前处于待机状态"}</p>
        </div>
        <button class="power-button ${device.power ? "on" : ""}" type="button" aria-label="${device.power ? "关闭" : "打开"}${device.name}" ${device.online ? "" : "disabled"}></button>
      </div>
    </div>
    ${device.online ? "" : '<p class="drawer-offline-note">请先启动对应 C++ 设备模拟器</p>'}
    ${device.power ? "" : '<p class="drawer-offline-note">打开设备后即可调整详细控制选项</p>'}
    <div class="drawer-controls ${device.power && device.online ? "" : "drawer-disabled"}">
      ${controls}
      <section class="control-section">
        <div class="control-title"><strong>设备信息</strong><span>真实后端状态</span></div>
        <div class="mini-stat-grid">
          <div class="mini-stat"><span>今日用电</span><strong>${device.energy}</strong></div>
          <div class="mini-stat"><span>最近同步</span><strong>${device.updated}</strong></div>
        </div>
      </section>
    </div>
  `;
}

function rangeControl(label, property, value, min, max, suffix, command, param) {
  const safeValue = Number(value ?? min);
  const progress = ((safeValue - min) / (max - min)) * 100;
  return `
    <section class="control-section">
      <div class="range-heading">
        <label for="control-${property}">${label}</label>
        <output id="output-${property}">${safeValue}${suffix}</output>
      </div>
      <input
        class="range-control"
        id="control-${property}"
        type="range"
        min="${min}"
        max="${max}"
        value="${safeValue}"
        data-property="${property}"
        data-suffix="${suffix}"
        data-command="${command}"
        data-param="${param}"
        style="--value:${progress}%"
      />
    </section>
  `;
}

function getDeviceControls(device) {
  const state = device.state || {};
  switch (device.type) {
    case "air_conditioner":
      return rangeControl("设定温度", "temperature", state.temperature, 16, 30, "°", "set_temperature", "temperature");
    case "light":
      return rangeControl("灯光亮度", "brightness", state.brightness, 0, 100, "%", "set_brightness", "brightness");
    case "tv":
      return `
        ${rangeControl("音量", "volume", state.volume, 0, 100, "%", "set_volume", "volume")}
        ${rangeControl("频道", "channel", state.channel, 1, 99, "", "set_channel", "channel")}
      `;
    default:
      return "";
  }
}

function updateDeviceFromResponse(response) {
  if (response.device) {
    devices[response.device.id] = response.device;
  }
  if (Array.isArray(response.devices)) {
    normalizeDeviceList(response.devices);
  }
  renderDevices();
  if (activeDeviceId && devices[activeDeviceId]) {
    renderDrawer(devices[activeDeviceId]);
  }
}

async function runDeviceCommand(deviceId, command, params = {}) {
  const response = await apiRequest(`/devices/${deviceId}/commands`, {
    method: "POST",
    body: JSON.stringify({ command, params }),
  });
  if (!response.success) {
    throw new Error(response.message || "设备命令执行失败");
  }
  updateDeviceFromResponse(response);
  return response;
}

async function toggleDevice(deviceId) {
  const device = devices[deviceId];
  if (!device) return;
  try {
    const command = device.power ? "turn_off" : "turn_on";
    await runDeviceCommand(deviceId, command);
    showToast(`${device.name}已${device.power ? "关闭" : "打开"}`);
  } catch (error) {
    showToast(error.message);
    await loadDashboard({ silent: true });
  }
}

async function applyScene(sceneId) {
  document.querySelectorAll(".scene-chip").forEach((chip) => {
    chip.classList.toggle("running", chip.dataset.scene === sceneId);
  });
  try {
    const response = await apiRequest(`/scenes/${sceneId}/execute`, { method: "POST" });
    updateDeviceFromResponse(response);
    showToast(`${response.scene?.name || "场景"}已执行`);
  } catch (error) {
    showToast(error.message);
  } finally {
    window.setTimeout(() => {
      document.querySelector(`[data-scene="${sceneId}"]`)?.classList.remove("running");
    }, 1200);
  }
}

function openChat() {
  dom.assistantWrap.classList.add("chat-open");
  window.setTimeout(() => dom.input.focus(), 260);
}

function closeChat() {
  dom.assistantWrap.classList.remove("chat-open");
}

function addMessage(text, sender) {
  const message = document.createElement("div");
  message.className = `message ${sender === "user" ? "user-message" : "assistant-message"}`;
  message.innerHTML = `
    ${sender === "assistant" ? '<span class="message-avatar">栖</span>' : ""}
    <div>
      <p>${escapeHtml(text)}</p>
      <time>现在</time>
    </div>
  `;
  dom.messages.appendChild(message);
  dom.messages.scrollTop = dom.messages.scrollHeight;
}

function showTyping() {
  const typing = document.createElement("div");
  typing.className = "message assistant-message";
  typing.id = "typingMessage";
  typing.innerHTML = `
    <span class="message-avatar">栖</span>
    <div class="typing-indicator"><i></i><i></i><i></i></div>
  `;
  dom.messages.appendChild(typing);
  dom.messages.scrollTop = dom.messages.scrollHeight;
}

async function sendCommand(command) {
  const trimmed = command.trim();
  if (!trimmed) return;

  openChat();
  addMessage(trimmed, "user");
  dom.input.value = "";
  showTyping();

  try {
    const response = await apiRequest("/assistant/messages", {
      method: "POST",
      body: JSON.stringify({ text: trimmed }),
    });
    document.querySelector("#typingMessage")?.remove();
    updateDeviceFromResponse(response);
    addMessage(response.reply || "指令已处理。", "assistant");
  } catch (error) {
    document.querySelector("#typingMessage")?.remove();
    addMessage(`我没能完成这次操作：${error.message}`, "assistant");
    showToast(error.message);
  }
}

async function sendVoiceBlob(blob) {
  const formData = new FormData();
  formData.append("audio", blob, "recording.wav");
  formData.append("language", "zh-CN");

  showTyping();
  try {
    const response = await apiRequest("/assistant/voice", {
      method: "POST",
      body: formData,
    });
    document.querySelector("#typingMessage")?.remove();
    const transcript = response.transcript?.text || "语音指令";
    addMessage(transcript, "user");
    updateDeviceFromResponse(response);
    addMessage(response.reply || "语音指令已处理。", "assistant");
  } catch (error) {
    document.querySelector("#typingMessage")?.remove();
    addMessage(`语音识别失败：${error.message}`, "assistant");
    showToast(error.message);
  }
}

async function startRecording() {
  if (isRecording) {
    finishRecording();
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    const chunks = [];

    processor.onaudioprocess = (event) => {
      chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
    recordingSession = { stream, audioContext, source, processor, chunks, sampleRate: audioContext.sampleRate };

    isRecording = true;
    openChat();
    dom.assistantWrap.classList.add("recording");
    dom.voiceButton.classList.add("recording");
    dom.assistantStatus.textContent = "正在聆听… 点击可停止";
    dom.voiceButton.setAttribute("aria-label", "停止录音");
    recordingTimer = window.setTimeout(finishRecording, 5000);
  } catch (error) {
    showToast("无法访问麦克风，请检查浏览器权限");
  }
}

async function finishRecording() {
  if (!isRecording || !recordingSession) return;
  window.clearTimeout(recordingTimer);
  isRecording = false;
  dom.assistantWrap.classList.remove("recording");
  dom.voiceButton.classList.remove("recording");
  dom.assistantStatus.textContent = "正在识别…";
  dom.voiceButton.setAttribute("aria-label", "按下开始语音");

  const { stream, audioContext, source, processor, chunks, sampleRate } = recordingSession;
  processor.disconnect();
  source.disconnect();
  stream.getTracks().forEach((track) => track.stop());
  await audioContext.close();
  recordingSession = null;

  const wavBlob = encodeWav(chunks, sampleRate);
  dom.assistantStatus.textContent = "栖居智能助手";
  await sendVoiceBlob(wavBlob);
}

function mergeBuffers(chunks) {
  const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Float32Array(length);
  let offset = 0;
  chunks.forEach((chunk) => {
    result.set(chunk, offset);
    offset += chunk.length;
  });
  return result;
}

function encodeWav(chunks, sampleRate) {
  const samples = mergeBuffers(chunks);
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  samples.forEach((sample) => {
    const clamped = Math.max(-1, Math.min(1, sample));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += 2;
  });

  return new Blob([view], { type: "audio/wav" });
}

function writeString(view, offset, text) {
  for (let i = 0; i < text.length; i += 1) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
}

dom.deviceGrid.addEventListener("click", (event) => {
  const toggle = event.target.closest(".device-toggle");
  if (toggle) {
    event.stopPropagation();
    toggleDevice(toggle.dataset.toggleId);
    return;
  }
  const card = event.target.closest(".device-card");
  if (card) openDrawer(card.dataset.deviceId);
});

dom.deviceGrid.addEventListener("keydown", (event) => {
  if ((event.key === "Enter" || event.key === " ") && !event.target.closest(".device-toggle")) {
    event.preventDefault();
    openDrawer(event.target.closest(".device-card")?.dataset.deviceId);
  }
});

dom.drawerBackdrop.addEventListener("click", closeDrawer);
dom.drawerContent.addEventListener("click", (event) => {
  if (event.target.closest(".drawer-close")) {
    closeDrawer();
    return;
  }
  if (event.target.closest(".power-button")) {
    toggleDevice(activeDeviceId);
  }
});

dom.drawerContent.addEventListener("input", (event) => {
  const range = event.target.closest(".range-control");
  if (!range) return;
  const suffix = range.dataset.suffix;
  const min = Number(range.min);
  const max = Number(range.max);
  range.style.setProperty("--value", `${((Number(range.value) - min) / (max - min)) * 100}%`);
  document.querySelector(`#output-${range.dataset.property}`).textContent = `${range.value}${suffix}`;
});

dom.drawerContent.addEventListener("change", async (event) => {
  const range = event.target.closest(".range-control");
  if (!range || !activeDeviceId) return;
  try {
    await runDeviceCommand(activeDeviceId, range.dataset.command, {
      [range.dataset.param]: Number(range.value),
    });
    showToast(`${devices[activeDeviceId].name}设置已更新`);
  } catch (error) {
    showToast(error.message);
    await loadDashboard({ silent: true });
  }
});

document.querySelectorAll(".scene-chip").forEach((chip) => {
  chip.addEventListener("click", () => applyScene(chip.dataset.scene));
});

document.querySelector("#openAssistantButton").addEventListener("click", openChat);
document.querySelector("#closeChatButton").addEventListener("click", closeChat);
document.querySelector("#moreScenesButton").addEventListener("click", () => {
  showToast("课程闭环版本内置回家、观影、离家三个场景");
});
document.querySelector("#securityButton").addEventListener("click", () => {
  showToast(`${dom.onlineCount.textContent} 台设备已连接 DeviceHub`);
});

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((navItem) => navItem.classList.remove("active"));
    item.classList.add("active");
    if (!item.getAttribute("data-tooltip")?.includes("总览")) {
      showToast(`${item.getAttribute("data-tooltip") || "此"}模块为课程展示入口`);
    }
  });
});

dom.form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendCommand(dom.input.value);
});

dom.input.addEventListener("focus", openChat);
dom.voiceButton.addEventListener("click", startRecording);

document.querySelector("#suggestionRow").addEventListener("click", (event) => {
  const suggestion = event.target.closest("[data-command]");
  if (suggestion) sendCommand(suggestion.dataset.command);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (dom.drawer.classList.contains("open")) closeDrawer();
    else closeChat();
  }
});

loadDashboard({ silent: true });
