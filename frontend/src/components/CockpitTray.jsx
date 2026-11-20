import React, { useState } from 'react';
import { Send, LayoutGrid, ListTodo, Map, Folder, Landmark, Power, Menu, Monitor, Eye } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CockpitTray({ onSend, setActiveApp, onOpenBank, nodMode, setNodMode, onToggleAgent, onOpenSidebar, viewMode, setViewMode }) {
  const [text, setText] = useState('');
  const [appsOpen, setAppsOpen] = useState(false);

  const handleSend = (e) => {
    e.preventDefault();
    if (text.trim()) {
      onSend(text);
      setText('');
    }
  };

  return (
    <div className="fixed bottom-0 left-0 w-full z-50 flex justify-center pointer-events-none">
      <div className="relative w-full pointer-events-auto bg-gradient-to-t from-black via-gray-950 to-gray-900 border-t-2 border-cyan-700/60 shadow-[0_-10px_40px_rgba(0,0,0,0.9)] px-6 py-3 flex justify-between items-center gap-4 h-[90px]">
        
        {/* Левая часть: Меню, Переключатель Вида, Дрон */}
        <div className="flex items-center gap-3">
          <button onClick={onOpenSidebar} className="p-3 bg-gray-900 border border-gray-700 text-gray-400 rounded-xl hover:text-cyan-400 transition-all">
            <Menu size={24} />
          </button>
          
          {/* Кнопка переключения вида */}
          <button 
            onClick={() => setViewMode(viewMode === 'cabin' ? 'normal' : 'cabin')} 
            className="p-3 bg-gray-900 border border-gray-700 text-gray-400 rounded-xl hover:text-cyan-400 transition-all"
            title={viewMode === 'cabin' ? "Переключить на обычный вид" : "Переключить на вид кабины"}
          >
            {viewMode === 'cabin' ? <Monitor size={24} /> : <Eye size={24} />}
          </button>

          <button onClick={() => onToggleAgent('dron')} className="px-6 py-3 bg-cyan-950/60 hover:bg-cyan-900 text-cyan-300 rounded-xl font-bold tracking-widest border border-cyan-800/50 flex items-center gap-3 transition-all">
            <Power size={18} className="text-green-400" />
            <span>ДРОН</span>
          </button>
        </div>

        {/* Центр: Чат и Меню приложений */}
        <div className="flex-1 max-w-[900px] relative">
          
          <AnimatePresence>
            {appsOpen && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
                className="absolute bottom-[70px] left-0 w-full bg-gray-950/95 border border-cyan-500/30 rounded-xl p-3 shadow-[0_0_30px_rgba(0,0,0,0.9)] grid grid-cols-5 gap-2"
              >
                <button onClick={() => {setActiveApp('tasks'); setAppsOpen(false);}} className="py-3 bg-gray-900 hover:bg-cyan-900 text-cyan-400 text-xs font-bold rounded-lg flex flex-col items-center gap-2"><ListTodo size={20}/> ЗАДАЧИ</button>
                <button onClick={() => {setActiveApp('map'); setAppsOpen(false);}} className="py-3 bg-gray-900 hover:bg-cyan-900 text-cyan-400 text-xs font-bold rounded-lg flex flex-col items-center gap-2"><Map size={20}/> КАРТА</button>
                <button onClick={() => {setActiveApp('files'); setAppsOpen(false);}} className="py-3 bg-gray-900 hover:bg-cyan-900 text-cyan-400 text-xs font-bold rounded-lg flex flex-col items-center gap-2"><Folder size={20}/> ФАЙЛЫ</button>
                <button onClick={() => {onOpenBank(); setAppsOpen(false);}} className="py-3 bg-gray-900 hover:bg-yellow-900 text-yellow-400 text-xs font-bold rounded-lg flex flex-col items-center gap-2"><Landmark size={20}/> БАНК</button>
                <button onClick={() => {setActiveApp('diary'); setAppsOpen(false);}} className="py-3 bg-gray-900 hover:bg-cyan-900 text-cyan-400 text-xs font-bold rounded-lg flex flex-col items-center gap-2"><LayoutGrid size={20}/> ДНЕВНИК</button>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSend} className="flex gap-2 w-full bg-black/60 border border-gray-700/80 rounded-xl p-2 backdrop-blur-md">
            <button type="button" onClick={() => setAppsOpen(!appsOpen)} className={`p-3 rounded-lg transition-all ${appsOpen ? 'bg-cyan-900 text-cyan-300' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
              <LayoutGrid size={20} />
            </button>
            <input 
              type="text" value={text} onChange={(e) => setText(e.target.value)}
              placeholder="Ввод команды..." 
              className="flex-1 bg-transparent border-none text-white outline-none font-mono text-xl px-2"
            />
            <button type="submit" className="bg-cyan-700 hover:bg-cyan-600 text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 text-lg">
              <Send size={20} /> ПУСК
            </button>
          </form>
        </div>

        {/* Правая часть: Джинни и NOD */}
        <div className="flex items-center gap-3">
          <button onClick={() => setNodMode(!nodMode)} className={`px-4 py-3 rounded-xl font-bold tracking-widest border transition-all ${nodMode ? 'bg-green-900/50 border-green-500 text-green-300' : 'bg-gray-900 border-gray-700 text-gray-500'}`}>
            NOD
          </button>
          <button onClick={() => onToggleAgent('jinny')} className="px-6 py-3 bg-purple-950/60 hover:bg-purple-900 text-purple-300 rounded-xl font-bold tracking-widest border border-purple-800/50 flex items-center gap-3 transition-all flex-row-reverse">
            <Power size={18} className="text-green-400" />
            <span>ДЖИННИ</span>
          </button>
        </div>

      </div>
    </div>
  );
}
