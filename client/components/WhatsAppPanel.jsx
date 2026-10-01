'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { FiCheck, FiCopy, FiExternalLink, FiTrash2 } from 'react-icons/fi';
import {
  createWhatsAppConnection,
  deleteWhatsAppConnection,
  fetchBots,
  fetchWhatsAppConnections,
  testWhatsAppConnection,
  updateWhatsAppConnection,
} from '../lib/api';

const EMPTY = {
  label: 'El meu WhatsApp',
  bot_id: 'auto',
  phone_number_id: '',
  access_token: '',
  app_secret: '',
  allowed_numbers: '',
};

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-zinc-300">{label}</span>
      {hint && <span className="mt-0.5 block text-[11px] text-zinc-500">{hint}</span>}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

const input = 'w-full rounded-xl border border-line1 bg-surf2 px-3 py-2 text-sm text-fg outline-none placeholder-zinc-500 focus:border-zinc-500';

/** A value to paste into Meta, with a button that copies it. */
function Copyable({ label, value, missing }) {
  const [done, setDone] = useState(false);
  if (!value) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
        <b className="block text-amber-200">{label}</b>
        {missing}
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-line1 bg-surf2 p-3">
      <div className="text-[11px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="mt-1 flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate font-mono text-xs text-fg">{value}</code>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard?.writeText(value).then(() => {
              setDone(true);
              setTimeout(() => setDone(false), 1600);
            }).catch(() => {});
          }}
          className="flex items-center gap-1 rounded-lg border border-line2 px-2 py-1 text-[11px] text-zinc-300 hover:border-zinc-400 hover:text-fg"
        >
          {done ? <FiCheck className="text-emerald-400" /> : <FiCopy />} {done ? 'Copiat' : 'Copia'}
        </button>
      </div>
    </div>
  );
}

