import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Bot, Sparkles, Mic, Eye, Volume2, Brain, Wrench, Puzzle, Settings2 } from 'lucide-react';

export default function AgentPanel({ activePanel, onClose }) {
  const [activeTab, setActiveTab] = useState('brain'); // brain, hearing, voice, hands, plugins

  if (!activePanel) return null;

  const isDron = activePanel === 'dron';
  const color = isDron ? 'cyan' : 'purple';
  const title = isDron ? 'ДРОН [LOCAL]' : 'ДЖИННИ [CLOUD]';
  const Icon = isDron ? Bot : Sparkles;
  const side = isDron ? '-100%' : '100%';
  const position = isDron ? 'left-0 border-r' : 'right-0 border-l';

  const TabButton = ({ id, icon, label }) => (
    <button 
      onClick={() => setActiveTab(id)}
      className={`flex flex-col items-center justify-center py-3 px-2 gap-1 text-[10px] font-bold tracking-widest transition-all w-full
        ${activeTab === id 
          ? `bg-${color}-900/40 text-${color}-300 border-b-2 border-${color}-500` 
          : `text-gray-500 hover:text-gray-300 hover:bg-gray-900/50 border-b-2 border-transparent`
        }`}
    >
      {icon}
      {label}
    </button>
  );

  const SettingCard = ({ title, desc, action }) => (
    <div className={`p-4 rounded-xl bg-gray-900/60 border border-gray-800 hover:border-${color}-500/30 transition-all flex justify-between items-center`}>
      <div>
        <div className="text-gray-200 font-bold text-sm mb-1">{title}</div>
        <div className="text-gray-500 text-xs">{desc}</div>
      </div>
      {action}
    </div>
  );

  const Toggle = ({ active }) => (
    <div className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${active ? `bg-${color}-600` : 'bg-gray-700'}`}>
      <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all ${active ? 'left-6' : 'left-1'}`}></div>
    </div>
  );

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ x: side }} animate={{ x: 0 }} exit={{ x: side }} transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        className={`fixed top-0 ${position} h-full w-[380px] bg-gray-950/95 backdrop-blur-xl border-${color}-500/40 shadow-[0_0_50px_rgba(0,0,0,0.9)] z-[60] flex flex-col`}
      >
        {/* Заголовок */}
        <div className={`p-4 flex justify-between items-center border-b border-${color}-900/50 bg-${color}-950/20`}>
          <span className={`text-${color}-400 font-bold tracking-widest flex items-center gap-2 text-sm`}>
            <Icon size={20} /> {title}
          </span>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors"><X size={20}/></button>
        </div>
        
        {/* Вкладки (как в Dewiar) */}
        <div className="flex border-b border-gray-800 bg-black/30">
          <TabButton id="brain" icon={<Brain size={18}/>} label="МОЗГ" />
          <TabButton id="hearing" icon={<Mic size={18}/>} label="СЛУХ" />
          <TabButton id="voice" icon={<Volume2 size={18}/>} label="ГОЛОС" />
          <TabButton id="hands" icon={<Wrench size={18}/>} label="РУКИ" />
          <TabButton id="plugins" icon={<Puzzle size={18}/>} label="ПЛАГИНЫ" />
        </div>

        {/* Контент вкладок */}
        <div className="p-4 flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-3">
          
          {/* МОЗГ */}
          {activeTab === 'brain' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-3">
              <div className={`p-4 rounded-xl bg-${color}-950/20 border border-${color}-500/30`}>
                <div className="text-xs text-gray-400 mb-2 tracking-widest">АКТИВНАЯ МОДЕЛЬ</div>
                <div className={`text-lg font-bold text-${color}-300 font-mono`}>google/gemma-4-e4b</div>
                <div className="text-[10px] text-gray-500 mt-1">Локальный сервер LM Studio (порт 1234)</div>
              </div>
              <SettingCard title="Температура" desc="Креативность модели (0.0 - 1.0)" action={<span className="text-gray-300 font-mono">0.7</span>} />
              <SettingCard title="Системный промпт" desc="Базовые инструкции для агента" action={<button className="text-cyan-400 text-xs hover:underline">Изменить</button>} />
            </motion.div>
          )}

          {/* СЛУХ */}
          {activeTab === 'hearing' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-3">
               <SettingCard title="Микрофон" desc="Слушать команды с микрофона" action={<Toggle active={true} />} />
               <SettingCard title="Активация по имени" desc="Реагировать на имя агента" action={<Toggle active={true} />} />
               <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800">
                 <div className="text-xs text-gray-500 mb-2">УРОВЕНЬ СИГНАЛА</div>
                 <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className={`w-2/3 h-full bg-${color}-500`}></div>
                 </div>
               </div>
            </motion.div>
          )}

          {/* ГОЛОС */}
          {activeTab === 'voice' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-3">
               <SettingCard title="Озвучка ответов" desc="Включить синтез речи" action={<Toggle active={true} />} />
               <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800">
                  <div className="text-xs text-gray-500 mb-2 tracking-widest">ДОСТУПНЫЕ ГОЛОСА</div>
                  <div className="space-y-2">
                    <button className={`w-full text-left p-2 rounded border border-${color}-500 text-${color}-300 bg-${color}-900/20 text-xs flex justify-between`}>Yandex SpeechKit (ru-RU) <span>✅</span></button>
                    <button className="w-full text-left p-2 rounded border border-gray-700 text-gray-400 hover:bg-gray-800 text-xs flex justify-between">Windows SAPI (Ирина) <span></span></button>
                  </div>
               </div>
            </motion.div>
          )}

          {/* РУКИ */}
          {activeTab === 'hands' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col gap-3">
               <SettingCard title="Поиск в интернете" desc="Разрешить поиск информации" action={<Toggle active={true} />} />
               <SettingCard title="Управление картой" desc="Строить маршруты" action={<Toggle active={false} />} />
               <SettingCard title="Открытие приложений" desc="Запуск программ на ПК" action={<Toggle active={false} />} />
            </motion.div>
          )}

          {/* ПЛАГИНЫ */}
          {activeTab === 'plugins' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-2 gap-2">
               <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col items-center text-center gap-2 hover:border-cyan-500/50 cursor-pointer">
                 <div className="p-2 rounded-full bg-cyan-900/30 text-cyan-400"><Brain size={20}/></div>
                 <span className="text-xs text-gray-300 font-bold">Obsidian</span>
                 <span className="text-[9px] text-green-400">Установлен</span>
               </div>
               <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col items-center text-center gap-2 hover:border-purple-500/50 cursor-pointer">
                 <div className="p-2 rounded-full bg-purple-900/30 text-purple-400"><Wrench size={20}/></div>
                 <span className="text-xs text-gray-300 font-bold">n8n</span>
                 <span className="text-[9px] text-gray-500">Выкл</span>
               </div>
               <div className="p-3 rounded-xl bg-gray-900/60 border border-gray-800 flex flex-col items-center text-center gap-2 hover:border-yellow-500/50 cursor-pointer col-span-2">
                 <div className="p-2 rounded-full bg-yellow-900/30 text-yellow-400"><Settings2 size={20}/></div>
                 <span className="text-xs text-gray-300 font-bold">Добавить плагин</span>
               </div>
            </motion.div>
          )}

        </div>
      </motion.div>
    </AnimatePresence>
  );
}
