// 前后端同源部署：API 用相对路径。FRP 只穿透 backend-core 一个端口即可。
const API_BASE = window.SMART_HOME_API_BASE || "/api/v1";

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
  candidateGrid: document.querySelector("#candidateGrid"),
  discoverButton: document.querySelector("#discoverButton"),
  addDeviceButton: document.querySelector("#addDeviceButton"),
  deviceModal: document.querySelector("#deviceModal"),
  sceneModal: document.querySelector("#sceneModal"),
  sceneList: document.querySelector("#sceneList"),
  sceneComposer: document.querySelector("#sceneComposer"),
  sceneNameInput: document.querySelector("#sceneNameInput"),
  sceneTextInput: document.querySelector("#sceneTextInput"),
  ruleDeviceSelect: document.querySelector("#ruleDeviceSelect"),
  ruleCommandSelect: document.querySelector("#ruleCommandSelect"),
  ruleParamInput: document.querySelector("#ruleParamInput"),
  addRuleButton: document.querySelector("#addRuleButton"),
  ruleList: document.querySelector("#ruleList"),
};

let devices = {};
let scenes = [];
let candidates = [];
let sceneRules = [];
let activeDeviceId = null;
let isRecording = false;
let recordingTimer = null;
let recordingSession = null;
let activeSpeechPlayback = null;

function iconMarkup(icon) {
  return `<svg aria-hidden="true"><use href="#${icon}"></use></svg>`;
}

function escapeHtml(text) {
  const element = document.createElement("div");
  element.textContent = text;
  return element.innerHTML;
}

function normalizeSpeech(speech) {
  if (!speech?.url) return null;
  const rawUrl = String(speech.url);
  let url;
  if (/^https?:\/\//i.test(rawUrl)) {
    url = rawUrl;
  } else if (rawUrl.startsWith("/")) {
    url = `${new URL(API_BASE, window.location.origin).origin}${rawUrl}`;
  } else {
    url = new URL(`${API_BASE.replace(/\/$/, "")}/${rawUrl.replace(/^\/+/, "")}`, window.location.origin).toString();
  }
  return {
    url,
    contentType: speech.content_type || "audio/mpeg",
  };
}

function setSpeechButtonState(button, state, label) {
  button.dataset.state = state;
  button.querySelector("span").textContent = label;
  button.setAttribute("aria-label", `${label}语音回复`);
}

function stopActiveSpeech(exceptButton = null) {
  if (!activeSpeechPlayback || activeSpeechPlayback.button === exceptButton) return;
  activeSpeechPlayback.audio.pause();
  activeSpeechPlayback.audio.currentTime = 0;
  setSpeechButtonState(activeSpeechPlayback.button, "ready", "播放");
  activeSpeechPlayback = null;
}

function getSpeechAudio(button, speech) {
  if (button.speechAudio) return button.speechAudio;

  const audio = new Audio(speech.url);
  audio.preload = "none";
  audio.addEventListener("ended", () => {
    if (activeSpeechPlayback?.button === button) {
      activeSpeechPlayback = null;
    }
    setSpeechButtonState(button, "ready", "播放");
  });
  audio.addEventListener("error", () => {
    if (activeSpeechPlayback?.button === button) {
      activeSpeechPlayback = null;
    }
    setSpeechButtonState(button, "failed", "重试");
  });
  button.speechAudio = audio;
  return audio;
}

async function playSpeech(button, speech, options = {}) {
  const audio = getSpeechAudio(button, speech);
  if (button.dataset.state === "playing") {
    audio.pause();
    setSpeechButtonState(button, "ready", "播放");
    activeSpeechPlayback = null;
    return;
  }

  stopActiveSpeech(button);
  if (button.dataset.state === "failed" || audio.ended) {
    audio.currentTime = 0;
  }

  setSpeechButtonState(button, "loading", "准备");
  try {
    await audio.play();
    activeSpeechPlayback = { button, audio };
    setSpeechButtonState(button, "playing", "暂停");
  } catch (error) {
    if (options.autoplay) {
      setSpeechButtonState(button, "ready", "播放");
      showToast("浏览器阻止自动播放，可点击播放语音回复");
      return;
    }
    setSpeechButtonState(button, "failed", "重试");
    showToast("语音播放失败，请稍后重试");
  }
}