/** Set up and look after the WhatsApp numbers that answer with a Dot. */
export default function WhatsAppPanel() {
  const [connections, setConnections] = useState([]);
  const [bots, setBots] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [created, setCreated] = useState(null);
  const [testTo, setTestTo] = useState('');
  const [testMsg, setTestMsg] = useState('');

  const load = useCallback(() => {
    fetchWhatsAppConnections().then(setConnections).catch(() => {});
    fetchBots().then(setBots).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function connect(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const numbers = form.allowed_numbers.split(/[\n,;]+/).map((n) => n.trim()).filter(Boolean);
      if (!numbers.length) throw new Error('Posa almenys un número que pugui parlar amb el Dot: el teu.');
      const made = await createWhatsAppConnection({
        label: form.label.trim() || 'WhatsApp',
        bot_id: form.bot_id,
        auto_route: form.bot_id === 'auto',
        phone_number_id: form.phone_number_id.trim(),
        access_token: form.access_token.trim(),
        app_secret: form.app_secret.trim(),
        allowed_numbers: numbers,
      });
      setCreated(made);
      setTestTo(numbers[0]);
      setForm(EMPTY);
      load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function sendTest(id) {
    setTestMsg('Enviant…');
    try {
      await testWhatsAppConnection(id, testTo);
      setTestMsg('Enviat. Mira el teu WhatsApp.');
    } catch (err) {
      setTestMsg(err.message);
    }
  }

  async function toggle(c) {
    await updateWhatsAppConnection(c.id, { enabled: !c.enabled }).catch((e) => setError(e.message));
    load();
  }

  async function remove(c) {
    if (!window.confirm(`Segur que vols esborrar «${c.label}»? El número deixarà de respondre.`)) return;
    await deleteWhatsAppConnection(c.id).catch((e) => setError(e.message));
    if (created && created.id === c.id) setCreated(null);
    load();
  }

  const shown = created || connections[0];

  return (
    <div className="h-full overflow-y-auto bg-surf0 p-6 text-fg sm:p-10">
      <div className="mx-auto max-w-3xl space-y-8">
        <header>
          <h1 className="text-2xl font-semibold tracking-tight">Connecta el teu WhatsApp</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Enllaça un número de WhatsApp amb els teus Dots. Només respondrà a les persones que tu autoritzis.
          </p>
        </header>

        {/* ---- what you need, in order ---- */}
        <section className="rounded-2xl border border-line1 bg-surf1 p-5">
          <h2 className="text-sm font-semibold">Abans de començar</h2>
          <ol className="mt-3 space-y-2 text-sm text-zinc-300">
            <li><b className="text-fg">1.</b> Entra a <a className="text-blue-400 hover:underline" href="https://developers.facebook.com/apps" target="_blank" rel="noreferrer">developers.facebook.com <FiExternalLink className="inline" /></a>, crea una app de tipus <i>Business</i> i afegeix-hi el producte <b>WhatsApp</b>.</li>
            <li><b className="text-fg">2.</b> Allà trobaràs el <b>Phone number ID</b> i un <b>token</b> de prova. El token de prova caduca en 24 hores; per a un ús continuat en necessites un de permanent.</li>
            <li><b className="text-fg">3.</b> L&apos;<b>App secret</b> és a Configuració de l&apos;app → Bàsica.</li>
            <li><b className="text-fg">4.</b> Afegeix el teu mòbil com a número de prova i verifica&apos;l amb el codi que t&apos;enviïn.</li>
          </ol>
        </section>

        {/* ---- the form ---- */}
        <form onSubmit={connect} className="space-y-4 rounded-2xl border border-line1 bg-surf1 p-5">
          <h2 className="text-sm font-semibold">Dades de la connexió</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Nom"><input className={input} value={form.label} onChange={set('label')} /></Field>
            <Field label="Qui respon">
              <select className={input} value={form.bot_id} onChange={set('bot_id')}>
                <option value="auto">Automàtic: el Dot adequat segons la pregunta</option>
                {bots.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </Field>
            <Field label="Phone number ID" hint="El número identificador que et dona Meta, no el telèfon.">
              <input className={input} value={form.phone_number_id} onChange={set('phone_number_id')} required />
            </Field>
            <Field label="Access token" hint="Es desa xifrat i no es torna a mostrar.">
              <input className={input} type="password" value={form.access_token} onChange={set('access_token')} required autoComplete="off" />
            </Field>
            <Field label="App secret" hint="Serveix per comprovar que els missatges són de Meta.">
              <input className={input} type="password" value={form.app_secret} onChange={set('app_secret')} required autoComplete="off" />
            </Field>
            <Field label="Qui hi pot parlar" hint="Un número per línia. Ningú més rebrà resposta.">
              <textarea className={`${input} h-[42px] resize-y`} rows={1} value={form.allowed_numbers} onChange={set('allowed_numbers')} placeholder="+34 600 111 222" required />
            </Field>
          </div>
          {error && <p role="alert" className="text-sm text-red-400">{error}</p>}
          <button type="submit" disabled={busy} className="rounded-full bg-inv px-5 py-2 text-sm font-semibold text-invtext disabled:opacity-50">
            {busy ? 'Connectant…' : 'Connecta el número'}
          </button>
        </form>

        {/* ---- what to paste back into Meta ---- */}
        {shown && (
          <section className="space-y-3 rounded-2xl border border-line1 bg-surf1 p-5">
            <h2 className="text-sm font-semibold">Ara, acaba-ho a Meta</h2>
            <p className="text-sm text-zinc-400">
              A Meta → WhatsApp → Configuration → Webhook, enganxa aquests dos valors i subscriu el camp <b>messages</b>.
            </p>
            <Copyable
              label="Callback URL"
              value={shown.webhook_url}
              missing="El servidor no sap quina és la seva adreça pública. Posa PUBLIC_BASE_URL a les variables d'entorn del servidor i torna a carregar; mentrestant, l'adreça és la del teu servidor seguida de /api/v1/whatsapp/webhook/{id}."
            />
            <Copyable label="Verify token" value={shown.verify_token} />
            <div className="pt-1">
              <Field label="Prova-ho" hint="T'enviem un missatge al número que diguis per veure que tot va bé.">
                <div className="flex flex-wrap gap-2">
                  <input className={`${input} max-w-xs`} value={testTo} onChange={(e) => setTestTo(e.target.value)} placeholder="+34 600 111 222" />
                  <button type="button" onClick={() => sendTest(shown.id)} className="rounded-full border border-line2 px-4 py-2 text-sm text-zinc-200 hover:border-zinc-400">
                    Envia una prova
                  </button>
                </div>
              </Field>
              {testMsg && <p className="mt-2 text-xs text-zinc-400">{testMsg}</p>}
            </div>
          </section>
        )}

        {/* ---- what is connected ---- */}
        <section className="rounded-2xl border border-line1 bg-surf1 p-5">
          <h2 className="mb-3 text-sm font-semibold">Números connectats</h2>
          {connections.length === 0 && <p className="text-sm text-zinc-500">Encara no n&apos;hi ha cap.</p>}
          <ul className="space-y-2">
            {connections.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-line1 bg-surf2 p-3">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{c.label}</div>
                  <div className="truncate text-xs text-zinc-500">
                    {c.auto_route ? 'Tria el Dot automàticament' : (bots.find((b) => b.id === c.bot_id)?.name || c.bot_id)}
                    {' · '}{c.allowed_numbers.length} número{c.allowed_numbers.length === 1 ? '' : 's'} autoritzat{c.allowed_numbers.length === 1 ? '' : 's'}
                  </div>
                </div>
                <button type="button" onClick={() => toggle(c)}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${c.enabled ? 'bg-emerald-500/15 text-emerald-300' : 'bg-zinc-500/20 text-zinc-400'}`}>
                  {c.enabled ? 'Actiu · pausa' : 'Pausat · activa'}
                </button>
                <button type="button" onClick={() => remove(c)} title="Esborra"
                  className="rounded-lg p-2 text-zinc-500 hover:bg-surf3 hover:text-red-400">
                  <FiTrash2 />
                </button>
              </li>
            ))}
          </ul>
        </section>

        <p className="text-xs text-zinc-500">
          El token i el secret es guarden xifrats al servidor. Cada missatge de Meta es comprova amb signatura abans de fer-ne cas,
          i cada persona té el seu fil de conversa separat.
        </p>
      </div>
    </div>
  );
}
