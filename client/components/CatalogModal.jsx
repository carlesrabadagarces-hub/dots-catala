'use client';

import React, { useEffect, useState } from 'react';
import { FiX, FiSearch, FiPlus } from 'react-icons/fi';
import DotAvatar from './DotAvatar';
import { fetchCatalog, fetchCatalogSectors, installCatalogAgent, generateAgent } from '../lib/api';

export default function CatalogModal({ isOpen, onClose, onCreated }) {
  const [tab, setTab] = useState('catalog'); // 'catalog' | 'ai'
  const [sectors, setSectors] = useState([]);
  const [sector, setSector] = useState('');
  const [query, setQuery] = useState('');
  const [agents, setAgents] = useState([]);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    fetchCatalogSectors().then(setSectors).catch(() => {});
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const timer = setTimeout(() => {
      fetchCatalog(sector, query).then(setAgents).catch(() => setAgents([]));
    }, 180);
    return () => clearTimeout(timer);
  }, [isOpen, sector, query]);

  if (!isOpen) return null;

  async function add(agent) {
    setBusy(agent.id);
    setError('');
    try {
      const bot = await installCatalogAgent(agent.id);
      onCreated(bot);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  async function createWithAi(e) {
    e.preventDefault();
    setBusy('ai');
    setError('');
    try {
      const bot = await generateAgent(description);
      onCreated(bot);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Afegeix un Dot">
      <div className="flex max-h-[88vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-zinc-800 bg-surf1 text-zinc-100 shadow-2xl">
        <div className="flex items-center justify-between border-b border-zinc-800 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Afegeix un Dot</h2>
            <p className="text-xs text-zinc-500">Tria&apos;n un de fet per al teu ofici o descriu-ne un de nou.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Tanca" className="rounded-full p-2 text-zinc-400 hover:bg-zinc-800 hover:text-fg">
            <FiX />
          </button>
        </div>

        <div className="flex gap-2 px-6 pt-4">
          {[['catalog', 'Catàleg'], ['ai', 'Crea amb IA']].map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${tab === id ? 'bg-inv text-invtext' : 'bg-zinc-900 text-zinc-300 hover:bg-zinc-800'}`}
            >
              {label}
            </button>
          ))}
        </div>

        {error && <p role="alert" className="px-6 pt-3 text-sm text-red-400">{error}</p>}

        {tab === 'catalog' ? (
          <>
            <div className="space-y-3 px-6 py-4">
              <div className="relative">
                <FiSearch className="absolute left-3 top-3 text-zinc-500" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Cerca: fontaner, metge, comptable, professor…"
                  className="w-full rounded-full border border-zinc-800 bg-zinc-900 py-2.5 pl-9 pr-4 text-sm outline-none focus:border-zinc-500"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => setSector('')} className={`rounded-full border px-3 py-1 text-xs ${sector === '' ? 'border-inv bg-inv text-invtext' : 'border-zinc-700 text-zinc-300 hover:border-zinc-500'}`}>
                  Tots
                </button>
                {sectors.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setSector(s.id)}
                    className={`rounded-full border px-3 py-1 text-xs ${sector === s.id ? 'border-inv bg-inv text-invtext' : 'border-zinc-700 text-zinc-300 hover:border-zinc-500'}`}
                  >
                    {s.name} <span className="opacity-60">{s.count}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="grid flex-1 grid-cols-1 gap-3 overflow-y-auto px-6 pb-6 sm:grid-cols-2 lg:grid-cols-3">
              {agents.length === 0 && <p className="col-span-full py-10 text-center text-sm text-zinc-500">No hi ha cap Dot amb aquesta cerca. Prova de crear-ne un amb IA.</p>}
              {agents.map((a) => (
                <div key={a.id} className="flex flex-col justify-between rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <DotAvatar bot={{ id: a.id, name: a.name }} look={a.look || undefined} size={56} alive={false} />
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold">{a.name}</div>
                        <div className="truncate text-xs text-zinc-500">{a.sector_name}</div>
                      </div>
                    </div>
                    <p className="mt-3 text-xs leading-relaxed text-zinc-400">{a.role}</p>
                    <ul className="mt-2 space-y-1 text-xs text-zinc-500">
                      {a.starters.slice(0, 2).map((s) => <li key={s} className="truncate">“{s}”</li>)}
                    </ul>
                  </div>
                  <button
                    type="button"
                    disabled={busy === a.id}
                    onClick={() => add(a)}
                    className="mt-4 flex items-center justify-center gap-2 rounded-full bg-inv px-4 py-2 text-sm font-semibold text-invtext transition hover:bg-zinc-200 disabled:opacity-50"
                  >
                    <FiPlus /> {busy === a.id ? 'Afegint…' : 'Afegeix'}
                  </button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <form onSubmit={createWithAi} className="flex flex-1 flex-col gap-4 px-6 py-6">
            <label htmlFor="ai-desc" className="text-sm text-zinc-300">Explica què ha de fer el teu Dot i per a quina feina o negoci.</label>
            <textarea
              id="ai-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={6}
              placeholder="Per exemple: un assistent per a la meva fisioteràpia que respongui dubtes de pacients, expliqui exercicis i m'ajudi a donar cites."
              className="w-full resize-none rounded-2xl border border-zinc-800 bg-zinc-900 p-4 text-sm outline-none focus:border-zinc-500"
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-zinc-500">El dissenyarà amb el model configurat: nom, coneixements, límits i preguntes d&apos;exemple.</span>
              <button
                type="submit"
                disabled={busy === 'ai' || description.trim().length < 8}
                className="rounded-full bg-inv px-5 py-2.5 text-sm font-semibold text-invtext transition hover:bg-zinc-200 disabled:opacity-40"
              >
                {busy === 'ai' ? 'Dissenyant…' : 'Crea el Dot'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
