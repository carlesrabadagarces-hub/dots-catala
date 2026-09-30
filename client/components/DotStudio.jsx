'use client';

import React, { useEffect, useState } from 'react';
import { FiX, FiShuffle } from 'react-icons/fi';
import DotAvatar, { fallbackLook } from './DotAvatar';
import { BODIES, TONES, TONE_COLORS, SPRITE_ITEMS, normalizeSpriteLook, isSpriteLook, randomSpriteLook } from '../lib/dotSprite';

const LABELS = {
  body: { blob: 'Gota', arch: 'Arc', cube: 'Cub' },
  tone: { pink: 'Rosa', orange: 'Taronja', yellow: 'Groc', green: 'Verd', teal: 'Verd atzur', blue: 'Blau', violet: 'Violeta', slate: 'Pissarra' },
  hat: { none: 'Cap', cap: 'Gorra', beanie: 'Gorro', tophat: 'Barret de copa', crown: 'Corona', party: 'Festa', cowboy: 'Vaquer', wizard: 'Mag', chef: 'Cuiner', graduation: 'Birret', hardhat: 'Casc', antenna: 'Antena', flower: 'Flor' },
  glasses: { none: 'Cap', round: 'Rodones', square: 'Quadrades', shades: 'De sol', monocle: 'Monocle', visor: 'Visera' },
  accessory: { none: 'Cap', bowtie: 'Pajarita', tie: 'Corbata', scarf: 'Bufanda', stethoscope: 'Fonendoscopi', headphones: 'Auriculars', mustache: 'Bigoti', badge: 'Insígnia', cape: 'Capa' },
};

const SECTIONS = [['hat', 'Barret'], ['glasses', 'Ulleres'], ['accessory', 'Complements']];

export default function DotStudio({ bot, onClose, onSave }) {
  const initial = () => normalizeSpriteLook(isSpriteLook(bot?.look) ? bot.look : { ...fallbackLook(bot), ...(bot?.look || {}), body: fallbackLook(bot).body });
  const [look, setLook] = useState(initial);
  const [name, setName] = useState(bot?.name || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setLook(initial());
    setName(bot?.name || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bot?.id]);

  if (!bot) return null;
  const set = (key, value) => setLook((prev) => ({ ...prev, [key]: value }));

  async function save() {
    setSaving(true);
    setError('');
    try {
      await onSave(bot.id, { look, name: name.trim() || bot.name });
      onClose();
    } catch (e) {
      setError(e.message || 'No s\'ha pogut desar.');
    } finally {
      setSaving(false);
    }
  }

  const chip = (active) => `flex flex-col items-center gap-1 rounded-2xl border p-2 text-[11px] transition ${active ? 'border-white bg-zinc-800' : 'border-zinc-800 hover:border-zinc-600'}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Personalitza el Dot">
      <div className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-zinc-800 bg-[#0e0e10] text-zinc-100 shadow-2xl md:flex-row">
        <div className="flex flex-col items-center justify-center gap-4 border-b border-zinc-800 bg-gradient-to-b from-zinc-800 to-[#0e0e10] p-6 md:w-80 md:border-b-0 md:border-r">
          <DotAvatar bot={bot} look={look} size={260} />
          <label htmlFor="dot-name" className="sr-only">Nom del Dot</label>
          <input
            id="dot-name"
            value={name}
            maxLength={60}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-full border border-zinc-700 bg-zinc-900 px-4 py-2 text-center text-sm font-semibold outline-none focus:border-zinc-400"
          />
          <button type="button" onClick={() => setLook(randomSpriteLook())} className="flex items-center gap-2 rounded-full border border-zinc-700 px-4 py-2 text-sm hover:border-zinc-400">
            <FiShuffle /> Sorpresa
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-zinc-800 px-6 py-4">
            <h2 className="text-lg font-semibold tracking-tight">Personalitza el teu Dot</h2>
            <button type="button" onClick={onClose} aria-label="Tanca" className="rounded-full p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white"><FiX /></button>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-zinc-500">Cos</h3>
              <div className="grid grid-cols-3 gap-2">
                {BODIES.map((b) => (
                  <button key={b} type="button" aria-pressed={look.body === b} onClick={() => set('body', b)} className={chip(look.body === b)}>
                    <DotAvatar look={{ ...look, body: b, hat: 'none', glasses: 'none', accessory: 'none' }} size={72} bot={{ name: LABELS.body[b] }} alive={false} />
                    <span className="text-zinc-300">{LABELS.body[b]}</span>
                  </button>
                ))}
              </div>
            </section>

            <section>
              <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-zinc-500">Color</h3>
              <div className="flex flex-wrap gap-2">
                {TONES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    aria-label={LABELS.tone[t]}
                    title={LABELS.tone[t]}
                    aria-pressed={look.tone === t}
                    onClick={() => set('tone', t)}
                    className={`h-9 w-9 rounded-full border-2 ${look.tone === t ? 'border-white' : 'border-transparent'}`}
                    style={{ background: TONE_COLORS[t] }}
                  />
                ))}
              </div>
            </section>

            {SECTIONS.map(([key, title]) => (
              <section key={key}>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-zinc-500">{title}</h3>
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-5">
                  {SPRITE_ITEMS[key].map((value) => (
                    <button key={value} type="button" aria-pressed={look[key] === value} onClick={() => set(key, value)} className={chip(look[key] === value)}>
                      <DotAvatar look={{ ...look, [key]: value }} size={64} bot={{ name: LABELS[key][value] }} alive={false} />
                      <span className="truncate text-zinc-300">{LABELS[key][value]}</span>
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-zinc-800 px-6 py-4">
            <span role="alert" className="text-sm text-red-400">{error}</span>
            <div className="flex gap-2">
              <button type="button" onClick={onClose} className="rounded-full border border-zinc-700 px-5 py-2 text-sm hover:border-zinc-400">Cancel·la</button>
              <button type="button" disabled={saving} onClick={save} className="rounded-full bg-white px-5 py-2 text-sm font-semibold text-black hover:bg-zinc-200 disabled:opacity-50">
                {saving ? 'Desant…' : 'Desa'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
