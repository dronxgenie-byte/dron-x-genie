document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initAppSwitcher();
    initChat();
    initMainControls();
    logRoute('X-Router запущен');
});

function initClock() {
    function update() {
        document.getElementById('clock').textContent = new Date().toLocaleTimeString('ru-RU');
    }
    update();
    setInterval(update, 1000);
}

function initAppSwitcher() {
    document.querySelectorAll('.app-icon').forEach(icon => {
        icon.addEventListener('click', () => {
            document.querySelectorAll('.app-icon').forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.app-window').forEach(w => w.classList.remove('active'));
            icon.classList.add('active');
            document.getElementById(icon.dataset.app + '-window').classList.add('active');
        });
    });
}

let currentAgent = 'dron';

function initChat() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    
    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    document.querySelectorAll('.agent-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.agent-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentAgent = btn.dataset.agent;
            
            // Логируем переключение
            const agentName = currentAgent === 'dron' ? 'Дрон' : currentAgent === 'jin' ? 'Джин' : 'X-Router';
            logRoute('Переключен на ' + agentName);
            document.getElementById('x-active-agent').textContent = agentName;
        });
    });
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    
    addMessage(message, 'user');
    input.value = '';
    
    logRoute('Запрос к ' + (currentAgent === 'dron' ? 'Дрон' : currentAgent === 'jin' ? 'Джин' : 'X'));
    
    try {
        const response = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, model: currentAgent })
        });
        
        const data = await response.json();
        addMessage(data.reply, currentAgent);
        logRoute('Ответ получен от ' + (currentAgent === 'dron' ? 'Дрон' : currentAgent === 'jin' ? 'Джин' : 'X'));
    } catch (error) {
        addMessage('Ошибка: ' + error.message, 'system');
        logRoute('Ошибка: ' + error.message);
    }
}

function addMessage(text, sender) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ' + sender;
    const agentName = sender === 'dron' ? '🤖 Дрон' : sender === 'jin' ? '☁️ Джин' : sender === 'x' ? '❌ X-Router' : sender === 'user' ? 'Вы' : 'Система';
    msgDiv.innerHTML = '<strong>' + agentName + ':</strong> ' + text;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function initMainControls() {
    document.getElementById('mic-btn').addEventListener('click', () => alert('🎤 Голосовой ввод'));
    document.getElementById('speak-btn').addEventListener('click', () => alert('🔊 Озвучивание'));
    document.getElementById('listen-btn').addEventListener('click', () => alert(' Прослушивание'));
}

// Открытие/закрытие панелей агентов
function openPanel(agent) {
    document.getElementById(agent + '-panel').classList.add('active');
}

function closePanel(agent) {
    document.getElementById(agent + '-panel').classList.remove('active');
}

// Быстрые действия X-Router
function switchAgent(agent) {
    document.querySelectorAll('.agent-btn').forEach(b => b.classList.remove('active'));
    const btn = document.querySelector('.agent-btn[data-agent="' + agent + '"]');
    if (btn) {
        btn.classList.add('active');
        currentAgent = agent;
        logRoute('Быстрое переключение на ' + (agent === 'dron' ? 'Дрон' : 'Джин'));
    }
    closePanel('x');
}

function updateMemory() {
    logRoute('🔄 Обновление векторной базы...');
    fetch('http://localhost:8000/update-memory', { method: 'POST' })
        .then(() => {
            logRoute('✅ Память обновлена');
            alert('✅ Память Obsidian обновлена');
        })
        .catch(err => {
            logRoute('❌ Ошибка обновления: ' + err.message);
            alert(' Ошибка: ' + err.message);
        });
}

function clearChat() {
    document.getElementById('chat-messages').innerHTML = '';
    logRoute('🗑️ Чат очищен');
}

// Логирование маршрутизации
function logRoute(text) {
    const logContainer = document.getElementById('route-log');
    if (!logContainer) return;
    
    const time = new Date().toLocaleTimeString('ru-RU');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = '<span class="log-time">' + time + '</span> <span class="log-text">' + text + '</span>';
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Делаем функции глобальными
window.openPanel = openPanel;
window.closePanel = closePanel;
window.switchAgent = switchAgent;
window.updateMemory = updateMemory;
window.clearChat = clearChat;
