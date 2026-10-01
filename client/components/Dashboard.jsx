'use client';

import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import ChatWindow from './ChatWindow';
import ComputerPanel from './ComputerPanel';
import Marketplace from './Marketplace';
import AuditPanel from './AuditPanel';
import WhatsAppPanel from './WhatsAppPanel';
import AppSettingsDrawer from './AppSettingsDrawer';
import CatalogModal from './CatalogModal';
import DotStudio from './DotStudio';

import { 
  fetchBots, 
  fetchModels, 
  fetchChatHistory, 
  fetchSettings,
  updateBot 
} from '../lib/api';

export default function Dashboard() {
  const [bots, setBots] = useState([]);
  const [models, setModels] = useState([]);
  const [activeBotId, setActiveBotId] = useState('');
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'computer' | 'marketplace' | 'audit' | 'whatsapp'
  const [messages, setMessages] = useState([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isCatalogOpen, setIsCatalogOpen] = useState(false);
  const [studioBotId, setStudioBotId] = useState('');
  const [defaultModel, setDefaultModel] = useState('gpt-5-mini');
  const [userName, setUserName] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('open_dots_user_name') || 'You';
    }
    return 'You';
  });

  // Initial Data Fetch
  useEffect(() => {
    async function initData() {
      try {
        const [botsData, modelsData, settingsData] = await Promise.all([fetchBots(), fetchModels(), fetchSettings()]);
        setBots(botsData);
        setModels(modelsData);
        if (settingsData?.default_model) {
          setDefaultModel(settingsData.default_model);
        }
        if (botsData.length > 0) {
          setActiveBotId(botsData[0].id);
        }
      } catch (err) {
        console.error('Initialization error:', err);
      }
    }
    initData();
  }, []);

  // Fetch chat history whenever active bot changes
  useEffect(() => {
    if (!activeBotId) return;
    fetchChatHistory(activeBotId)
      .then((history) => setMessages(history))
      .catch((err) => console.error('Failed to load history:', err));
  }, [activeBotId]);

  const activeBot = bots.find((b) => b.id === activeBotId) || bots[0];

  const handleUpdateBotModel = async (botId, newModel) => {
    try {
      const updated = await updateBot(botId, { model: newModel });
      setBots((prev) => prev.map((b) => (b.id === botId ? updated : b)));
    } catch (err) {
      console.error('Failed to update bot model:', err);
    }
  };

  const handleCreateNewBot = () => setIsCatalogOpen(true);

  const handleSaveLook = async (botId, updates) => {
    const updated = await updateBot(botId, updates);
    setBots((prev) => prev.map((b) => (b.id === botId ? updated : b)));
  };

  const handleBotCreated = (bot) => {
    setBots((prev) => [...prev, bot]);
    setActiveBotId(bot.id);
    setActiveTab('chat');
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surf0 text-zinc-100 font-sans">
      {/* Sidebar Navigation & Bot Roster */}
      <Sidebar
        bots={bots}
        activeBotId={activeBotId}
        userName={userName}
        onSelectBot={(id) => {
          setActiveBotId(id);
          setActiveTab('chat');
        }}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenSettings={() => setIsSettingsOpen(!isSettingsOpen)}
        onOpenNewBot={handleCreateNewBot}
        onEditBot={setStudioBotId}
      />

      {/* Main Workspace Display Area */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden relative">
        {activeTab === 'chat' && (
          <ChatWindow
            bot={activeBot}
            models={models}
            messages={messages}
            setMessages={setMessages}
            onUpdateBotModel={handleUpdateBotModel}
            onToggleComputer={() => setActiveTab('computer')}
            defaultModel={defaultModel}
            onEditBot={setStudioBotId}
          />
        )}

        {activeTab === 'computer' && (
          <ComputerPanel bot={activeBot} onBackToChat={() => setActiveTab('chat')} />
        )}

        {activeTab === 'marketplace' && (
          <Marketplace onOpenSettings={() => setIsSettingsOpen(true)} />
        )}

        {activeTab === 'whatsapp' && <WhatsAppPanel />}

        {activeTab === 'audit' && <AuditPanel />}
      </main>

      {studioBotId && (
        <DotStudio
          bot={bots.find((b) => b.id === studioBotId)}
          onClose={() => setStudioBotId('')}
          onSave={handleSaveLook}
        />
      )}

      <CatalogModal isOpen={isCatalogOpen} onClose={() => setIsCatalogOpen(false)} onCreated={handleBotCreated} />

      {/* Right Side App Settings Drawer Panel */}
      <AppSettingsDrawer
        models={models}
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentModel={defaultModel}
        onUpdateDefaultModel={async (newModel) => {
          setDefaultModel(newModel);
          setModels(await fetchModels());
        }}
        onProfileUpdate={(name) => setUserName(name || 'You')}
      />
    </div>
  );
}
