const devices = {
  aircon: {
    id: "aircon",
    name: "中央空调",
    room: "客厅",
    icon: "icon-ac",
    type: "aircon",
    power: true,
    online: true,
    temperature: 24,
    mode: "自动",
    wind: "中风",
    energy: "1.2 kWh",
    updated: "刚刚",
    color: "#4488a5",
    soft: "#e0eff5",
    glow: "rgba(134, 184, 215, .36)",
  },
  livingLight: {
    id: "livingLight",
    name: "客厅主灯",
    room: "客厅",
    icon: "icon-light",
    type: "light",
    power: true,
    online: true,
    brightness: 72,
    colorTemperature: 4200,
    energy: "0.3 kWh",
    updated: "刚刚",
    color: "#ad8038",
    soft: "#f5ead5",
    glow: "rgba(237, 182, 94, .36)",
  },
  bedroomLight: {
    id: "bedroomLight",
    name: "卧室氛围灯",
    room: "主卧",
    icon: "icon-light",
    type: "light",
    power: false,
    online: true,
    brightness: 35,
    colorTemperature: 3000,
    energy: "0.1 kWh",
    updated: "1 分钟前",
    color: "#9d72a8",
    soft: "#f0e5f2",
    glow: "rgba(158, 145, 200, .32)",
  },
  tv: {
    id: "tv",
    name: "智能电视",
    room: "客厅",
    icon: "icon-tv",
    type: "tv",
    power: false,
    online: true,
    volume: 32,
    source: "影音",
    channel: "栖居影院",
    energy: "0.0 kWh",
    updated: "2 分钟前",
    color: "#7566a0",
    soft: "#e9e5f3",
    glow: "rgba(158, 145, 200, .3)",
  },
  fridge: {
    id: "fridge",
    name: "智能冰箱",
    room: "厨房",
    icon: "icon-fridge",
    type: "fridge",
    power: true,
    online: true,
    temperature: 3,
    freezerTemperature: -18,
    mode: "节能",
    fresh: true,
    energy: "0.9 kWh",
    updated: "刚刚",
    color: "#397e72",
    soft: "#deeee9",
    glow: "rgba(110, 190, 165, .3)",
  },
  fan: {
    id: "fan",
    name: "循环风扇",
    room: "主卧",
    icon: "icon-fan",
    type: "fan",
    power: true,
    online: true,
    speed: 2,
    oscillation: true,
    timer: "关闭",
    energy: "0.2 kWh",
    updated: "刚刚",
    color: "#397499",
    soft: "#deebf2",
    glow: "rgba(134, 184, 215, .32)",
  },
};

const sceneNames = {
  home: "回家模式",
  movie: "观影模式",
  sleep: "睡眠模式",
  away: "离家模式",
};

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

let activeDeviceId = null;
let isRecording = false;
let recordingTimer = null;

function iconMarkup(icon) {
  return `<svg aria-hidden="true"><use href="#${icon}"></use></svg>`;
}

function getDeviceReading(device) {
  if (!device.power) {
    return { value: "已关闭", unit: "", label: "待机" };
  }

  switch (device.type) {
    case "aircon":
      return { value: `${device.temperature}°`, unit: "", label: device.mode };
    case "light":
      return { value: `${device.brightness}`, unit: "%", label: "亮度" };
    case "tv":
      return { value: `${device.volume}`, unit: "%", label: device.source };
    case "fridge":
      return { value: `${device.temperature}°`, unit: "C", label: device.mode };
    case "fan":
      return { value: `${device.speed}`, unit: "档", label: device.oscillation ? "摇头送风" : "定向送风" };
    default:
      return { value: "运行中", unit: "", label: "在线" };
  }
}

