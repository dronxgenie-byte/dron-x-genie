import React, { useState, useEffect, useRef } from 'react';
import { sendMessage } from '../api';
import { Terminal } from 'lucide-react';

export default function UnifiedChat({ nodMode, activeAgent = 'x' }) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    const handleTraySend = (e) => processMessage(e.detail);
    window.addEventListener('sendMessageFromTray', handleTraySend);
    return () => window.removeEventListener('sendMessageFromTray', handleTraySend);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const processMessage = async (text) => {
    if (!text.trim()) return;
    setMessages(prev => [...prev, { sender: 'user', text }]);
    setIsLoading(true);
    try {
      const response = await sendMessage(text, activeAgent);
      setIsLoading(false);
      
      if (response.data.dron_reply && response.data.jinny_reply) {
        setMessages(prev => [
          ...prev, 
          { sender: 'dron', text: response.data.dron_reply },
          { sender: 'jinny', text: response.data.jinny_reply }
        ]);
      } else if (response.data.nod_steps) {
        setMessages(prev => [...prev, { sender: 'dron', text: response.data.response || "Задача выполнена.", steps: response.data.nod_steps }]);
      } else {
        const textResp = response.data.response || response.data.text || JSON.stringify(response.data);
        const sender = response.data.agent === 'genie' ? 'jinny' : response.data.agent === 'x' ? 'agent_x' : 'dron';
        setMessages(prev => [...prev, { sender: sender, text: textResp }]);
      }
    } catch (error) {
      setIsLoading(false);
      setMessages(prev => [...prev, { sender: 'system', text: 'Связь с кораблём потеряна. Проверьте бэкенд.' }]);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto px-6 pt-4 pb-4 space-y-6 custom-scrollbar">
      
      {messages.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center h-full text-cyan-700/60 animate-pulse">
          <Terminal size={80} className="mb-6" />
          <h2 className="text-3xl font-bold tracking-widest">БОРТОВОЙ КОМПЬЮТЕР ГОТОВ</h2>
          <p className="text-lg mt-3 font-mono">Введите команду на нижней панели...</p>
        </div>
      )}

      {messages.map((msg, idx) => (
        <div key={idx} className={`flex w-full ${msg.sender === 'user' ? 'justify-center' : msg.sender === 'jinny' ? 'justify-end' : 'justify-start'}`}>
          
          <div className={`max-w-[75%] p-4 rounded-xl border backdrop-blur-sm text-xl leading-relaxed font-mono tracking-wide shadow-lg
            ${msg.sender === 'user' ? 'bg-blue-900/10 border-blue-500/50 text-blue-100 text-center' : ''}
            ${msg.sender === 'dron' ? 'bg-cyan-950/20 border-cyan-500/50 text-cyan-50 text-left' : ''}
            ${msg.sender === 'jinny' ? 'bg-purple-950/20 border-purple-500/50 text-purple-100 text-left' : ''}
            ${msg.sender === 'agent_x' ? 'bg-green-950/20 border-green-500/50 text-green-50 text-left' : ''}
            ${msg.sender === 'system' ? 'bg-red-950/30 border-red-500/80 text-red-200 font-bold' : ''}
          `}>
            <div className="font-bold text-xs mb-2 opacity-70 flex items-center gap-2">
              {msg.sender === 'user' && '👨‍✈️ КАПИТАН / ВАНЯ'}
              {msg.sender === 'dron' && '🤖 ДРОН [LOCAL]'}
              {msg.sender === 'jinny' && '✨ ДЖИННИ [CLOUD]'}
              {msg.sender === 'agent_x' && '👽 АГЕНТ X [NOD]'}
              {msg.sender === 'system' && '⚠️ СИСТЕМА'}
            </div>
            <div className="whitespace-pre-wrap">{msg.text}</div>
            
            {nodMode && msg.steps && (
              <div className="mt-3 pt-3 border-t border-cyan-700/50 text-sm text-cyan-300/70">
                <div className="font-bold mb-1">NOD STEPS:</div>
                {msg.steps.map((step, i) => (
                  <div key={i}>[ {step.state || step.step} ] {step.action || ''}</div>
                ))}
              </div>
            )}
          </div>

        </div>
      ))}
      
      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-cyan-950/20 border border-cyan-500/50 p-4 rounded-xl text-cyan-400 text-lg animate-pulse flex items-center gap-3">
            <span className="w-3 h-3 bg-cyan-400 rounded-full animate-ping"></span>
            Агент печатает...
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