function attachSpeechPlayback(message, speech, autoplay = true) {
  const button = message.querySelector(".speech-button");
  if (!button) return;

  button.addEventListener("click", () => playSpeech(button, speech));
  if (autoplay) {
    window.setTimeout(() => playSpeech(button, speech, { autoplay: true }), 120);
  }
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
    candidates = dashboard.candidates || [];
    renderDevices();
    renderScenes();
    renderCandidates();
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
  if (!dom.sceneList) return;
  if (!scenes.length) {
    dom.sceneList.innerHTML = `
      <article class="empty-card">
        <strong>还没有场景</strong>
        <span>添加家电后，可以用自然语言创建场景。</span>
      </article>
    `;
    return;
  }
  dom.sceneList.innerHTML = scenes
    .map((scene) => {
      const icon = scene.id === "movie" ? "icon-tv" : scene.id === "away" ? "icon-shield" : "icon-home";
      const disabled = scene.available === false;
      return `
        <article class="scene-chip ${disabled ? "scene-disabled" : ""}" data-scene="${scene.id}">
          <button class="scene-run" type="button" data-scene-run="${scene.id}" ${disabled ? "disabled" : ""}>
            <span class="scene-icon ${scene.id === "movie" ? "movie-scene" : scene.id === "away" ? "away-scene" : "home-scene"}">
              ${iconMarkup(icon)}
            </span>
            <span><strong>${escapeHtml(scene.name)}</strong><small>${escapeHtml(scene.description || "自定义场景")}</small></span>
          </button>
          ${scene.builtin ? "" : `<button class="scene-delete" type="button" data-scene-delete="${scene.id}" aria-label="删除${escapeHtml(scene.name)}">×</button>`}
        </article>
      `;
    })
    .join("");
}

function renderCandidates() {
  if (!dom.candidateGrid) return;
  const addable = candidates.filter((item) => !item.bound);
  if (!addable.length) {
    dom.candidateGrid.innerHTML = `
      <article class="empty-card">
        <strong>没有发现可添加设备</strong>
        <span>请先启动家电模拟器进程，再点击“检索设备”。已添加设备不会重复显示。</span>
      </article>
    `;
    return;
  }
  dom.candidateGrid.innerHTML = addable
    .map((item) => `
      <article class="candidate-card">
        <div>
          <span class="device-location">DeviceHub 已捕获</span>
          <h3>${escapeHtml(item.display || `${item.type_code || item.type} / ${item.original_name}`)}</h3>
          <small>${escapeHtml(item.room || "未分配")}</small>
        </div>
        <button class="more-button add-device-button" type="button" data-bind-device="${item.id}">添加家电</button>
      </article>
    `)
    .join("");
}

function renderRuleBuilder() {
  if (!dom.ruleDeviceSelect || !dom.ruleCommandSelect || !dom.ruleList) return;
  const list = Object.values(devices);
  dom.ruleDeviceSelect.innerHTML = list.length
    ? list.map((device) => `<option value="${device.id}">${escapeHtml(device.name)} / ${escapeHtml(device.original_name || device.id)}</option>`).join("")
    : '<option value="">暂无已添加设备</option>';
  renderRuleCommandOptions();
  dom.ruleList.innerHTML = sceneRules.length
    ? sceneRules.map((rule, index) => {
        const device = devices[rule.device_id];
        return `
          <div class="rule-item">
            <span>${escapeHtml(device?.name || rule.device_id)} · ${escapeHtml(rule.command)} ${escapeHtml(JSON.stringify(rule.params || {}))}</span>
            <button type="button" data-remove-rule="${index}" aria-label="删除动作">×</button>
          </div>
        `;
      }).join("")
    : '<span class="rule-empty">尚未添加规则动作</span>';
}

function renderRuleCommandOptions() {
  if (!dom.ruleDeviceSelect || !dom.ruleCommandSelect) return;
  const device = devices[dom.ruleDeviceSelect.value];
  const commands = device?.capabilities || [];
  dom.ruleCommandSelect.innerHTML = commands.length
    ? commands.map((command) => `<option value="${command.name}">${escapeHtml(command.description || command.name)}</option>`).join("")
    : '<option value="">暂无命令</option>';
}

