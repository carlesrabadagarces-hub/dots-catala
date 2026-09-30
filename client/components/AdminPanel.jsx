'use client';

import Link from 'next/link';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchAdminStats, updateAdminUser } from '../lib/api';

const nf = new Intl.NumberFormat('ca-ES');
const fmt = (n) => nf.format(Math.round(n || 0));
const compact = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)} k` : String(Math.round(n || 0)));

function Kpi({ label, value, hint, tone }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
      <div className="text-[11px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tracking-tight ${tone || ''}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </div>
  );
}

function Bars({ data, valueKey, color }) {
  const max = Math.max(1, ...data.map((d) => d[valueKey]));
  const w = 720;
  const h = 150;
  const step = w / data.length;
  return (
    <svg viewBox={`0 0 ${w} ${h + 22}`} className="w-full" role="img" aria-label={`Gràfic diari de ${valueKey}`}>
      {[0, 0.5, 1].map((t) => (
        <line key={t} x1="0" x2={w} y1={h - t * h} y2={h - t * h} stroke="rgb(var(--line-1))" strokeDasharray="3 5" />
      ))}
      {data.map((d, i) => {
        const bh = (d[valueKey] / max) * (h - 6);
        return (
          <g key={d.date}>
            <rect x={i * step + 1.5} y={h - bh} width={Math.max(2, step - 3)} height={bh} rx="2" fill={color}>
              <title>{`${d.date}: ${fmt(d[valueKey])}`}</title>
            </rect>
          </g>
        );
      })}
      <text x="0" y={h + 16} fontSize="10" fill="rgb(var(--z-500))">{data[0]?.date}</text>
      <text x={w} y={h + 16} fontSize="10" fill="rgb(var(--z-500))" textAnchor="end">{data[data.length - 1]?.date}</text>
      <text x={w} y="10" fontSize="10" fill="rgb(var(--z-500))" textAnchor="end">màx {fmt(max)}</text>
    </svg>
  );
}

function Table({ head, rows, empty }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-[11px] uppercase tracking-widest text-zinc-500">
            {head.map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={head.length} className="px-3 py-6 text-center text-zinc-500">{empty}</td></tr>}
          {rows}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminPanel() {
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('tokens');
  const [auto, setAuto] = useState(true);
  const [updated, setUpdated] = useState(0);

  const load = useCallback(() => {
    fetchAdminStats(days).then((s) => { setStats(s); setError(''); setUpdated(Date.now()); }).catch((e) => setError(e.message));
  }, [days]);

  useEffect(() => {
    load();
    if (!auto) return undefined;
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load, auto]);

  const members = useMemo(() => {
    if (!stats) return [];
    const q = query.trim().toLowerCase();
    const list = stats.users.filter((u) => !q || `${u.name} ${u.email || ''} ${u.provider}`.toLowerCase().includes(q));
    const by = { tokens: (a, b) => b.tokens - a.tokens, today: (a, b) => b.tokens_today - a.tokens_today, dots: (a, b) => b.dots - a.dots, recent: (a, b) => String(b.last_seen || '').localeCompare(String(a.last_seen || '')), name: (a, b) => String(a.name).localeCompare(String(b.name)) };
    return [...list].sort(by[sort] || by.tokens);
  }, [stats, query, sort]);

  function exportCsv() {
    const rows = [['nom', 'correu', 'proveïdor', 'dots', 'missatges', 'tokens', 'tokens_avui', 'limit_diari', 'estat']];
    members.forEach((u) => rows.push([u.name, u.email || '', u.provider, u.dots, u.messages, u.tokens, u.tokens_today, u.token_limit ?? '', u.disabled ? 'suspès' : 'actiu']));
    const csv = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `superdotats-membres-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function control(user, body) {
    setBusy(user.id);
    try {
      await updateAdminUser(user.id, body);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  if (error && !stats) return <div className="p-10 text-red-400">{error}</div>;
  if (!stats) return <div className="p-10 text-zinc-400">Carregant…</div>;
  const t = stats.totals;

  return (
    <div className="min-h-screen overflow-y-auto bg-surf0 p-4 text-zinc-100 sm:p-8" style={{ fontFamily: 'Geist, Helvetica Neue, Arial, sans-serif' }}>
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-300">← Torna a l&apos;app</Link>
            <h1 className="text-3xl font-semibold tracking-tight">Panell d&apos;administració</h1>
            <p className="text-xs text-zinc-500">Actualitzat {new Date(stats.generated_at).toLocaleTimeString('ca-ES')} · {stats.token_note}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={load} className="rounded-full border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:border-zinc-500" title="Actualitza ara">↻ Actualitza</button>
            <label className="flex cursor-pointer items-center gap-1.5 rounded-full border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300">
              <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} className="accent-emerald-500" /> Auto 30 s
            </label>
            {[7, 30, 90].map((d) => (
              <button key={d} type="button" onClick={() => setDays(d)} aria-pressed={days === d}
                className={`rounded-full border px-4 py-1.5 text-sm ${days === d ? 'border-inv bg-inv text-invtext' : 'border-zinc-700 text-zinc-300 hover:border-zinc-500'}`}>
                {d} dies
              </button>
            ))}
          </div>
        </header>
        {error && <p role="alert" className="text-sm text-red-400">{error}</p>}

        <section aria-label="Resum" className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Kpi label="Membres" value={fmt(t.members)} hint={`${fmt(t.active_7d)} actius en 7 dies`} />
          <Kpi label="Dots creats" value={fmt(t.dots)} hint={`${t.members ? (t.dots / t.members).toFixed(1) : 0} per membre`} />
          <Kpi label="Missatges" value={compact(t.messages)} />
          <Kpi label="Peticions al model" value={compact(t.requests)} hint={`${days} dies`} />
          <Kpi label="Tokens (est.)" value={compact(t.tokens_in + t.tokens_out)} hint={`${compact(t.tokens_in)} entrada · ${compact(t.tokens_out)} sortida`} />
          <Kpi label="Cost estimat" value={`${t.est_cost_usd.toFixed(2)} $`} hint="Segons els preus configurats" />
          <Kpi label="Latència" value={`${(t.avg_latency_ms / 1000).toFixed(1)} s`} hint={`mediana ${(t.p50_latency_ms / 1000).toFixed(1)} s · p95 ${(t.p95_latency_ms / 1000).toFixed(1)} s`} />
          <Kpi label="Errors" value={`${(t.error_rate * 100).toFixed(1)} %`} hint={`${fmt(t.errors)} peticions`} tone={t.error_rate > 0.05 ? 'text-red-400' : 'text-emerald-400'} />
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
            <h2 className="mb-2 text-sm font-semibold">Peticions per dia</h2>
            <Bars data={stats.daily} valueKey="requests" color="#2f7bff" />
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
            <h2 className="mb-2 text-sm font-semibold">Tokens per dia</h2>
            <Bars data={stats.daily} valueKey="tokens" color="#7a4cf0" />
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 md:col-span-2">
            <h2 className="mb-2 text-sm font-semibold">Models</h2>
            <Table head={['Model', 'Peticions', 'Tokens', 'Errors']} empty="Encara no hi ha activitat."
              rows={stats.by_model.map((m) => (
                <tr key={m.model} className="border-b border-zinc-800/60"><td className="px-3 py-2">{m.model}</td><td className="px-3 py-2">{fmt(m.requests)}</td><td className="px-3 py-2">{compact(m.tokens)}</td><td className="px-3 py-2">{fmt(m.errors)}</td></tr>
              ))} />
          </div>
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
            <h2 className="mb-2 text-sm font-semibold">Canals</h2>
            <Table head={['Canal', 'Peticions']} empty="—"
              rows={stats.by_channel.map((c) => (
                <tr key={c.channel} className="border-b border-zinc-800/60"><td className="px-3 py-2 capitalize">{c.channel}</td><td className="px-3 py-2">{fmt(c.requests)}</td></tr>
              ))} />
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <h2 className="mb-2 text-sm font-semibold">Dots més actius</h2>
          <Table head={['Dot', 'Propietari', 'Peticions', 'Tokens', 'Errors']} empty="Encara no hi ha activitat."
            rows={stats.top_dots.map((d) => (
              <tr key={d.id} className="border-b border-zinc-800/60"><td className="px-3 py-2">{d.name}</td><td className="px-3 py-2 text-zinc-400">{d.owner}</td><td className="px-3 py-2">{fmt(d.requests)}</td><td className="px-3 py-2">{compact(d.tokens)}</td><td className="px-3 py-2">{fmt(d.errors)}</td></tr>
            ))} />
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <h2 className="mb-1 text-sm font-semibold">Membres i control</h2>
          <p className="mb-3 text-xs text-zinc-500">Pots suspendre un compte o limitar-ne els tokens diaris (buit = sense límit).</p>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Cerca per nom o correu…" aria-label="Cerca membres" className="min-w-[14rem] flex-1 rounded-full border border-zinc-700 bg-zinc-950 px-4 py-1.5 text-sm outline-none focus:border-zinc-400" />
            <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Ordena" className="rounded-full border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-sm">
              <option value="tokens">Més tokens</option><option value="today">Més actius avui</option><option value="dots">Més Dots</option><option value="recent">Vistos fa poc</option><option value="name">Nom (A–Z)</option>
            </select>
            <button type="button" onClick={exportCsv} className="rounded-full border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 hover:border-zinc-500">⭳ Exporta CSV</button>
            <span className="text-xs text-zinc-500">{members.length} de {stats.users.length}</span>
          </div>
          <Table head={['Membre', 'Dots', 'Missatges', 'Tokens', 'Avui', 'Límit diari', 'Estat']} empty="Encara no hi ha membres."
            rows={members.map((u) => (
              <tr key={u.id} className="border-b border-zinc-800/60">
                <td className="px-3 py-2">
                  <div className="font-medium">{u.name}{u.role === 'admin' && <span className="ml-2 rounded-full bg-zinc-800 px-2 py-0.5 text-[10px]">admin</span>}</div>
                  <div className="text-xs text-zinc-500">{u.email || u.provider}{u.last_seen ? ` · vist ${new Date(u.last_seen).toLocaleDateString('ca-ES')}` : ''}</div>
                </td>
                <td className="px-3 py-2">{fmt(u.dots)}</td>
                <td className="px-3 py-2">{fmt(u.messages)}</td>
                <td className="px-3 py-2">
                  {compact(u.tokens)}
                  <div className="mt-1 h-1 w-20 overflow-hidden rounded-full bg-zinc-800"><div className="h-full rounded-full bg-blue-500" style={{ width: `${Math.min(100, (u.tokens / Math.max(1, ...stats.users.map((x) => x.tokens))) * 100)}%` }} /></div>
                </td>
                <td className="px-3 py-2">{compact(u.tokens_today)}</td>
                <td className="px-3 py-2">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const value = new FormData(e.currentTarget).get('limit');
                      control(u, value === '' ? { clear_token_limit: true } : { token_limit: Number(value) });
                    }}
                    className="flex items-center gap-1"
                  >
                    <input name="limit" type="number" min="0" defaultValue={u.token_limit ?? ''} aria-label={`Límit diari de ${u.name}`} className="w-24 rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1 text-xs" />
                    <button type="submit" disabled={busy === u.id} className="rounded-lg border border-zinc-700 px-2 py-1 text-xs hover:border-zinc-400">Desa</button>
                  </form>
                </td>
                <td className="px-3 py-2">
                  {u.role === 'admin' ? <span className="text-xs text-zinc-500">—</span> : (
                    <button type="button" disabled={busy === u.id} onClick={() => control(u, { disabled: !u.disabled })}
                      className={`rounded-full px-3 py-1 text-xs font-medium ${u.disabled ? 'bg-red-500/20 text-red-300' : 'bg-emerald-500/15 text-emerald-300'}`}>
                      {u.disabled ? 'Suspès · reactiva' : 'Actiu · suspèn'}
                    </button>
                  )}
                </td>
              </tr>
            ))} />
        </section>
      </div>
    </div>
  );
}
