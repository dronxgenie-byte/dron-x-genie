import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles } from 'lucide-react';

export default function Holograms({ activeAgent }) {
  return (
    <div className="absolute inset-0 pointer-events-none z-10 flex justify-between items-center px-24 pb-32">
      
      {/* Голограмма Дрона (Слева) */}
      <motion.div 
        animate={{ 
          y: [0, -15, 0], 
          opacity: activeAgent === 'dron' ? [0.8, 1, 0.8] : 0.1,
          scale: activeAgent === 'dron' ? 1.1 : 1
        }} 
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        className="flex flex-col items-center"
      >
        <div className="relative">
          <div className={`absolute inset-0 blur-[50px] rounded-full transition-all duration-700 ${activeAgent === 'dron' ? 'bg-cyan-500/60' : 'bg-cyan-500/0'}`}></div>
          <Bot size={160} className={`relative z-10 transition-all duration-700 ${activeAgent === 'dron' ? 'text-cyan-300 drop-shadow-[0_0_40px_rgba(34,211,238,1)]' : 'text-cyan-800'}`} />
        </div>
      </motion.div>

      {/* Голограмма Джинни (Справа) */}
      <motion.div 
        animate={{ 
          y: [0, -20, 0], 
          opacity: activeAgent === 'jinny' ? [0.8, 1, 0.8] : 0.1,
          scale: activeAgent === 'jinny' ? 1.1 : 1
        }} 
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
        className="flex flex-col items-center"
      >
        <div className="relative">
          <div className={`absolute inset-0 blur-[50px] rounded-full transition-all duration-700 ${activeAgent === 'jinny' ? 'bg-purple-500/60' : 'bg-purple-500/0'}`}></div>
          <Sparkles size={160} className={`relative z-10 transition-all duration-700 ${activeAgent === 'jinny' ? 'text-purple-300 drop-shadow-[0_0_40px_rgba(168,85,247,1)]' : 'text-purple-900'}`} />
        </div>
      </motion.div>

    </div>
  );
}
