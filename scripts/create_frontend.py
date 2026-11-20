html = """<!DOCTYPE html>
<html lang="ru" class="theme-neon">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DRON X GENIE</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        
        /* Верхние кнопки */
        .top-controls {
            display: flex;
            justify-content: center;
            gap: 15px;
            padding: 15px;
            background: rgba(20, 20, 30, 0.8);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        
        .top-btn {
            padding: 10px 20px;
            background: linear-gradient(135deg, #00ff88, #00cc66);
            border: none;
            border-radius: 8px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .top-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 0 15px #00ff88;
        }
        
        .top-btn.active {
            background: linear-gradient(135deg, #ff8800, #ff6600);
        }
        
        /* Основная область */
        .main-area {
            flex: 1;
            display: flex;
            gap: 20px;
            position: relative;
            overflow: hidden;
        }
        
        /* Выдвижные панели */
        .side-panel {
            width: 400px;
            background: rgba(20, 20, 30, 0.9);
            border: 2px solid #00ff88;
            border-radius: 15px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            transition: all 0.3s;
        }
        
        .side-panel.collapsed {
            width: 60px;
            overflow: hidden;
        }
        
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #00ff88;
        }
        
        .panel-title {
            font-size: 1.5em;
            color: #00ff88;
            text-shadow: 0 0 10px #00ff88;
        }
        
        .toggle-btn {
            background: rgba(0, 255, 136, 0.2);
            border: 1px solid #00ff88;
            color: #00ff88;
            padding: 5px 10px;
            border-radius: 6px;
            cursor: pointer;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 15px;
        }
        
        .message-wrapper {
            margin-bottom: 15px;
            display: flex;
            flex-direction: column;
        }
        
        .message {
            padding: 12px 18px;
            border-radius: 12px;
            max-width: 90%;
            word-wrap: break-word;
        }
        
        .user-message {
            background: linear-gradient(135deg, #0066ff, #0044cc);
            align-self: flex-end;
            color: white;
        }
        
        .agent-message {
            background: linear-gradient(135deg, #00cc66, #009944);
            align-self: flex-start;
            color: white;
        }
        
        .message-actions {
            display: flex;
            gap: 8px;
            margin-top: 5px;
            font-size: 0.85em;
        }
        
        .message-actions button {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ccc;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
        }
        
        .message-actions button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        /* Центральная область */
        .center-area {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .status {
            text-align: center;
            padding: 10px;
            color: #888;
            font-size: 0.9em;
        }
        
        /* Поле ввода */
        .input-container {
            display: flex;
            gap: 10px;
            padding: 15px;
            background: rgba(20, 20, 30, 0.8);
            border-radius: 12px;
            margin-top: 20px;
        }
        
        #userInput {
            flex: 1;
            padding: 15px;
            background: rgba(10, 10, 20, 0.8);
            border: 2px solid #00ff88;
            border-radius: 10px;
            color: white;
            font-size: 1.1em;
            outline: none;
        }
        
        #userInput:focus {
            box-shadow: 0 0 15px #00ff88;
        }
        
        #sendBtn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #00ff88, #00cc66);
            border: none;
            border-radius: 10px;
            color: #000;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
        }
        
        #sendBtn:hover {
            transform: scale(1.05);
            box-shadow: 0 0 20px #00ff88;
        }
        
        #sendBtn:disabled {
            background: #666;
            cursor: not-allowed;
        }
        
        /* Голосовые кнопки */
        #voice-controls {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
            z-index: 9999;
        }
        
        .voice-btn {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        .voice-btn:hover {
            transform: scale(1.1);
        }
        
        #mic-btn { background: #ff4444; }
        #mic-btn.active {
            background: #44ff44;
            animation: pulse 1.5s infinite;
        }
        
        #speaker-btn { background: #4444ff; }
        #speaker-btn.muted { background: #888; }
        
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(68, 255, 68, 0.7); }
            50% { box-shadow: 0 0 0 15px rgba(68, 255, 68, 0); }
        }
        
        .voice-status {
            position: fixed;
            bottom: 90px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: #00ff88;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 0.9em;
            display: none;
            z-index: 9999;
        }
        
        .voice-status.visible { display: block; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Верхние кнопки -->
        <div class="top-controls">
            <button class="top-btn" onclick="switchAgent('dron')">🤖 ДРОН</button>
            <button class="top-btn" onclick="switchAgent('genie')">🪔 ДЖИНН</button>
            <button class="top-btn" onclick="toggleVoice()">🎤 ГОЛОС</button>
        </div>
        
        <!-- Основная область -->
        <div class="main-area">
            <!-- Левая панель: Дрон -->
            <div class="side-panel" id="dron-panel">
                <div class="panel-header">
                    <div class="panel-title">🤖 ДРОН</div>
                    <button class="toggle-btn" onclick="togglePanel('dron')">◀</button>
                </div>
                <div class="chat-container" id="dron-chat"></div>
            </div>
            
            <!-- Центр -->
            <div class="center-area">
                <div class="status" id="status">Готов к работе</div>
            </div>
            
            <!-- Правая панель: Джинн -->
            <div class="side-panel" id="genie-panel">
                <div class="panel-header">
                    <div class="panel-title">🪔 ДЖИНН</div>
                    <button class="toggle-btn" onclick="togglePanel('genie')">▶</button>
                </div>
                <div class="chat-container" id="genie-chat"></div>
            </div>
        </div>
        
        <!-- Поле ввода -->
        <div class="input-container">
            <input type="text" id="userInput" placeholder="Напиши сообщение..." />
            <button id="sendBtn">Отправить</button>
        </div>
    </div>
    
    <!-- Голосовые кнопки -->
    <div id="voice-controls">
        <button id="mic-btn" class="voice-btn" title="Микрофон"></button>
        <button id="speaker-btn" class="voice-btn" title="Динамик">🔊</button>
    </div>
    
    <div id="voice-status" class="voice-status"></div>

    <script>
        let currentAgent = 'dron';
        let ws = null;
        let audioContext = null;
        let micStream = null;
        let isMicOn = false;
        let isSpeakerOn = true;
        let playQueue = [];
        let isPlaying = false;

        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const status = document.getElementById('status');
        const micBtn = document.getElementById('mic-btn');
        const speakerBtn = document.getElementById('speaker-btn');
        const voiceStatus = document.getElementById('voice-status');

        function showStatus(text) {
            voiceStatus.textContent = text;
            voiceStatus.classList.add('visible');
            setTimeout(() => voiceStatus.classList.remove('visible'), 3000);
        }

        function switchAgent(agent) {
            currentAgent = agent;
            document.querySelectorAll('.top-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            status.textContent = `Активен: ${agent === 'dron' ? 'ДРОН' : 'ДЖИНН'}`;
        }

        function togglePanel(panel) {
            const panelEl = document.getElementById(`${panel}-panel`);
            panelEl.classList.toggle('collapsed');
        }

        function addMessage(text, isUser, agent) {
            const chatContainer = document.getElementById(`${agent}-chat`);
            const wrapper = document.createElement('div');
            wrapper.className = 'message-wrapper';
            
            const msg = document.createElement('div');
            msg.className = `message ${isUser ? 'user-message' : 'agent-message'}`;
            msg.textContent = text;
            wrapper.appendChild(msg);
            
            if (!isUser) {
                const actions = document.createElement('div');
                actions.className = 'message-actions';
                actions.innerHTML = `
                    <button onclick="copyMsg(this, '${agent}')">📋 Копировать</button>
                    <button onclick="replyMsg(this)">↩ Ответить</button>
                `;
                wrapper.appendChild(actions);
            }
            
            chatContainer.appendChild(wrapper);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function copyMsg(btn, agent) {
            const text = btn.closest('.message-wrapper').querySelector('.message').textContent;
            navigator.clipboard.writeText(text);
            btn.textContent = '✅ Скопировано';
            setTimeout(() => btn.textContent = '📋 Копировать', 2000);
        }

        function replyMsg(btn) {
            const text = btn.closest('.message-wrapper').querySelector('.message').textContent;
            userInput.value = text;
            userInput.focus();
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            
            addMessage(text, true, currentAgent);
            userInput.value = '';
            sendBtn.disabled = true;
            status.textContent = '✨ Думаю...';
            
            try {
                const response = await fetch(`/api/${currentAgent}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                
                const data = await response.json();
                addMessage(data.response || 'Ошибка', false, currentAgent);
                status.textContent = `⚡ ${data.tokens || 0} ток | ⏱ ${data.time || 0}с`;
            } catch (e) {
                addMessage(`Ошибка: ${e}`, false, currentAgent);
                status.textContent = 'Ошибка соединения';
            }
            
            sendBtn.disabled = false;
        }

        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        function toggleVoice() {
            if (isMicOn) stopMicrophone();
            else startMicrophone();
        }

        function initAudioContext() {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
            }
        }

        function connectWebSocket() {
            if (ws && ws.readyState === WebSocket.OPEN) return;
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/voice-agent`);
            
            ws.onopen = () => {
                console.log('✅ Подключено к голосовому агенту');
                showStatus('Голосовой агент подключён');
            };
            
            ws.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'response.output_audio.delta' && isSpeakerOn) {
                        if (data.delta) {
                            const audioBuffer = await base64ToAudioBuffer(data.delta);
                            playQueue.push(audioBuffer);
                            if (!isPlaying) playNext();
                        }
                    }
                    
                    if (data.type === 'response.output_text.delta') {
                        console.log('🗣️ Джинн:', data.delta);
                    }
                } catch (e) {
                    console.error('Ошибка обработки:', e);
                }
            };
            
            ws.onclose = () => {
                console.log('🔌 Отключено');
                showStatus('Переподключение...');
                setTimeout(connectWebSocket, 3000);
            };
        }

        async function base64ToAudioBuffer(base64) {
            const binary = atob(base64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            return await audioContext.decodeAudioData(bytes.buffer.slice(0));
        }

        async function playNext() {
            if (playQueue.length === 0) {
                isPlaying = false;
                return;
            }
            isPlaying = true;
            const audioBuffer = playQueue.shift();
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContext.destination);
            source.onended = playNext;
            source.start();
        }

        async function startMicrophone() {
            try {
                initAudioContext();
                micStream = await navigator.mediaDevices.getUserMedia({ 
                    audio: { 
                        sampleRate: 24000,
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true
                    } 
                });
                
                const source = audioContext.createMediaStreamSource(micStream);
                const processor = audioContext.createScriptProcessor(4096, 1, 1);
                
                processor.onaudioprocess = (e) => {
                    if (isMicOn && ws && ws.readyState === WebSocket.OPEN) {
                        const inputData = e.inputBuffer.getChannelData(0);
                        const pcmData = new Int16Array(inputData.length);
                        for (let i = 0; i < inputData.length; i++) {
                            const s = Math.max(-1, Math.min(1, inputData[i]));
                            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        }
                        const base64 = arrayBufferToBase64(pcmData.buffer);
                        ws.send(JSON.stringify({
                            type: 'input_audio_buffer.append',
                            audio: base64
                        }));
                    }
                };
                
                source.connect(processor);
                processor.connect(audioContext.destination);
                
                isMicOn = true;
                micBtn.classList.add('active');
                showStatus('🎤 Микрофон включён');
            } catch (e) {
                console.error('Ошибка микрофона:', e);
                alert('Не удалось получить доступ к микрофону');
            }
        }

        function stopMicrophone() {
            isMicOn = false;
            if (micStream) {
                micStream.getTracks().forEach(track => track.stop());
                micStream = null;
            }
            micBtn.classList.remove('active');
            showStatus('🔇 Микрофон выключен');
        }

        function arrayBufferToBase64(buffer) {
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return btoa(binary);
        }

        micBtn.addEventListener('click', () => {
            if (isMicOn) stopMicrophone();
            else startMicrophone();
        });

        speakerBtn.addEventListener('click', () => {
            isSpeakerOn = !isSpeakerOn;
            speakerBtn.classList.toggle('muted', !isSpeakerOn);
            showStatus(isSpeakerOn ? '🔊 Динамик включён' : '🔇 Динамик выключен');
        });

        connectWebSocket();
    </script>
</body>
</html>"""

with open("frontend/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ frontend/index.html обновлён")