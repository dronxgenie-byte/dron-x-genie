import React from 'react';
import { Calendar, Landmark, BookOpen, Brain, Network, Home, Book } from 'lucide-react';

export default function TopDock({ activeApp, setActiveApp }) {
  const apps = [
    { id: 'calendar', icon: <Calendar size={20} />, label: 'КАЛЕНДАРЬ' },
    { id: 'diary', icon: <Book size={20} />, label: 'ДНЕВНИК' }, // Новая кнопка
    { id: 'bank', icon: <Landmark size={20} />, label: 'БАНК' },
    { id: 'school', icon: <BookOpen size={20} />, label: 'ШКОЛА' },
    { id: 'brain', icon: <Brain size={20} />, label: 'МОЗГ' },
  ];

  return (
    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 pointer-events-auto">
      <div className="flex gap-2 p-2 bg-black/60 backdrop-blur-lg border border-cyan-500/30 rounded-2xl shadow-[0_0_30px_rgba(0,255,255,0.1)]">
        <button 
          onClick={() => setActiveApp('chat')}
          className={`p-3 rounded-xl transition-all duration-300 flex flex-col items-center gap-1 ${activeApp === 'chat' ? 'bg-cyan-900/80 text-cyan-300 shadow-[0_0_15px_rgba(0,255,255,0.4)]' : 'text-gray-400 hover:text-cyan-400 hover:bg-cyan-950/50'}`}
        >
          <Home size={20} />
          <span className="text-[9px] font-bold tracking-widest">МОСТИК</span>
        </button>
        <div className="w-px bg-cyan-500/20 mx-1"></div>
        {apps.map((app) => (
          <button
            key={app.id}
            onClick={() => setActiveApp(app.id)}
            className={`p-3 rounded-xl transition-all duration-300 flex flex-col items-center gap-1 ${activeApp === app.id ? 'bg-cyan-900/80 text-cyan-300 shadow-[0_0_15px_rgba(0,255,255,0.4)]' : 'text-gray-400 hover:text-cyan-400 hover:bg-cyan-950/50'}`}
          >
            {app.icon}
            <span className="text-[9px] font-bold tracking-widest">{app.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