function addSceneRule() {
  const device = devices[dom.ruleDeviceSelect?.value];
  const commandName = dom.ruleCommandSelect?.value;
  if (!device || !commandName) {
    showToast("请先选择已添加设备和命令");
    return;
  }
  const capability = (device.capabilities || []).find((item) => item.name === commandName);
  const paramEntries = Object.entries(capability?.params || {});
  const params = {};
  if (paramEntries.length) {
    const [paramName, schema] = paramEntries[0];
    const rawValue = dom.ruleParamInput.value.trim();
    if (!rawValue) {
      showToast("这个命令需要填写参数值");
      return;
    }
    params[paramName] = schema.type === "integer" ? Number(rawValue) : rawValue;
  }
  sceneRules.push({ device_id: device.id, command: commandName, params });
  dom.ruleParamInput.value = "";
  renderRuleBuilder();
}

function deviceConnectionLabel(device) {
  if (device.conflict) return "冲突";
  return device.online ? "在线" : "未连接";
}

function deviceStatusLabel(device, reading) {
  if (device.conflict) return "设备冲突";
  return device.online ? (device.power ? reading.label : "已关闭") : "离线";
}

function renderDevices() {
  const list = Object.values(devices);
  if (!list.length) {
    dom.deviceGrid.innerHTML = `
      <article class="empty-card">
        <strong>家里还没有家电</strong>
        <span>点击“检索设备”，从候选列表中添加家电。</span>
      </article>
    `;
    dom.onlineCount.textContent = "0";
    dom.activeCount.textContent = "0";
    return;
  }
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
            <span class="device-location">${device.room} · ${deviceConnectionLabel(device)}</span>
            <h3>${device.name}${device.online ? "" : `<span class="offline-badge">${device.conflict ? "冲突" : "离线"}</span>`}</h3>
          </div>
          <div class="device-card-bottom">
            <span class="device-state"><strong>${reading.value}</strong>${reading.unit}</span>
            <span class="device-status-label ${device.online ? "" : "offline-label"}">${deviceStatusLabel(device, reading)}</span>
          </div>
        </article>
      `;
    })
    .join("");

  dom.onlineCount.textContent = String(list.filter((device) => device.online).length);
  dom.activeCount.textContent = String(list.filter((device) => device.online && device.power).length);
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  dom.toastRegion.appendChild(toast);
  window.setTimeout(() => toast.remove(), 3200);
}

function openModal(modal) {
  modal?.classList.add("open");
  modal?.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeModal(modal) {
  modal?.classList.remove("open");
  modal?.setAttribute("aria-hidden", "true");
  if (!dom.drawer.classList.contains("open")) {
    document.body.style.overflow = "";
  }
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
        <span class="drawer-room">${device.room.toUpperCase()} · ${deviceConnectionLabel(device)}</span>
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
    ${device.conflict ? `<p class="drawer-offline-note">设备 ID 冲突：缓存类型 ${escapeHtml(device.conflict_expected_type || "unknown")}，当前连接类型 ${escapeHtml(device.conflict_connected_type || "unknown")}。请移除缓存设备，或用正确类型重新启动模拟器。</p>` : ""}
    ${device.online || device.conflict ? "" : '<p class="drawer-offline-note">请先启动对应 C++ 设备模拟器</p>'}
    ${device.power ? "" : '<p class="drawer-offline-note">打开设备后即可调整详细控制选项</p>'}
    <section class="drawer-controls drawer-manage">
      <div class="control-section">
        <div class="control-title"><strong>家庭信息</strong><span>${escapeHtml(device.original_name || device.id)}</span></div>
        <div class="field-grid">
          <label>
            <span>显示名称</span>
            <input type="text" id="deviceNameInput" value="${escapeHtml(device.name)}" />
          </label>
          <label>
            <span>房间</span>
            <input type="text" id="deviceRoomInput" value="${escapeHtml(device.room)}" />
          </label>
        </div>
        <div class="button-row">
          <button class="more-button save-device-button" type="button" data-save-device="${device.id}">保存信息</button>
          <button class="danger-button remove-device-button" type="button" data-remove-device="${device.id}">移除家电</button>
        </div>
      </div>
    </section>
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
    case "fridge":
      return rangeControl("冷藏温度", "temperature", state.temperature, 2, 8, "°", "set_temperature", "temperature");
    case "washer":
      return rangeControl("洗涤进度", "progress", state.progress, 0, 100, "%", "set_progress", "progress");
    case "water_heater":
      return rangeControl("热水温度", "temperature", state.temperature, 35, 65, "°", "set_temperature", "temperature");
    case "air_purifier":
      return rangeControl("净化风速", "speed", state.speed, 1, 5, "档", "set_speed", "speed");
    case "curtain":
      return rangeControl("窗帘开合", "percent", state.percent, 0, 100, "%", "set_open_percent", "percent");
    case "robot_vacuum":
      return rangeControl("电量模拟", "battery", state.battery, 0, 100, "%", "set_battery", "battery");
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
  if (Array.isArray(response.candidates)) {
    candidates = response.candidates;
  }
  if (Array.isArray(response.scenes)) {
    scenes = response.scenes;
  }
  renderDevices();
  renderCandidates();
  renderScenes();
  renderRuleBuilder();
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

async function discoverDevices() {
  try {
    const response = await apiRequest("/devices/discover");
    candidates = response.devices || [];
    renderCandidates();
    showToast("设备检索完成");
  } catch (error) {
    showToast(error.message);
  }
}

async function bindDevice(deviceId) {
  const candidate = candidates.find((item) => item.id === deviceId);
  try {
    const response = await apiRequest(`/devices/${deviceId}/bind`, {
      method: "POST",
      body: JSON.stringify({
        name: candidate?.type_label || candidate?.original_name || deviceId,
        room: candidate?.room || "",
      }),
    });
    updateDeviceFromResponse(response);
    closeModal(dom.deviceModal);
    showToast(`${candidate?.original_name || deviceId} 已添加到家庭`);
  } catch (error) {
    showToast(error.message);
  }
}

async function removeDevice(deviceId) {
  const device = devices[deviceId];
  try {
    const response = await apiRequest(`/devices/${deviceId}`, { method: "DELETE" });
    closeDrawer();
    updateDeviceFromResponse(response);
    showToast(`${device?.name || deviceId} 已移除`);
  } catch (error) {
    showToast(error.message);
  }
}

async function saveDeviceInfo(deviceId) {
  try {
    const response = await apiRequest(`/devices/${deviceId}`, {
      method: "PATCH",
      body: JSON.stringify({
        name: document.querySelector("#deviceNameInput")?.value || "",
        room: document.querySelector("#deviceRoomInput")?.value || "",
      }),
    });
    updateDeviceFromResponse(response);
    showToast("家电信息已保存");
  } catch (error) {
    showToast(error.message);
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

async function deleteScene(sceneId) {
  try {
    const response = await apiRequest(`/scenes/${sceneId}`, { method: "DELETE" });
    scenes = response.scenes || scenes.filter((scene) => scene.id !== sceneId);
    renderScenes();
    showToast("场景已删除");
  } catch (error) {
    showToast(error.message);
  }
}

async function createNaturalScene(event) {
  event.preventDefault();
  const text = dom.sceneTextInput.value.trim();
  const name = dom.sceneNameInput.value.trim();
  if (!text && !sceneRules.length) {
    showToast("请输入自然语言描述，或至少添加一条规则动作");
    return;
  }
  try {
    const response = text
      ? await apiRequest("/scenes/natural", {
          method: "POST",
          body: JSON.stringify({ text: name ? `${name}：${text}` : text }),
        })
      : await apiRequest("/scenes", {
          method: "POST",
          body: JSON.stringify({ name: name || "自定义场景", description: "", commands: sceneRules }),
        });
    scenes = response.scenes || scenes;
    renderScenes();
    dom.sceneNameInput.value = "";
    dom.sceneTextInput.value = "";
    sceneRules = [];
    renderRuleBuilder();
    closeModal(dom.sceneModal);
    showToast("场景已创建");
  } catch (error) {
    showToast(`场景创建失败：${error.message}`);
  }
}

function openChat() {
  dom.assistantWrap.classList.add("chat-open");
  window.setTimeout(() => dom.input.focus(), 260);
}

function closeChat() {
  dom.assistantWrap.classList.remove("chat-open");
}

function addMessage(text, sender, options = {}) {
  const speech = sender === "assistant" ? normalizeSpeech(options.speech) : null;
  const speechMarkup = speech
    ? `<button class="speech-button" type="button" data-state="ready" aria-label="播放语音回复" title="播放语音回复">
        ${iconMarkup("icon-volume")}
        <span>播放</span>
      </button>`
    : "";
  const message = document.createElement("div");
  message.className = `message ${sender === "user" ? "user-message" : "assistant-message"}`;
  message.innerHTML = `
    ${sender === "assistant" ? '<span class="message-avatar">栖</span>' : ""}
    <div class="message-content">
      <p>${escapeHtml(text)}</p>
      ${speechMarkup}
      <time>现在</time>
    </div>
  `;
  dom.messages.appendChild(message);
  dom.messages.scrollTop = dom.messages.scrollHeight;
  if (speech) {
    attachSpeechPlayback(message, speech, options.autoplay !== false);
  }
  return message;
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

function handleAssistantResponse(response, fallbackText) {
  document.querySelector("#typingMessage")?.remove();
  updateDeviceFromResponse(response);
  addMessage(response.reply || fallbackText, "assistant", { speech: response.speech });
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
    handleAssistantResponse(response, "指令已处理。");
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
    handleAssistantResponse(response, "语音指令已处理。");
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
  if (!navigator.mediaDevices?.getUserMedia) {
    showToast("无法访问麦克风，请检查浏览器权限");
    return;
  }

  let stream;
  let audioContext;
  let source;
  let processor;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext();
    // ★ 关键：现代浏览器 AudioContext 默认暂停，必须手动 resume
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }
    source = audioContext.createMediaStreamSource(stream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);
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
    window.clearTimeout(recordingTimer);
    isRecording = false;
    recordingSession = null;
    processor?.disconnect();
    source?.disconnect();
    stream?.getTracks().forEach((track) => track.stop());
    await audioContext?.close().catch(() => {});
    dom.assistantWrap.classList.remove("recording");
    dom.voiceButton.classList.remove("recording");
    dom.assistantStatus.textContent = "栖居智能助手";
    dom.voiceButton.setAttribute("aria-label", "按下开始语音");
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

  if (!chunks.length) {
    dom.assistantStatus.textContent = "栖居智能助手";
    addMessage("未捕获到音频，请检查麦克风权限后重试。", "assistant");
    showToast("录音失败：未捕获到音频数据");
    return;
  }

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
  const removeButton = event.target.closest("[data-remove-device]");
  if (removeButton) {
    removeDevice(removeButton.dataset.removeDevice);
    return;
  }
  const saveButton = event.target.closest("[data-save-device]");
  if (saveButton) {
    saveDeviceInfo(saveButton.dataset.saveDevice);
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

dom.candidateGrid?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-bind-device]");
  if (button) bindDevice(button.dataset.bindDevice);
});

dom.discoverButton?.addEventListener("click", discoverDevices);
dom.addDeviceButton?.addEventListener("click", () => {
  openModal(dom.deviceModal);
  discoverDevices();
});

document.querySelectorAll("[data-close-modal]").forEach((button) => {
  button.addEventListener("click", () => closeModal(document.querySelector(`#${button.dataset.closeModal}`)));
});

