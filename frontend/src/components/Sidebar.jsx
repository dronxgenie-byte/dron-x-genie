import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, MessageSquare, Settings, X, Folder } from 'lucide-react';

export default function Sidebar({ isOpen, onClose }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Затемнение фона */}
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[60]"
          />
          {/* Сама панель */}
          <motion.div 
            initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }} transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 left-0 h-full w-[300px] bg-gray-950 border-r border-cyan-900/50 shadow-[0_0_50px_rgba(0,0,0,0.9)] z-[70] flex flex-col"
          >
            <div className="p-4 flex justify-between items-center border-b border-gray-800">
              <span className="text-cyan-400 font-bold tracking-widest">БОРТОВОЙ ЖУРНАЛ</span>
              <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={20}/></button>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto">
              <button className="w-full flex items-center gap-2 bg-cyan-900/30 hover:bg-cyan-900/60 text-cyan-300 p-3 rounded-lg border border-cyan-700/50 mb-6 transition-all">
                <Plus size={18} /> НОВЫЙ СЕАНС СВЯЗИ
              </button>
              
              <div className="text-xs text-gray-500 font-bold mb-2 tracking-widest">ИСТОРИЯ</div>
              <div className="space-y-1">
                <button className="w-full text-left p-2 rounded text-gray-300 hover:bg-gray-800 flex items-center gap-2 text-sm truncate">
                  <MessageSquare size={14} className="text-cyan-500"/> Полёт к Сатурну
                </button>
                <button className="w-full text-left p-2 rounded text-gray-300 hover:bg-gray-800 flex items-center gap-2 text-sm truncate">
                  <MessageSquare size={14} className="text-cyan-500"/> Урок математики
                </button>
                <button className="w-full text-left p-2 rounded text-gray-300 hover:bg-gray-800 flex items-center gap-2 text-sm truncate">
                  <MessageSquare size={14} className="text-cyan-500"/> Настройка n8n
                </button>
              </div>
            </div>

            <div className="p-4 border-t border-gray-800">
              <button className="w-full flex items-center gap-2 text-gray-400 hover:text-white p-2 text-sm">
                <Settings size={16} /> НАСТРОЙКИ КОРАБЛЯ
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
