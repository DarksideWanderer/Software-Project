/**
 * web-console 前端 JavaScript 单元测试 (Jest)
 *
 * 安装依赖:
 *   cd smart-home-system/web-console
 *   npm init -y
 *   npm install --save-dev jest jsdom
 *
 * 运行:
 *   npx jest --config jest.config.js
 *
 * jest.config.js:
 *   module.exports = {
 *     testEnvironment: 'jsdom',
 *     roots: ['<rootDir>/tests'],
 *   };
 */

// ======================== Mock Setup ========================

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    headers: new Headers(),
  })
);

// Mock DOM elements
document.body.innerHTML = `
<div id="deviceGrid"></div>
<span id="onlineCount">0</span>
<span id="activeCount">0</span>
<div id="deviceDrawer" class="drawer"><div id="drawerContent"></div></div>
<div id="drawerBackdrop"></div>
<div id="assistantWrap"><div id="chatPanel"><div id="messages"></div></div></div>
<form id="assistantForm"><input id="assistantInput" /></form>
<button id="voiceButton"><span></span></button>
<div id="voiceFeedback"></div>
<div id="assistantStatus"></div>
<div id="toastRegion"></div>
<div id="candidateGrid"></div>
<button id="discoverButton"></button>
<button id="addDeviceButton"></button>
<div id="deviceModal"></div>
<div id="sceneModal"></div>
<div id="sceneList"></div>
<div id="sceneComposer"></div>
<input id="sceneNameInput" />
<input id="sceneTextInput" />
<select id="ruleDeviceSelect"></select>
<select id="ruleCommandSelect"></select>
<input id="ruleParamInput" />
<button id="addRuleButton"></button>
<div id="ruleList"></div>
`;

// Load the app.js module (inline for testing)
const fs = require('fs');
const path = require('path');

// ======================== Tests ========================

describe('Utility Functions', () => {
  // 在测试前加载 app.js
  beforeAll(() => {
    // 动态加载 app.js 脚本
    const scriptContent = fs.readFileSync(
      path.join(__dirname, '..', 'app.js'),
      'utf-8'
    );
    // 提取可测试的函数
    eval(scriptContent);
  });

  test('escapeHtml escapes special characters', () => {
    expect(escapeHtml('<script>alert("xss")</script>')).toBe(
      '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
    );
  });

  test('escapeHtml handles empty string', () => {
    expect(escapeHtml('')).toBe('');
  });

  test('escapeHtml handles normal text', () => {
    expect(escapeHtml('Hello World')).toBe('Hello World');
  });

  test('iconMarkup returns SVG', () => {
    const result = iconMarkup('icon-ac');
    expect(result).toContain('<svg');
    expect(result).toContain('#icon-ac');
  });
});

describe('API Request', () => {
  test('apiRequest builds correct URL', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'ok' }),
        headers: new Headers(),
      })
    );

    const result = await apiRequest('/dashboard');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/dashboard'),
      expect.any(Object)
    );
    expect(result.status).toBe('ok');
  });

  test('apiRequest handles error response', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ detail: 'Service unavailable' }),
        headers: new Headers(),
      })
    );

    await expect(apiRequest('/dashboard')).rejects.toThrow('Service unavailable');
  });
});

describe('Device Normalization', () => {
  test('normalizeDeviceList creates lookup map', () => {
    const list = [
      { id: 'ac-003', name: '客厅空调' },
      { id: 'light-001', name: '客厅主灯' },
    ];
    normalizeDeviceList(list);
    expect(devices).toBeDefined();
    expect(devices['ac-003'].name).toBe('客厅空调');
    expect(devices['light-001'].name).toBe('客厅主灯');
  });

  test('normalizeDeviceList with empty list', () => {
    normalizeDeviceList([]);
    expect(Object.keys(devices).length).toBe(0);
  });
});

describe('Speech Handling', () => {
  test('normalizeSpeech returns null for null input', () => {
    expect(normalizeSpeech(null)).toBeNull();
  });

  test('normalizeSpeech returns null for missing url', () => {
    expect(normalizeSpeech({})).toBeNull();
  });

  test('normalizeSpeech handles relative URL', () => {
    const result = normalizeSpeech({
      url: '/api/v1/audio/tts/test.mp3',
      content_type: 'audio/mpeg',
    });
    expect(result).not.toBeNull();
    expect(result.contentType).toBe('audio/mpeg');
  });

  test('normalizeSpeech handles absolute URL', () => {
    const result = normalizeSpeech({
      url: 'https://example.com/audio.mp3',
      content_type: 'audio/mpeg',
    });
    expect(result).not.toBeNull();
    expect(result.url).toBe('https://example.com/audio.mp3');
  });
});

describe('DOM Rendering', () => {
  test('renderOfflineState shows error message', () => {
    renderOfflineState('Connection refused');
    const grid = document.querySelector('#deviceGrid');
    expect(grid.innerHTML).toContain('后端未连接');
    expect(grid.innerHTML).toContain('Connection refused');
  });

  test('renderOfflineState updates counts', () => {
    renderOfflineState('Test');
    expect(document.querySelector('#onlineCount').textContent).toBe('0');
    expect(document.querySelector('#activeCount').textContent).toBe('0');
  });
});
