'use client';

import React, { useState } from 'react';
import { FiSearch, FiPlus, FiSettings, FiActivity } from 'react-icons/fi';
import MascotAvatar from './MascotAvatar';
import DotAvatar from './DotAvatar';

export default function Sidebar({
  bots,
  activeBotId,
  userName,
  onSelectBot,
  activeTab,
  onSelectTab,
  onOpenSettings,
  onOpenNewBot,
  onEditBot
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isIssueDismissed, setIsIssueDismissed] = useState(false);
  // userName comes from Dashboard (synced with AppSettingsDrawer in real-time)
  const displayName = userName || 'You';


  // Default bot list fallback matching the exact mockup items if bots array is empty or customized
  const defaultMockupBots = [
    {
      id: 'bot-new-error',
      name: 'New Bot',
      subtitle: 'Your assistants will show up here',
      avatarType: 'warning',
      time: '2:49 PM',
      isError: true,
    },
    {
      id: 'bot-new-pink',
      name: 'New Bot',
      subtitle: 'What do you mostly want help with?',
      avatarType: 'pink',
      time: '',
      isError: false,
    },
    {
      id: 'bot-new-blue-1',
      name: 'New Bot',
      subtitle: 'What do you mostly want help with?',
      avatarType: 'blue',
      time: '',
      isError: false,
    },
    {
      id: 'bot-milind',
      name: 'Milind',
      subtitle: 'What do you mostly want help with?',
      avatarType: 'blue',
      time: '',
      isError: false,
    },
  ];

  // Merge real bots or fallback to mockup display
  const displayBots = bots && bots.length > 0
    ? bots.map((b, idx) => ({
        id: b.id,
        name: b.name,
        subtitle: b.role || b.description || 'General Intelligence',
        avatarType: b.isError ? 'warning' : idx % 2 === 1 ? 'pink' : 'blue',
        time: b.created_at ? new Date(b.created_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }) : (b.time || ''),
        isError: !!b.isError,
        originalBot: b
      }))
    : defaultMockupBots;


  const errorCount = displayBots.filter((b) => b.isError).length;

  const filteredBots = displayBots.filter(
    (b) =>
      b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      b.subtitle.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <aside className="w-72 h-screen dark-sidebar flex flex-col justify-between select-none flex-shrink-0 text-zinc-300 font-sans">
      {/* Top Header & Search Area */}
      <div className="p-3.5 space-y-3">
        {/* Traffic Light Dots & Plus Button Header */}
        <div className="flex items-center justify-between pt-1 px-1">
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-[#ff5f57] block border border-[#e0443e]/40 cursor-pointer hover:opacity-80 transition" />
            <span className="w-3 h-3 rounded-full bg-[#febc2e] block border border-[#d8a025]/40 cursor-pointer hover:opacity-80 transition" />
            <span className="w-3 h-3 rounded-full bg-[#28c840] block border border-[#1fa031]/40 cursor-pointer hover:opacity-80 transition" />
          </div>

          <button
            suppressHydrationWarning={true}
            onClick={onOpenNewBot}
            title="Create New Bot"
            className="text-zinc-400 hover:text-fg transition p-1 rounded-md hover:bg-surf3"
          >
            <FiPlus className="text-lg" />
          </button>
        </div>

        {/* Rounded Search Bar */}
        <div className="relative">
          <FiSearch className="absolute left-3 top-2.5 text-zinc-500 text-xs" />
          <input
            suppressHydrationWarning={true}
            type="text"
            placeholder="Search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-surf3 border border-line2 rounded-xl pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-500 transition"
          />
        </div>
      </div>

      {/* Bot Roster List */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1.5">
        {filteredBots.map((botItem) => {
          const isActive = activeBotId === botItem.id || (activeBotId === '' && botItem.id === displayBots[0]?.id);

          return (
            <div
              key={botItem.id}
              onClick={() => onSelectBot(botItem.id)}
              className={`group p-2.5 rounded-xl cursor-pointer transition-all duration-150 flex items-start gap-3 ${
                isActive
                  ? 'bg-surf3 text-fg shadow-sm border border-line2'
                  : 'hover:bg-surf2 text-zinc-400 border border-transparent'
              }`}
            >
              {botItem.originalBot ? (
                <DotAvatar bot={botItem.originalBot} size={46} alive={isActive} />
              ) : (
                <MascotAvatar type={botItem.avatarType} size="md" />
              )}

              <div className="flex-1 min-w-0 pt-0.5">
                <div className="flex items-center justify-between">
                  <h3 className={`text-xs font-semibold truncate ${isActive ? 'text-fg' : 'text-zinc-200'}`}>
                    {botItem.name}
                  </h3>
                  {botItem.originalBot && onEditBot && (
                    <button
                      type="button"
                      title="Personalitza"
                      onClick={(e) => { e.stopPropagation(); onEditBot(botItem.id); }}
                      className="ml-1 rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-200 opacity-0 transition group-hover:opacity-100 hover:bg-zinc-700"
                    >
                      Personalitza
                    </button>
                  )}
                  {botItem.time && (
                    <span className="text-[10px] text-zinc-400 font-normal ml-1">
                      {botItem.time}
                    </span>
                  )}
                </div>

                <p
                  className={`text-[11px] truncate mt-0.5 ${
                    botItem.isError
                      ? 'text-zinc-400'
                      : 'text-zinc-400 group-hover:text-zinc-300'
                  }`}
                >
                  {botItem.subtitle}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Sidebar Footer */}
      <div className="p-3 space-y-2 border-t border-line1">
        {/* Plugins Section */}
        <button
          suppressHydrationWarning={true}
          onClick={() => onSelectTab && onSelectTab('marketplace')}
          className={`w-full flex items-center gap-2 px-2 py-1 rounded-lg text-xs font-medium transition ${
            activeTab === 'marketplace'
              ? 'text-fg bg-surf2'
              : 'text-zinc-300 hover:text-fg hover:bg-surf2'
          }`}
        >
          <span className="text-sm">🧩</span>
          <span>Plugins</span>
        </button>

        <button
          suppressHydrationWarning={true}
          onClick={() => onSelectTab && onSelectTab('audit')}
          className={`w-full flex items-center gap-2 px-2 py-1 rounded-lg text-xs font-medium transition ${
            activeTab === 'audit'
              ? 'text-fg bg-surf2'
              : 'text-zinc-300 hover:text-fg hover:bg-surf2'
          }`}
        >
          <FiActivity className="text-sm text-cyan-400" />
          <span>Audit trail</span>
        </button>

        {/* Dynamic Issue Alert Badge vs You Profile Row */}
        <div className="flex items-center justify-between pt-1">
          {errorCount > 0 && !isIssueDismissed ? (
            <div className="flex items-center gap-2">
              <div
                className="bg-[#e11d48]/90 hover:bg-[#e11d48] text-white text-[11px] font-semibold px-2.5 py-1 rounded-full flex items-center gap-1.5 shadow-sm border border-rose-500/40 cursor-pointer transition"
                title={`${errorCount} agent process spawn issue detected`}
              >
                <span className="w-2 h-2 rounded-full bg-white block animate-pulse" />
                <span>{errorCount} Issue{errorCount > 1 ? 's' : ''}</span>
                <button
                  suppressHydrationWarning={true}
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsIssueDismissed(true);
                  }}
                  className="text-white/80 hover:text-white ml-0.5 font-bold transition focus:outline-none"
                  title="Dismiss issue notification"
                >
                  ✕
                </button>

              </div>
            </div>
          ) : (
            <button
              suppressHydrationWarning={true}
              onClick={onOpenSettings}
              className="flex items-center gap-2 px-2 py-1 rounded-lg text-xs font-medium text-zinc-300 hover:text-fg hover:bg-surf2 transition"
            >
              <div className="w-5 h-5 rounded-full bg-surf3 flex items-center justify-center text-[10px] text-zinc-400 font-bold border border-line2">
                {displayName.charAt(0).toUpperCase()}
              </div>
              <span>{displayName}</span>
            </button>

          )}

          <button
            suppressHydrationWarning={true}
            onClick={onOpenSettings}
            className="p-2 text-zinc-400 hover:text-zinc-200 hover:bg-surf2 rounded-lg transition"
            title="Settings"
          >
            <FiSettings className="text-sm" />
          </button>
        </div>
      </div>
    </aside>
  );
}

