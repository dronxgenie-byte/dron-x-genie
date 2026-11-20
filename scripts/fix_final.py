html = """<!DOCTYPE html>
<html lang="ru" class="theme-neon">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DRON x GENIE</title>
<style>
:root { --bg-dark: #0f0f13; --bg-panel: #1a1a24; --text-main: #e0e0e0; --accent: #8a2be2; --accent-glow: #00f3ff; --border: #2a2a3a; --ok: #00ff88; --err: #ff3355; }
.theme-genie { --bg-dark: #1a0f24; --bg-panel: #2d1b4e; --text-main: #fff8e7; --accent: #ffd700; --accent-glow: #40e0d0; --border: #4a3b6a; }
* { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
body { background: var(--bg-dark); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.top-bar { height: 44px; background: var(--bg-panel); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 15px; flex-shrink: 0; }
.app-icons { display: flex; gap: 8px; }
.app-icon { width: 32px; height: 32px; border-radius: 6px; background: var(--border); display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 11px; color: var(--text-main); transition: 0.2s; border: 1px solid transparent; }
.app-icon:hover { border-color: var(--accent); background: var(--bg-dark); }
.app-icon.active { background: var(--accent); color: #000; font-weight: bold; }
.theme-toggle { background: none; border: 1px solid var(--accent); color: var(--accent); padding: 4px 12px; border-radius: 16px; cursor: pointer; font-size: 12px; }

.scene { display: flex; flex: 1; overflow: hidden; position: relative; }

.panel { background: var(--bg-panel); display: flex; flex-direction: column; overflow: hidden; transition: width 0.3s ease; flex-shrink: 0; }
.panel.left { width: 260px; border-right: 1px solid var(--border); }
.panel.right { width: 260px; border-left: 1px solid var(--border); }
.panel.collapsed { width: 0; min-width: 0; border: none; }
.panel.collapsed .panel-header,
.panel.collapsed .panel-content,
.panel.collapsed .panel-help,
.panel.collapsed .lamp-btn { display: none; }

.panel-header { display: flex; align-items: center; gap: 8px; padding: 10px; cursor: pointer; border-bottom: 1px solid var(--border); user-select: none; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.status-dot.online { background: var(--ok); box-shadow: 0 0 8px var(--ok); }
.status-dot.offline { background: var(--err); box-shadow: 0 0 8px var(--err); }
.panel-header-text { font-size: 13px; font-weight: bold; color: var(--accent); letter-spacing: 1px; flex: 1; }
.panel-controls { display: flex; gap: 4px; }
.ctrl-btn { width: 24px; height: 24px; border-radius: 4px; background: transparent; border: 1px solid var(--border); color: var(--text-main); cursor: pointer; font-size: 12px; display: flex; align-items: center; justify-content: center; }
.ctrl-btn:hover { background: var(--accent); color: #000; }

.panel-content { padding: 10px; flex: 1; overflow-y: auto; }
.panel-help { padding: 10px; font-size: 11px; color: #888; border-top: 1px solid var(--border); }
.panel-help code { background: rgba(255,255,255,0.05); padding: 1px 4px; border-radius: 3px; color: var(--accent-glow); font-size: 10px; }

.live-status { background: rgba(0,0,0,0.2); padding: 8px; border-radius: 6px; border-left: 3px solid var(--accent-glow); font-size: 11px; line-height: 1.4; margin-bottom: 10px; }
.live-status pre { white-space: pre-wrap; font-family: 'Consolas', monospace; color: var(--accent-glow); margin: 0; font-size: 10px; }

.lamp-btn { width: calc(100% - 20px); margin: 10px; padding: 12px; background: linear-gradient(135deg, #ffd700, #b8860b); color: #000; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 13px; }
.lamp-btn:hover { filter: brightness(1.1); }

/* Кнопки разворачивания панелей */
.expand-btn { position: absolute; top: 50%; transform: translateY(-50%); width: 24px; height: 60px; background: var(--bg-panel); border: 1px solid var(--border); color: var(--accent); cursor: pointer; font-size: 14px; display: none; align-items: center; justify-content: center; z-index: 100; transition: 0.2s; }
.expand-btn:hover { background: var(--accent); color: #000; }
.expand-btn.left { left: 0; border-radius: 0 6px 6px 0; }
.expand-btn.right { right: 0; border-radius: 6px 0 0 6px; }
.expand-btn.visible { display: flex; }

.screen-x { flex: 1; background: var(--bg-dark); display: flex; flex-direction: column; min-width: 0; }
.chat-area { flex: 1; padding: 15px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }

.message-wrapper { display: flex; flex-direction: column; max-width: 75%; }
.message-wrapper.user { align-self: center; align-items: center; }
.message-wrapper.dron { align-self: flex-start; }
.message-wrapper.genie { align-self: flex-end; }

.message { padding: 10px 14px; border-radius: 10px; line-height: 1.5; font-size: 14px; white-space: pre-wrap; word-wrap: break-word; }
.msg-user { background: var(--accent); color: #000; }
.msg-dron { background: var(--bg-panel); border: 1px solid var(--border); }
.msg-genie { background: linear-gradient(135deg, var(--bg-panel), #3a2060); border: 1px solid var(--accent); }
.msg-system { align-self: center; background: transparent; color: var(--accent-glow); font-size: 11px; border: 1px dashed var(--border); padding: 6px 12px; max-width: 100%; }

.msg-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; padding: 0 4px; font-size: 10px; color: #666; }
.msg-meta span { display: flex; align-items: center; gap: 3px; }
.meta-btn { background: transparent; border: 1px solid var(--border); color: #888; padding: 2px 6px; border-radius: 4px; cursor: pointer; font-size: 10px; }
.meta-btn:hover { color: var(--accent); border-color: var(--accent); }

.input-area { padding: 12px 15px; border-top: 1px solid var(--border); display: flex; gap: 8px; flex-shrink: 0; background: var(--bg-panel); }
.input-field { flex: 1; background: var(--bg-dark); border: 1px solid var(--border); color: var(--text-main); padding: 10px 12px; border-radius: 8px; outline: none; font-size: 13px; }
.input-field:focus { border-color: var(--accent); }
.send-btn { background: var(--accent); color: #000; border: none; padding: 0 18px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 14px; }
</style>
</head>
<body>

<div class="top-bar">
    <div class="app-icons">
        <div class="app-icon active" title="Чат">X</div>
        <div class="app-icon" title="VAN">V</div>
        <div class="app-icon" title="BANK">B</div>
        <div class="app-icon" title="Календарь">K</div>
        <div class="app-icon" title="Настройки" onclick="alert('Настройки системы')">⚙</div>
    </div>
    <button class="theme-toggle" onclick="toggleTheme()">🎨 Тема</button>
</div>

<div class="scene" id="scene">
    <!-- Кнопки разворачивания панелей -->
    <button class="expand-btn left" id="expandLeft" onclick="togglePanel('left')">▶</button>
    <button class="expand-btn right" id="expandRight" onclick="togglePanel('right')"></button>

    <div class="panel left" id="panelDron">
        <div class="panel-header" onclick="togglePanel('left')">
            <div class="status-dot online" id="dronDot"></div>
            <span class="panel-header-text">DRON</span>
            <div class="panel-controls">
                <button class="ctrl-btn" title="Микрофон" onclick="event.stopPropagation(); alert('Микрофон')">🎤</button>
                <button class="ctrl-btn" title="Динамик" onclick="event.stopPropagation(); alert('Динамик')">🔊</button>
                <button class="ctrl-btn" title="Настройки Дрона" onclick="event.stopPropagation(); alert('Настройки Дрона')">⚙</button>
            </div>
        </div>
        <div class="panel-content">
            <div class="live-status" id="dronStatus"><pre>Загрузка...</pre></div>
        </div>
        <div class="panel-help">
            <p><b>Команды:</b></p>
            <p><code>/сохрани [текст]</code></p>
            <p><code>/сжать</code></p>
            <p><code>статус дрона</code></p>
        </div>
    </div>

    <div class="screen-x">
        <div class="chat-area" id="chatArea"></div>
        <div class="input-area">
            <input type="text" class="input-field" id="userInput" placeholder="Введите команду или спросите..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button class="send-btn" onclick="sendMessage()">➤</button>
        </div>
    </div>

    <div class="panel right" id="panelGenie">
        <div class="panel-header" onclick="togglePanel('right')">
            <div class="status-dot online" id="genieDot"></div>
            <span class="panel-header-text">GENIE</span>
            <div class="panel-controls">
                <button class="ctrl-btn" title="Микрофон" onclick="event.stopPropagation(); alert('Микрофон')">🎤</button>
                <button class="ctrl-btn" title="Динамик" onclick="event.stopPropagation(); alert('Динамик')">🔊</button>
                <button class="ctrl-btn" title="Настройки Джинна" onclick="event.stopPropagation(); alert('Настройки Джинна')">⚙</button>
            </div>
        </div>
        <div class="panel-content">
            <div class="live-status"><pre>Статус: В ожидании<br>06_X_HUB: Чист</pre></div>
        </div>
        <button class="lamp-btn" onclick="summonGenie()">🪔 Потереть Лампу</button>
    </div>
</div>

<script>
let currentMode = 'x', chatHistory = [];

// Загрузка истории из localStorage при старте
window.onload = function() {
    const saved = localStorage.getItem('chatHistory');
    if (saved) {
        chatHistory = JSON.parse(saved);
        chatHistory.forEach(msg => {
            if (msg.role === 'user') addMessage(msg.content, 'user');
            else if (msg.role === 'assistant') addMessage(msg.content, 'dron');
        });
    }
};

function toggleTheme() { document.documentElement.classList.toggle('theme-genie'); }

function togglePanel(side) {
    const panel = side === 'left' ? document.getElementById('panelDron') : document.getElementById('panelGenie');
    const expandBtn = side === 'left' ? document.getElementById('expandLeft') : document.getElementById('expandRight');
    panel.classList.toggle('collapsed');
    expandBtn.classList.toggle('visible');
}

setInterval(async () => {
    try {
        const res = await fetch('/api/dron/status');
        const data = await res.json();
        document.getElementById('dronStatus').innerHTML = '<pre>' + data.status + '</pre>';
        document.getElementById('dronDot').className = 'status-dot online';
    } catch(e) {
        document.getElementById('dronDot').className = 'status-dot offline';
    }
}, 3000);

async function sendMessage() {
    const input = document.getElementById('userInput');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    chatHistory.push({role: 'user', content: text});
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    input.value = '';

    const thinkingId = addMessage('Анализирую...', 'dron');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, mode: currentMode, history: chatHistory })
        });
        const data = await response.json();
        document.getElementById(thinkingId).remove();

        let type = 'dron';
        if (data.source && data.source.includes('GENIE')) type = 'genie';
        else if (data.source && data.source.includes('ERROR')) type = 'system';

        addMessage(data.response, type, {tokens: data.tokens || 0, time: data.time || '0.0'});
        chatHistory.push({role: 'assistant', content: data.response});
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));

        if (data.action === 'clear_chat') {
            setTimeout(() => {
                document.getElementById('chatArea').innerHTML = '';
                chatHistory = [];
                localStorage.removeItem('chatHistory');
                addMessage('✨ Чат очищен. Контекст сжат.', 'system');
            }, 1500);
        }
    } catch (error) {
        document.getElementById(thinkingId).remove();
        addMessage('Сбой связи с Дроном.', 'system');
    }
}

async function summonGenie() {
    try {
        const res = await fetch('/api/genie/summon', { method: 'POST' });
        const data = await res.json();
        addMessage('✨ ' + data.ritual_phrase, 'genie');
    } catch (e) {
        addMessage('Лампа не отвечает...', 'system');
    }
}

function addMessage(text, type, meta = {}) {
    const chat = document.getElementById('chatArea');
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper ' + type;

    const msg = document.createElement('div');
    msg.className = 'message msg-' + type;
    msg.innerText = text;
    wrapper.appendChild(msg);

    if (type !== 'system') {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'msg-meta';
        metaDiv.innerHTML = `
            <span>⚡ ${meta.tokens || 0} ток</span>
            <span>⏱ ${meta.time || '0.0'}с</span>
            <button class="meta-btn" onclick="copyMsg(this)"></button>
            <button class="meta-btn" onclick="replyMsg(this)">↩</button>
        `;
        wrapper.appendChild(metaDiv);
    }

    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
    return wrapper.id = 'msg-' + Date.now();
}

function copyMsg(btn) {
    const text = btn.closest('.message-wrapper').querySelector('.message').innerText;
    navigator.clipboard.writeText(text);
    btn.innerText = '✓';
    setTimeout(() => btn.innerText = '', 1000);
}

function replyMsg(btn) {
    const text = btn.closest('.message-wrapper').querySelector('.message').innerText;
    document.getElementById('userInput').value = '> ' + text.substring(0, 50) + '...';
    document.getElementById('userInput').focus();
}
</script>
</body>
</html>"""

with open("frontend/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("✅ frontend/index.html обновлён")