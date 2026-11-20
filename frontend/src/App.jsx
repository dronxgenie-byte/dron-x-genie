import React, { useState, useEffect } from 'react';
import CockpitFrame from './components/CockpitFrame';
import SpaceBackground from './components/SpaceBackground';
import UnifiedChat from './components/UnifiedChat';
import CockpitTray from './components/CockpitTray';
import BankPanel from './components/BankPanel';
import Holograms from './components/Holograms';
import AgentPanel from './components/AgentPanel';
import Sidebar from './components/Sidebar';
import DiaryView from './components/DiaryView';
import LandingPage from './components/LandingPage';
import CabinInterface from './components/CabinInterface';

function App() {
  const [viewMode, setViewMode] = useState('cabin');
  const [activeApp, setActiveApp] = useState('chat');
  const [isBankOpen, setIsBankOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activePanel, setActivePanel] = useState(null);
  const [nodMode, setNodMode] = useState(false);
  const [activeAgent, setActiveAgent] = useState('x');

  // Views: 'landing' | 'cabin'
  const [view, setView] = useState('landing');

  useEffect(() => {
    const handleEnterCockpit = () => setView('cabin');
    window.addEventListener('enter-cockpit', handleEnterCockpit);
    return () => window.removeEventListener('enter-cockpit', handleEnterCockpit);
  }, []);

  const handleSendGlobal = (text) => {
    const event = new CustomEvent('sendMessageFromTray', { detail: text });
    window.dispatchEvent(event);
  };

  const toggleAgentPanel = (agent) => {
    setActivePanel(prev => prev === agent ? null : agent);
  };

  if (view === 'landing') {
    return <LandingPage />;
  }

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-black text-white font-orbitron select-none">
      {viewMode === 'cabin' ? <CockpitFrame /> : <SpaceBackground />}

      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      <AgentPanel activePanel={activePanel} onClose={() => setActivePanel(null)} />

      <CabinInterface
        onExit={() => setView('landing')}
        setActiveAgent={setActiveAgent}
        activeAgent={activeAgent}
        nodMode={nodMode}
        setNodMode={setNodMode}
      />

      <main className="relative z-10 flex flex-col h-full w-full pb-[100px]">
        <div className="flex-1 overflow-hidden relative px-8 pt-20">
          {activeApp === 'chat' && <UnifiedChat nodMode={nodMode} activeAgent={activeAgent} />}
          {activeApp === 'diary' && <DiaryView />}
        </div>

        <Holograms activeAgent={activePanel} />

        <CockpitTray
          setActiveApp={setActiveApp}
          onSend={handleSendGlobal}
          onOpenBank={() => setIsBankOpen(true)}
          onOpenSidebar={() => setIsSidebarOpen(true)}
          onToggleAgent={toggleAgentPanel}
          nodMode={nodMode}
          setNodMode={setNodMode}
          viewMode={viewMode}
          setViewMode={setViewMode}
        />

        {isBankOpen && <BankPanel onClose={() => setIsBankOpen(false)} />}
      </main>
    </div>
  );
}

export default App;
