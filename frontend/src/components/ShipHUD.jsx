import { useState, useEffect } from 'react'

export default function ShipHUD({ nodMode, onToggleNOD }) {
  const [telemetry, setTelemetry] = useState({ cpu: 0, ram: 0 })

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry({
        cpu: Math.floor(Math.random() * 40) + 20,
        ram: Math.floor(Math.random() * 50) + 30,
      })
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex justify-between w-full max-w-6xl mx-auto">
      {/* Левая панель — Дрон */}
      <div className="flex flex-col gap-2 w-64">
        <div className="bg-cyan-900/30 border border-cyan-500/30 rounded p-3 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
          <div className="flex items-center gap-2 mb-2 text-cyan-400 font-bold uppercase text-[10px]">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            ДРОН (LOCAL)
          </div>
          <div className="text-xs text-cyan-200 space-y-1">
            <div className="flex justify-between">
              <span>Статус:</span>
              <span className="text-green-400">АКТИВЕН</span>
            </div>
            <div className="flex justify-between">
              <span>Модель:</span>
              <span>gemma-4-e4b</span>
            </div>
            <div className="flex justify-between">
              <span>Навыки:</span>
              <span>кодер, файлы, vault</span>
            </div>
          </div>
        </div>
      </div>

      {/* Центр — телеметрия */}
      <div className="flex flex-col items-center gap-2">
        <div className="bg-gray-900/50 border border-gray-700 rounded p-3 shadow-[0_0_15px_rgba(255,255,255,0.1)]">
          <div className="text-xs text-gray-400 uppercase font-bold mb-2">ТЕЛЕМЕТРИЯ КОРАБЛЯ</div>
          <div className="w-48 bg-gray-800 rounded-full h-4 overflow-hidden border border-gray-600">
            <div
              className={`h-full bg-cyan-500 transition-all duration-500`}
              style={{ width: `${telemetry.cpu}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-300 mt-1">
            <span>CPU: {telemetry.cpu}%</span>
            <span>RAM: {telemetry.ram}%</span>
          </div>
        </div>
      </div>

      {/* Правая панель — управление */}
      <div className="flex flex-col gap-2 w-64 items-end">
        <div className="bg-purple-900/30 border border-purple-500/30 rounded p-3 shadow-[0_0_15px_rgba(168,85,247,0.3)]">
          <div className="flex items-center gap-2 mb-2 text-purple-400 font-bold uppercase text-[10px]">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            ДЖИННИ (CLOUD)
          </div>
          <div className="text-xs text-purple-200 space-y-1">
            <div className="flex justify-between">
              <span>Статус:</span>
              <span className="text-green-400">ОНЛАЙН</span>
            </div>
            <div className="flex justify-between">
              <span>Модель:</span>
              <span>yandexgpt/latest</span>
            </div>
            <div className="flex justify-between">
              <span>Речь:</span>
              <span>ru-RU-Svetlana</span>
            </div>
          </div>
        </div>

        {/* NOD Mode toggle */}
        <button
          onClick={onToggleNOD}
          className={`mt-2 px-3 py-1.5 rounded text-xs font-bold transition ${
            nodMode
              ? 'bg-cyan-600 text-white border border-cyan-400'
              : 'bg-gray-800 text-gray-300 border border-gray-600 hover:bg-gray-700'
          }`}
        >
          {nodMode ? 'NOD: ВКЛ' : 'NOD: ВЫКЛ'}
        </button>
      </div>
    </div>
  )
}