function renderDevices() {
  dom.deviceGrid.innerHTML = Object.values(devices)
    .map((device) => {
      const reading = getDeviceReading(device);
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
            ></button>
          </div>
          <div class="device-info">
            <span class="device-location">${device.room}</span>
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

  dom.onlineCount.textContent = Object.values(devices).filter((device) => device.online).length;
  dom.activeCount.textContent = Object.values(devices).filter((device) => device.power).length;
}

function toggleDevice(deviceId, nextPower, options = {}) {
  const device = devices[deviceId];
  if (!device) return;
  device.power = typeof nextPower === "boolean" ? nextPower : !device.power;
  device.updated = "刚刚";
  renderDevices();

  if (activeDeviceId === deviceId) {
    renderDrawer(device);
  }

  if (!options.silent) {
    showToast(`${device.name}已${device.power ? "打开" : "关闭"}`);
  }
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  dom.toastRegion.appendChild(toast);
  window.setTimeout(() => toast.remove(), 2800);
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
  const reading = getDeviceReading(device);
  const controls = getDeviceControls(device);
  dom.drawerContent.innerHTML = `
    <div class="drawer-hero" style="background:linear-gradient(145deg, ${device.color}, #254f42)">
      <div class="drawer-topline">
        <span class="drawer-room">${device.room.toUpperCase()} · 在线</span>
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
        <button class="power-button ${device.power ? "on" : ""}" type="button" aria-label="${device.power ? "关闭" : "打开"}${device.name}"></button>
      </div>
    </div>
    ${device.power ? "" : '<p class="drawer-offline-note">打开设备后即可调整详细控制选项</p>'}
    <div class="drawer-controls ${device.power ? "" : "drawer-disabled"}">
      ${controls}
      <section class="control-section">
        <div class="control-title"><strong>设备信息</strong><span>状态健康</span></div>
        <div class="mini-stat-grid">
          <div class="mini-stat"><span>今日用电</span><strong>${device.energy}</strong></div>
          <div class="mini-stat"><span>最近同步</span><strong>${device.updated}</strong></div>
        </div>
      </section>
    </div>
  `;
}

function updateDrawerSummary(device) {
  const summary = dom.drawerContent.querySelector(".drawer-device-summary p");
  if (!summary) return;
  const reading = getDeviceReading(device);
  summary.textContent = device.power
    ? `${reading.value}${reading.unit} · ${reading.label}`
    : "设备当前处于待机状态";
}

function rangeControl(label, property, value, min, max, suffix, displayValue = value) {
  const progress = ((value - min) / (max - min)) * 100;
  return `
    <section class="control-section">
      <div class="range-heading">
        <label for="control-${property}">${label}</label>
        <output id="output-${property}">${displayValue}${suffix}</output>
      </div>
      <input
        class="range-control"
        id="control-${property}"
        type="range"
        min="${min}"
        max="${max}"
        value="${value}"
        data-property="${property}"
        data-suffix="${suffix}"
        style="--value:${progress}%"
      />
    </section>
  `;
}

function segmentedControl(title, property, options, activeValue) {
  return `
    <section class="control-section">
      <div class="control-title"><strong>${title}</strong><span>${activeValue}</span></div>
      <div class="segmented-control" data-property="${property}">
        ${options
          .map(
            (option) => `
              <button
                class="segment-button ${option === activeValue ? "active" : ""}"
                type="button"
                data-value="${option}"
              >${option}</button>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function inlineToggle(title, description, property, checked) {
  return `
    <div class="inline-toggle-row">
      <div class="inline-toggle-copy">
        <strong>${title}</strong>
        <small>${description}</small>
      </div>
      <button
        class="toggle inline-toggle"
        type="button"
        role="switch"
        aria-checked="${checked}"
        data-property="${property}"
      ></button>
    </div>
  `;
}

function getDeviceControls(device) {
  switch (device.type) {
    case "aircon":
      return `
        ${rangeControl("设定温度", "temperature", device.temperature, 16, 30, "°")}
        ${segmentedControl("运行模式", "mode", ["制冷", "自动", "除湿", "送风"], device.mode)}
        ${segmentedControl("风速", "wind", ["低风", "中风", "高风"], device.wind)}
      `;
    case "light":
      return `
        ${rangeControl("灯光亮度", "brightness", device.brightness, 1, 100, "%")}
        ${rangeControl("色温", "colorTemperature", device.colorTemperature, 2700, 6500, "K")}
        ${segmentedControl("光效预设", "lightPreset", ["阅读", "放松", "自然"], "自然")}
      `;
    case "tv":
      return `
        ${rangeControl("音量", "volume", device.volume, 0, 100, "%")}
        ${segmentedControl("信号源", "source", ["影音", "电视", "游戏"], device.source)}
        <section class="control-section">
          <div class="control-title"><strong>正在播放</strong><span>${device.channel}</span></div>
          <div class="mini-stat-grid">
            <div class="mini-stat"><span>画面模式</span><strong>影院</strong></div>
            <div class="mini-stat"><span>声音模式</span><strong>空间音频</strong></div>
          </div>
        </section>
      `;
    case "fridge":
      return `
        ${rangeControl("冷藏室温度", "temperature", device.temperature, 1, 8, "°")}
        ${rangeControl("冷冻室温度", "freezerTemperature", device.freezerTemperature, -24, -14, "°")}
        ${segmentedControl("运行模式", "mode", ["速冷", "节能", "假日"], device.mode)}
        <section class="control-section">
          ${inlineToggle("智能保鲜", "根据食材自动调节湿度", "fresh", device.fresh)}
        </section>
      `;
    case "fan":
      return `
        ${rangeControl("风速档位", "speed", device.speed, 1, 5, " 档")}
        ${segmentedControl("定时关闭", "timer", ["关闭", "1 小时", "2 小时", "4 小时"], device.timer)}
        <section class="control-section">
          ${inlineToggle("左右摇头", "扩大室内空气循环范围", "oscillation", device.oscillation)}
        </section>
      `;
    default:
      return "";
  }
}

function applyScene(sceneId, options = {}) {
  document.querySelectorAll(".scene-chip").forEach((chip) => {
    chip.classList.toggle("running", chip.dataset.scene === sceneId);
  });

  switch (sceneId) {
    case "home":
      Object.assign(devices.aircon, { power: true, temperature: 24, mode: "自动" });
      Object.assign(devices.livingLight, { power: true, brightness: 72 });
      Object.assign(devices.bedroomLight, { power: false });
      break;
    case "movie":
      Object.assign(devices.tv, { power: true, volume: 28, source: "影音" });
      Object.assign(devices.livingLight, { power: true, brightness: 18, colorTemperature: 3000 });
      Object.assign(devices.bedroomLight, { power: false });
      break;
    case "sleep":
      Object.assign(devices.aircon, { power: true, temperature: 26, mode: "自动", wind: "低风" });
      Object.assign(devices.bedroomLight, { power: true, brightness: 12, colorTemperature: 2700 });
      Object.assign(devices.livingLight, { power: false });
      Object.assign(devices.tv, { power: false });
      Object.assign(devices.fan, { power: false });
      break;
    case "away":
      Object.values(devices).forEach((device) => {
        if (device.type !== "fridge") device.power = false;
      });
      break;
    default:
      return;
  }

  renderDevices();
  if (!options.silent) showToast(`${sceneNames[sceneId]}已开启`);
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

function escapeHtml(text) {
  const element = document.createElement("div");
  element.textContent = text;
  return element.innerHTML;
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

function respondToCommand(command) {
  const normalized = command.replace(/\s+/g, "");
  const target = findTargetDevice(normalized);
  const wantsOff = /关闭|关掉|关上|停掉/.test(normalized);
  const wantsOn = /打开|开启|启动|开开/.test(normalized);

  if (/回家模式|回家场景/.test(normalized)) {
    applyScene("home", { silent: true });
    return "回家模式已开启：客厅灯和空调已调整到舒适状态。";
  }
  if (/观影模式|看电影|影院模式/.test(normalized)) {
    applyScene("movie", { silent: true });
    return "观影模式已开启：电视已打开，客厅灯已调暗至 18%。";
  }
  if (/睡眠模式|睡觉模式|我要睡觉/.test(normalized)) {
    applyScene("sleep", { silent: true });
    return "睡眠模式已开启：非必要设备已关闭，卧室夜灯保持 12% 亮度。";
  }
  if (/离家模式|我要出门|离开家/.test(normalized)) {
    applyScene("away", { silent: true });
    return "离家模式已开启：除冰箱外的设备均已关闭。";
  }
  if (/全部关闭|关闭全部|所有设备.*关/.test(normalized)) {
    Object.values(devices).forEach((device) => {
      if (device.type !== "fridge") device.power = false;
    });
    renderDevices();
    return "已关闭除冰箱外的所有设备。";
  }
  if (!target) {
    return "我暂时没找到对应设备。你可以试试说“打开客厅灯”或“空调调到 22 度”。";
  }

  const device = devices[target];
  const numberMatch = normalized.match(/-?\d+/);
  const value = numberMatch ? Number(numberMatch[0]) : null;

  if (wantsOff) {
    toggleDevice(target, false, { silent: true });
    return `${device.name}已关闭。`;
  }

  if (value !== null) {
    if (device.type === "aircon" && /度|温度|调到/.test(normalized)) {
      device.temperature = Math.min(30, Math.max(16, value));
      device.power = true;
      renderDevices();
      return `好的，${device.name}已调到 ${device.temperature}°。`;
    }
    if (device.type === "light" && /亮度|%|百分/.test(normalized)) {
      device.brightness = Math.min(100, Math.max(1, value));
      device.power = true;
      renderDevices();
      return `${device.name}亮度已调到 ${device.brightness}%。`;
    }
    if (device.type === "tv" && /音量|声音/.test(normalized)) {
      device.volume = Math.min(100, Math.max(0, value));
      device.power = true;
      renderDevices();
      return `电视音量已调到 ${device.volume}%。`;
    }
    if (device.type === "fan" && /档|风速/.test(normalized)) {
      device.speed = Math.min(5, Math.max(1, value));
      device.power = true;
      renderDevices();
      return `风扇已调到 ${device.speed} 档。`;
    }
  }

  if (wantsOn || /调到|调成/.test(normalized)) {
    toggleDevice(target, true, { silent: true });
    return `${device.name}已打开。`;
  }

  return `${device.name}目前${device.power ? "正在运行" : "处于关闭状态"}，${getStatusSentence(device)}`;
}

function findTargetDevice(command) {
  if (/卧室灯|氛围灯|床头灯/.test(command)) return "bedroomLight";
  if (/客厅灯|主灯|灯光/.test(command)) return "livingLight";
  if (/空调/.test(command)) return "aircon";
  if (/电视|TV/i.test(command)) return "tv";
  if (/冰箱/.test(command)) return "fridge";
  if (/风扇/.test(command)) return "fan";
  return null;
}

function getStatusSentence(device) {
  const reading = getDeviceReading(device);
  if (!device.power) return "需要我帮你打开吗？";
  return `当前状态为 ${reading.value}${reading.unit}，${reading.label}。`;
}

function sendCommand(command) {
  const trimmed = command.trim();
  if (!trimmed) return;

  openChat();
  addMessage(trimmed, "user");
  dom.input.value = "";
  showTyping();

  window.setTimeout(() => {
    document.querySelector("#typingMessage")?.remove();
    const response = respondToCommand(trimmed);
    addMessage(response, "assistant");
    showToast("智能指令已执行");
  }, 650);
}

function startRecording() {
  if (isRecording) {
    finishRecording();
    return;
  }

  isRecording = true;
  openChat();
  dom.assistantWrap.classList.add("recording");
  dom.voiceButton.classList.add("recording");
  dom.assistantStatus.textContent = "正在聆听… 点击可停止";
  dom.voiceButton.setAttribute("aria-label", "停止录音");

  recordingTimer = window.setTimeout(finishRecording, 3200);
}

function finishRecording() {
  if (!isRecording) return;
  window.clearTimeout(recordingTimer);
  isRecording = false;
  dom.assistantWrap.classList.remove("recording");
  dom.voiceButton.classList.remove("recording");
  dom.assistantStatus.textContent = "正在识别…";
  dom.voiceButton.setAttribute("aria-label", "按下开始语音");

  window.setTimeout(() => {
    dom.assistantStatus.textContent = "栖居智能助手";
    sendCommand("把卧室氛围灯调到 35%");
  }, 600);
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
    return;
  }

  const segment = event.target.closest(".segment-button");
  if (segment) {
    const group = segment.closest(".segmented-control");
    const property = group.dataset.property;
    devices[activeDeviceId][property] = segment.dataset.value;
    renderDrawer(devices[activeDeviceId]);
    renderDevices();
    showToast(`${devices[activeDeviceId].name}设置已更新`);
    return;
  }

  const inlineToggleButton = event.target.closest(".inline-toggle");
  if (inlineToggleButton) {
    const property = inlineToggleButton.dataset.property;
    devices[activeDeviceId][property] = !devices[activeDeviceId][property];
    renderDrawer(devices[activeDeviceId]);
    renderDevices();
    showToast(`${inlineToggleButton.closest(".inline-toggle-row").querySelector("strong").textContent}已更新`);
  }
});

dom.drawerContent.addEventListener("input", (event) => {
  const range = event.target.closest(".range-control");
  if (!range) return;

  const property = range.dataset.property;
  const value = Number(range.value);
  const suffix = range.dataset.suffix;
  const min = Number(range.min);
  const max = Number(range.max);
  devices[activeDeviceId][property] = value;
  range.style.setProperty("--value", `${((value - min) / (max - min)) * 100}%`);
  document.querySelector(`#output-${property}`).textContent = `${value}${suffix}`;
  renderDevices();
  updateDrawerSummary(devices[activeDeviceId]);
});

dom.drawerContent.addEventListener("change", (event) => {
  const range = event.target.closest(".range-control");
  if (range) showToast(`${devices[activeDeviceId].name}设置已更新`);
});

document.querySelectorAll(".scene-chip").forEach((chip) => {
  chip.addEventListener("click", () => applyScene(chip.dataset.scene));
});

document.querySelector("#openAssistantButton").addEventListener("click", openChat);
document.querySelector("#closeChatButton").addEventListener("click", closeChat);
document.querySelector("#moreScenesButton").addEventListener("click", () => {
  showToast("场景管理功能将在正式版开放");
});
document.querySelector("#securityButton").addEventListener("click", () => {
  showToast("6 台设备在线，网络状态良好");
});

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((navItem) => navItem.classList.remove("active"));
    item.classList.add("active");
    if (!item.getAttribute("data-tooltip")?.includes("总览")) {
      showToast(`${item.getAttribute("data-tooltip") || "此"}模块为视觉演示`);
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

renderDevices();
