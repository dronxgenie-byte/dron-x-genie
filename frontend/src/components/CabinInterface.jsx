import React, { useState, useEffect } from 'react';
import { Shield, Power, Wifi, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function CabinInterface({ onExit, setActiveAgent, activeAgent, nodMode, setNodMode }) {
  const [status, setStatus] = useState({ dron: 'checking', genie: 'checking', agent_x: 'checking' });
  const [pinVerified, setPinVerified] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [pinError, setPinError] = useState(false);

  // --- PIN protection via localStorage ---
  const STORED_PIN_HASH = localStorage.getItem('dronx_pin_hash');

  useEffect(() => {
    // First check: is PIN already set?
    if (!STORED_PIN_HASH) {
      // No PIN yet — ask to create one
      setPinVerified(false);
      return;
    }
    // PIN exists — require verification
    setPinVerified(false);
  }, [STORED_PIN_HASH]);

  // --- Real-time status polling ---
  useEffect(() => {
    if (!pinVerified) return;

    const interval = setInterval(checkStatus, 15000);
    checkStatus();
    return () => clearInterval(interval);
  }, [pinVerified]);

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

  const handlePinSubmit = (e) => {
    e.preventDefault();
    if (!STORED_PIN_HASH) {
      // Creating first PIN — simple hash (store as-is for demo; production should use real hash)
      localStorage.setItem('dronx_pin_hash', pinInput);
      setPinVerified(true);
      setPinError(false);
      setPinInput('');
    } else {
      // Verifying existing PIN
      if (pinInput === STORED_PIN_HASH) {
        setPinVerified(true);
        setPinError(false);
        setPinInput('');
      } else {
        setPinError(true);
      }
    }
  };

  const statusLabel = (s) =>
    s === 'ok' ? 'ОНЛАЙН' : s === 'checking' ? 'ПРОВЕРКА...' : 'ОФЛАЙН';

  const statusColor = (s) =>
    s === 'ok' ? 'text-green-400' : s === 'checking' ? 'text-yellow-500' : 'text-red-500';

  const sysStatus = [
    { key: 'dron', label: 'ДРОН', icon: '🤖', color: 'cyan', status: status.dron },
    { key: 'genie', label: 'ДЖИННИ', icon: '✨', color: 'purple', status: status.genie },
    { key: 'agent_x', label: 'АГЕНТ X', icon: '👽', color: 'green', status: status.agent_x },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] bg-black text-white font-orbitron select-none flex flex-col"
    >
      {/* Header */}
      <header className="z-20 flex items-center justify-between px-8 py-4 border-b border-gray-800 bg-black/80 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-blue-900 rounded flex items-center justify-center">
            <Shield size={24} strokeWidth={2} />
          </div>
          <h1 className="text-xl font-black tracking-tight text-white">КАБИНА КОРАБЛЯ</h1>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={onExit}
            className="px-4 py-2 bg-red-900/30 border border-red-600 text-red-300 rounded-lg hover:bg-red-900 transition-colors text-sm font-bold"
          >
            <Power size={16} /> ВЫХОД
          </button>
        </div>
      </header>

      {/* PIN screen */}
      {!pinVerified && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="absolute inset-0 z-[110] bg-black/95 flex flex-col items-center justify-center"
        >
          <div className="max-w-md w-full p-8 rounded-2xl border border-gray-700 bg-gray-900/80 backdrop-blur-md shadow-2xl text-center">
            {!STORED_PIN_HASH ? (
              <>
                <Shield className="w-16 h-16 text-cyan-400 mx-auto mb-4" strokeWidth={2} />
                <h2 className="text-2xl font-bold text-white mb-2">Создайте PIN-код кабины</h2>
                <p className="text-gray-400 text-sm mb-6">
                  Придумайте код доступа к кабине корабля. Он сохранится в этом браузере.
                </p>
                <form onSubmit={handlePinSubmit} className="flex flex-col gap-3">
                  <input
                    type="password"
                    value={pinInput}
                    onChange={(e) => setPinInput(e.target.value)}
                    placeholder="Придумайте PIN (минимум 4 символа)"
                    className="px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 text-lg"
                    minLength={4}
                    required
                  />
                  <button
                    type="submit"
                    className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg transition-colors"
                  >
                    УСТАНОВИТЬ
                  </button>
                </form>
              </>
            ) : (
              <>
                <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" strokeWidth={2} />
                <h2 className="text-2xl font-bold text-white mb-2">Введите PIN-код</h2>
                <p className="text-gray-400 text-sm mb-6">Требуется доступ к кабине корабля.</p>
                {pinError && (
                  <p className="text-red-400 text-sm mb-4 animate-pulse">Неверный PIN-код.</p>
                )}
                <form onSubmit={handlePinSubmit} className="flex flex-col gap-3">
                  <input
                    type="password"
                    value={pinInput}
                    onChange={(e) => setPinInput(e.target.value)}
                    placeholder="PIN-код"
                    className="px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-cyan-500 text-lg"
                    required
                  />
                  <button
                    type="submit"
                    className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-lg transition-colors"
                  >
                    ВОЙТИ
                  </button>
                </form>
              </>
            )}
          </div>
        </motion.div>
      )}

      {/* Cabin content */}
      {pinVerified && (
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Background grid */}
          <div className="absolute inset-0 z-[-10] opacity-10 pointer-events-none">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e3a8a_1px,transparent_1px),linear-gradient(to_bottom,#1e3a8a_1px,transparent_1px)] bg-[size:40px_40px]"></div>
          </div>

          <div className="flex-1 overflow-y-auto px-8 py-6 space-y-8">
            {/* Welcome */}
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.4)] mb-4">
                <CheckCircle size={32} strokeWidth={2} />
              </div>
              <h2 className="text-3xl font-black text-white tracking-tight">Добро пожаловать, Капитан</h2>
              <p className="text-cyan-400 text-sm tracking-widest mt-2">
                Кабина загружена. Системы в норме.
              </p>
            </div>

            {/* Status grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {sysStatus.map((sys) => (
                <div key={sys.key} className={`p-6 rounded-2xl border bg-gray-900/40 backdrop-blur-sm group hover:border-${sys.color}-500/40 transition-colors`}>
                  <div className={`absolute top-4 right-4 w-2.5 h-2.5 rounded-full ${sys.status === 'ok' ? 'bg-green-400 animate-pulse' : 'bg-gray-700'}`}></div>
                  <div className={`text-${sys.color}-400 text-4xl mb-3`}>{sys.icon}</div>
                  <h3 className="text-lg font-bold text-white mb-1">{sys.label}</h3>
                  <p className={`text-xs font-mono tracking-widest ${statusColor(sys.status)}`}>
                    {statusLabel(sys.status)}
                  </p>
                </div>
              ))}
            </div>

            {/* Controls */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="p-6 rounded-2xl border border-gray-700 bg-gray-900/40">
                <h3 className="text-white font-bold mb-4 flex items-center gap-2">
                  <Wifi size={20} /> НОД — ФАЙЛОВЫЙ МОСТ
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  Агент X работает через файловый мост в <code className="text-cyan-400 bg-gray-800 px-2 py-1 rounded">nod_bridge/</code>.
                </p>
                <button
                  onClick={() => setActiveAgent('x')}
                  className="px-6 py-3 bg-green-900/30 border border-green-600 text-green-300 rounded-xl hover:bg-green-900 transition-colors font-bold text-sm"
                >
                  АКТИВИРОВАТЬ АГЕНТ X
                </button>
              </div>

              <div className="p-6 rounded-2xl border border-gray-700 bg-gray-900/40">
                <h3 className="text-white font-bold mb-4 flex items-center gap-2">
                  <Loader2 size={20} className="animate-spin" /> СТАТУС СИСТЕМ
                </h3>
                <p className="text-gray-400 text-sm mb-4">
                  Обновление каждые 15 секунд. Данные с бэкенда через API.
                </p>
                <button
                  onClick={checkStatus}
                  className="px-6 py-3 bg-blue-900/30 border border-blue-600 text-blue-300 rounded-xl hover:bg-blue-900 transition-colors font-bold text-sm"
                >
                  ОБНОВИТЬ СЕЙЧАС
                </button>
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-between items-center text-xs text-gray-500 font-mono border-t border-gray-800 pt-6 mt-8">
              <span>DRON X GENIE OS v0.2.0</span>
              <span>Кабина • app.dronxgenie.com</span>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
