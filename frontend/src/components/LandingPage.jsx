import React, { useState, useEffect } from 'react';

export default function LandingPage() {
  const [status, setStatus] = useState({
    dron: 'checking',
    genie: 'checking',
    agent_x: 'checking',
  });

  useEffect(() => {
    const checkStatus = async () => {
      const results = { dron: 'offline', genie: 'offline', agent_x: 'offline' };

      try {
        const r1 = await fetch('/api/health');
        if (r1.ok) results.dron = 'ok';
      } catch { /* keep offline */ }

      try {
        const r2 = await fetch('/api/genie/status');
        if (r2.ok) results.genie = 'ok';
      } catch { /* keep offline */ }

      try {
        const r3 = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: 'status', agent: 'x' }),
        });
        if (r3.ok) results.agent_x = 'ok';
      } catch { /* keep offline */ }

      setStatus(results);
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const statusLabel = (s) =>
    s === 'ok' ? 'ОНЛАЙН' : s === 'checking' ? 'ПРОВЕРКА...' : 'ОФЛАЙН';

  return (
    <div className="relative h-screen w-full overflow-hidden bg-[#050a14] text-white font-orbitron select-none">
      {/* Cosmic background */}
      <div className="absolute inset-0 z-[-10] opacity-30">
        <div className="absolute top-0 left-0 w-full h-full bg-[url('https://www.transparenttextures.com/patterns/stardust.png')]"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-purple-600/20 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-1/3 right-1/5 w-64 h-64 bg-green-500/10 rounded-full blur-[80px] animate-pulse" style={{ animationDelay: '4s' }}></div>
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-gradient-to-br from-cyan-400 to-blue-900 rounded-xl flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.6)] rotate-6">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight text-white drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]">
              DRON X<span className="text-cyan-400">GENIE</span>
            </h1>
            <p className="text-cyan-300/80 text-sm tracking-widest font-mono uppercase letter-spacing-widest">
              Космический Корабль Анисимовых • Бортовой Компьютер
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6 text-xs font-mono text-gray-400">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full animate-pulse ${status.dron === 'ok' ? 'bg-green-400' : 'bg-gray-600'}`}></span>
            <span>VITE : 5173</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full animate-pulse ${status.agent_x === 'ok' ? 'bg-green-400' : 'bg-gray-600'}`}></span>
            <span>API : 8000</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full animate-pulse ${status.genie === 'ok' ? 'bg-green-400' : 'bg-gray-600'}`}></span>
            <span>CLOUDFLare TUNNEL</span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 flex flex-col items-center justify-center h-full px-8">
        <div className="max-w-4xl w-full text-center space-y-12">
          <div className="relative inline-block">
            <div className="absolute -inset-1 bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 rounded-2xl blur opacity-30 animate-pulse"></div>
            <div className="relative p-2 bg-[#050a14] rounded-2xl border border-cyan-900/50 shadow-[0_0_40px_rgba(6,182,212,0.2)]">
              <h2 className="text-5xl font-black tracking-tighter mb-4 drop-shadow-[0_0_20px_rgba(6,182,212,0.5)]">
                КАПИТАНСКИЙ МОСТ
              </h2>
              <p className="text-lg text-cyan-300/90 max-w-xl mx-auto leading-relaxed">
                Система управления космическим кораблем Анисимовых. <br />
                Владелец: Андрей Анисимов (ANANISIM) • Валюта: Анисы (₳)
              </p>
            </div>
          </div>

          {/* System status grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[ 
              { key: 'dron', label: 'ДРОН', icon: '🤖', color: 'cyan', status: status.dron },
              { key: 'genie', label: 'ДЖИННИ', icon: '✨', color: 'purple', status: status.genie },
              { key: 'agent_x', label: 'АГЕНТ X', icon: '👽', color: 'green', status: status.agent_x },
            ].map((sys) => (
              <div key={sys.key} className={`group relative p-6 rounded-2xl border bg-gray-900/40 backdrop-blur-sm transition-all hover:border-${sys.color}-500/50`}>
                <div className={`absolute top-4 right-4 w-2 h-2 rounded-full ${sys.status === 'ok' ? 'bg-${sys.color}-400 animate-pulse' : 'bg-gray-700'}`}></div>
                <div className={`text-${sys.color}-400 text-4xl mb-3 group-hover:scale-110 transition-transform`}>{sys.icon}</div>
                <h3 className="text-xl font-bold text-white mb-1">{sys.label}</h3>
                <p className={`text-xs font-mono tracking-widest ${sys.status === 'ok' ? 'text-green-400' : sys.status === 'checking' ? 'text-yellow-500' : 'text-red-500'}`}>
                  {statusLabel(sys.status)}
                </p>
              </div>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              className="px-10 py-4 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl shadow-[0_0_25px_rgba(6,182,212,0.4)] transition-all tracking-widest text-lg"
              onClick={() => { window.dispatchEvent(new CustomEvent('enter-cockpit')); }}
            >
              ВОЙТИ В КАБИНУ
            </button>
            <button
              className="px-10 py-4 bg-transparent border-2 border-cyan-600 hover:bg-cyan-600 text-cyan-400 font-bold rounded-xl transition-all tracking-widest text-lg"
            >
              СТАТУС СИСТЕМ
            </button>
          </div>

          <div className="mt-8 text-xs text-gray-500 font-mono">
            DRON X GENIE OS v0.2.0 • dronxgenie.com • Через Cloudflare Tunnel
          </div>
        </div>
      </main>

      {/* Floating particles */}
      <div className="absolute inset-0 z-[-5] pointer-events-none overflow-hidden">
        {[...Array(20)].map((_, i) => (
          <div
            key={i}
            className="absolute w-[2px] h-[2px] bg-white rounded-full animate-float"
          />
        ))}
      </div>
    </div>
  );
}
