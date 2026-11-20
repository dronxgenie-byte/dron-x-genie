import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, Loader2 } from 'lucide-react';

export default function DiaryView() {
  const [diary, setDiary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('http://127.0.0.1:8000/api/vault/diary')
      .then(res => {
        setDiary(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) return (
    <div className="flex h-full items-center justify-center text-cyan-500">
      <Loader2 className="animate-spin mr-3" size={32} /> ЗАГРУЗКА ПАМЯТИ КОРАБЛЯ...
    </div>
  );

  return (
    <div className="h-full w-full p-8 overflow-y-auto custom-scrollbar flex justify-center">
      <div className="max-w-4xl w-full bg-black/60 backdrop-blur-xl border border-cyan-500/30 rounded-2xl p-8 shadow-[0_0_50px_rgba(0,255,255,0.1)]">
        <div className="flex items-center gap-4 mb-6 border-b border-cyan-500/30 pb-4">
          <FileText className="text-cyan-400" size={32} />
          <div>
            <h2 className="text-2xl font-bold text-cyan-300 tracking-widest">БОРТОВОЙ ЖУРНАЛ</h2>
            <p className="text-cyan-600 text-sm font-mono">{diary?.filename || 'Файл не найден'}</p>
          </div>
        </div>
        
        {diary?.content ? (
          <div className="text-gray-200 text-lg leading-relaxed font-mono whitespace-pre-wrap">
            {diary.content}
          </div>
        ) : (
          <div className="text-red-400 text-center py-10">Нет данных для отображения.</div>
        )}
      </div>
    </div>
  );
}