[dom.deviceModal, dom.sceneModal].forEach((modal) => {
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) closeModal(modal);
  });
});

dom.sceneList?.addEventListener("click", (event) => {
  const runButton = event.target.closest("[data-scene-run]");
  if (runButton) {
    applyScene(runButton.dataset.sceneRun);
    return;
  }
  const deleteButton = event.target.closest("[data-scene-delete]");
  if (deleteButton) deleteScene(deleteButton.dataset.sceneDelete);
});

dom.sceneComposer?.addEventListener("submit", createNaturalScene);
dom.ruleDeviceSelect?.addEventListener("change", renderRuleCommandOptions);
dom.addRuleButton?.addEventListener("click", addSceneRule);
dom.ruleList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-rule]");
  if (!button) return;
  sceneRules.splice(Number(button.dataset.removeRule), 1);
  renderRuleBuilder();
});

document.querySelector("#openAssistantButton").addEventListener("click", openChat);
document.querySelector("#closeChatButton").addEventListener("click", closeChat);
document.querySelector("#moreScenesButton").addEventListener("click", () => {
  renderRuleBuilder();
  openModal(dom.sceneModal);
  window.setTimeout(() => dom.sceneNameInput?.focus(), 120);
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
    if (dom.deviceModal?.classList.contains("open")) closeModal(dom.deviceModal);
    else if (dom.sceneModal?.classList.contains("open")) closeModal(dom.sceneModal);
    else if (dom.drawer.classList.contains("open")) closeDrawer();
    else closeChat();
  }
});

loadDashboard({ silent: true });
