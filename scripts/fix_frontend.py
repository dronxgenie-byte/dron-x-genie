html = """<!DOCTYPE html>
<html lang="ru" class="theme-neon">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DRON × GENIE</title>
    <style>
        :root { --bg-dark: #0f0f13; --bg-panel: #1a1a24; --text-main: #e0e0e0; --accent: #8a2be2; --accent-glow: #00f3ff; --border: #2a2a3a; }
        .theme-genie { --bg-dark: #1a0f24; --bg-panel: #2d1b4e; --text-main: #fff8e7; --accent: #ffd700; --accent-glow: #40e0d0; --border: #4a3b6a; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background: var(--bg-dark); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        .top-bar { height: 50px; background: var(--bg-panel); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
        .mode-btn { background: transparent; border: 1px solid var(--border); color: var(--text-main); padding: 5px 15px; border-radius: 20px; cursor: pointer; margin-right: 5px; }
        .mode-btn.active { background: var(--accent); color: #000; font-weight: bold; }
        .theme-toggle { background: none; border: 1px solid var(--accent); color: var(--accent); padding: 5px 15px; border-radius: 20px; cursor: pointer; }
        .scene { display: grid; grid-template-columns: 280px 1fr 280px; flex: 1; overflow: hidden; }
        .panel { background: var(--bg-panel); border-right: 1px solid var(--border); padding: 15px; overflow-y: auto; }
        .panel.right { border-right: none; border-left: 1px solid var(--border); }
        .panel-header { font-size: 14px; font-weight: bold; color: var(--accent); margin-bottom: 15px; }
        .live-status { background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; border-left: 3px solid var(--accent-glow); font-size: 12px; margin-bottom: 15px; }
        .live-status pre { white-space: pre-wrap; font-family: monospace; color: var(--accent-glow); margin: 0; }
        .screen-x { background: var(--bg-dark); display: flex; flex-direction: column; }
        .chat-area { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { max-width: 85%; padding: 12px 18px; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; }
        .msg-user { align-self: flex-end; background: var(--accent); color: #000; }
        .msg-dron { align-self: flex-start; background: var(--bg-panel); border: 1px solid var(--border); }
        .msg-genie { align-self: flex-start; background: linear-gradient(135deg, var(--bg-panel), #3a2060); border: 1px solid var(--accent); }
        .msg-system { align-self: center; background: transparent; color: var(--accent-glow); font-size: 12px; border: 1px dashed var(--border); }
        .input-area { padding: 20px; border-top: 1px solid var(--border); display: flex; gap: 10px; }
        .input-field { flex: 1; background: var(--bg-panel); border: 1px solid var(--border); color: var(--text-main); padding: 12px; border-radius: 8px; outline: none; }
        .send-btn { background: var(--accent); color: #000; border: none; padding: 0 25px; border-radius: 8px; cursor: pointer; font-weight: bold; }
        .lamp-btn { width: 100%; padding: 15px; background: linear-gradient(135deg, #ffd700, #b8860b); color: #000; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; margin-top: auto; }
    </style>
</head>
<body>
    <div class="top-bar">
        <div>
            <button class="mode-btn active" onclick="setMode('dron')">[DRON]</button>
            <button class="mode-btn" onclick="setMode('x')">[X]</button>
            <button class="mode-btn" onclick="setMode('genie')">[GENIE]</button>
        </div>
        <button class="theme-toggle" onclick="toggleTheme()">🎨 Тема</button>
    </div>
    <div class="scene">
        <div class="panel left">
            <div class="panel-header">🧔 DRON</div>
            <div class="live-status" id="dronStatus"><pre>Загрузка...</pre></div>
            <div style="font-size:12px; color:#888;">
                <p>💡 <b>Слэш-команды:</b></p>
                <p><code>/сохрани [текст]</code></p>
                <p><code>/сжать</code></p>
                <p><code>статус дрона</code></p>
            </div>
        </div>
        <div class="screen-x">
            <div class="chat-area" id="chatArea">
                <div class="message msg-dron">Система ANANISIM OS запущена. Экран X активен. Ожидаю приказаний, Босс.</div>
            </div>
            <div class="input-area">
                <input type="text" class="input-field" id="userInput" placeholder="Введите команду или спросите..." onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="send-btn" onclick="sendMessage()">➤</button>
            </div>
        </div>
        <div class="panel right">
            <div class="panel-header"> GENIE</div>
            <div class="live-status"><pre>Статус: В ожидании<br>06_X_HUB: Чист</pre></div>
            <button class="lamp-btn" onclick="summonGenie()">🪔 Потереть Лампу</button>
        </div>
    </div>
    <script>
        let currentMode = 'x', chatHistory = [];
        function setMode(mode) { currentMode = mode; document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active')); event.target.classList.add('active'); }
        function toggleTheme() { document.documentElement.classList.toggle('theme-genie'); }
        setInterval(async () => { try { const res = await fetch('/api/dron/status'); const data = await res.json(); document.getElementById('dronStatus').innerHTML = '<pre>' + data.status + '</pre>'; } catch(e) {} }, 3000);
        async function sendMessage() { const input = document.getElementById('userInput'); const text = input.value.trim(); if (!text) return; addMessage(text, 'user'); chatHistory.push({role: 'user', content: text}); input.value = ''; const thinkingId = addMessage('Анализирую...', 'dron'); try { const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: text, mode: currentMode, history: chatHistory }) }); const data = await response.json(); document.getElementById(thinkingId).remove(); let cls = data.source.includes('GENIE') ? 'msg-genie' : (data.source.includes('ERROR') ? 'msg-system' : 'msg-dron'); addMessage(data.response, cls.replace('msg-', '')); chatHistory.push({role: 'assistant', content: data.response}); if (data.action === 'clear_chat') { setTimeout(() => { document.getElementById('chatArea').innerHTML = ''; chatHistory = []; addMessage('✨ Чат очищен. Контекст сжат.', 'system'); }, 1500); } } catch (error) { document.getElementById(thinkingId).innerText = 'Сбой связи.'; document.getElementById(thinkingId).className = 'message msg-system'; } }
        async function summonGenie() { const btn = document.querySelector('.lamp-btn'); btn.innerText = '✨ Призываю...'; try { const res = await fetch('/api/genie/summon', { method: 'POST' }); const data = await res.json(); addMessage('✨ ' + data.ritual_phrase, 'genie'); } catch (e) { addMessage('Лампа не отвечает...', 'system'); } finally { btn.innerText = '🪔 Потереть Лампу'; } }
        function addMessage(text, type) { const chat = document.getElementById('chatArea'); const div = document.createElement('div'); div.className = 'message msg-' + type; div.id = 'msg-' + Date.now(); div.innerText = text; chat.appendChild(div); chat.scrollTop = chat.scrollHeight; return div.id; }
    </script>
</body>
</html>"""

with open("frontend/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("✅ frontend/index.html записан с кириллицей")