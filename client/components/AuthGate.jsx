'use client';

import ThemeToggle from './ThemeToggle';
import Link from 'next/link';
import React, { useEffect, useState } from 'react';
import DotAvatar from './DotAvatar';
import { getAuthStatus, oauthStartUrl, loginWithToken, loginWithPassword, registerAccount, logout } from '../lib/api';

const CAST = [
  { look: { body: 'arch', tone: 'pink', hat: 'tophat', accessory: 'bowtie' }, size: 150, style: { left: '6%', top: '12%' } },
  { look: { body: 'blob', tone: 'blue', glasses: 'shades' }, size: 170, style: { right: '7%', top: '9%' }, delay: 1 },
  { look: { body: 'cube', tone: 'teal', hat: 'chef', accessory: 'mustache' }, size: 140, style: { left: '10%', bottom: '10%' }, delay: 2 },
  { look: { body: 'blob', tone: 'violet', hat: 'wizard' }, size: 160, style: { right: '10%', bottom: '11%' }, delay: 0.5 },
  { look: { body: 'arch', tone: 'yellow', hat: 'crown', accessory: 'bowtie' }, size: 120, style: { left: '21%', top: '3%' }, delay: 1.5 },
  { look: { body: 'cube', tone: 'slate', glasses: 'shades' }, size: 110, style: { right: '27%', bottom: '3%' }, delay: 2.5 },
  { look: { body: 'blob', tone: 'orange', hat: 'hardhat' }, size: 70, style: { left: '3%', top: '52%' }, delay: 1 },
  { look: { body: 'arch', tone: 'green' }, size: 70, style: { right: '3%', top: '46%' }, delay: 2 },
];

function Mascot({ look, size, style, delay = 0 }) {
  return (
    <div aria-hidden="true" style={{ position: 'absolute', animation: `sd-float ${5 + delay}s ease-in-out ${delay}s infinite`, ...style }}>
      <DotAvatar look={look} size={size} alive={false} />
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.6c0-1.6-.1-3.1-.4-4.6H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.6 5.9c4.4-4.1 7-10.1 7-17.5z" />
      <path fill="#FBBC05" d="M10.5 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.9-4.7l-7.9-6.1A24 24 0 0 0 0 24c0 3.9.9 7.5 2.6 10.8l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.6-5.9c-2.1 1.4-4.9 2.3-8.3 2.3-6.3 0-11.6-4.1-13.5-9.8l-7.9 6.1C6.5 42.6 14.6 48 24 48z" />
    </svg>
  );
}

function AppleMark() {
  return (
    <svg width="18" height="20" viewBox="0 0 384 512" aria-hidden="true" fill="currentColor">
      <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z" />
    </svg>
  );
}

function Login({ providers, error }) {
  const [token, setToken] = useState('');
  const [localError, setLocalError] = useState('');
  const none = !providers.google && !providers.apple;
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');

  async function submitPassword(e) {
    e.preventDefault();
    setLocalError('');
    setBusy(true);
    try {
      if (creating) await registerAccount(username.trim(), password, name.trim());
      else await loginWithPassword(username.trim(), password);
      window.location.reload();
    } catch (err) {
      setLocalError(err.message);
      setBusy(false);
    }
  }

  async function submitToken(e) {
    e.preventDefault();
    setLocalError('');
    try {
      await loginWithToken(token.trim());
      window.location.reload();
    } catch {
      setLocalError('Token no vàlid.');
    }
  }

  const btn = 'flex w-full items-center justify-center gap-3 rounded-full px-6 py-3.5 text-[15px] font-semibold transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0';

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-white text-[#0a0a0a]" style={{ fontFamily: 'Geist, Helvetica Neue, Arial, sans-serif' }}>
      <style>{`@keyframes sd-float{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-14px) rotate(3deg)}}`}</style>
      {CAST.map((c, i) => <Mascot key={i} {...c} />)}
      <div className="relative z-10 flex h-full flex-col items-center justify-center px-6 text-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.png" alt="" width="92" height="92" className="mb-3" />
        <div className="font-mono text-xs uppercase tracking-[0.12em] text-neutral-500">Privat · Segur · Fàcil</div>
        <h1 className="mt-4 text-5xl font-semibold tracking-[-0.045em] sm:text-7xl">super<span className="font-bold">DOT</span>ats</h1>
        <p className="mt-4 max-w-md text-lg text-neutral-500">Un Dot per a cada dubte. Entra i comença.</p>

        <div className="mt-8 flex w-full max-w-xs flex-col gap-3">
          <a
            href={providers.apple ? oauthStartUrl('apple') : undefined}
            aria-disabled={!providers.apple}
            className={`${btn} bg-black text-white ${providers.apple ? '' : 'pointer-events-none opacity-40'}`}
          >
            <AppleMark /> Continua amb Apple
          </a>
          <a
            href={providers.google ? oauthStartUrl('google') : undefined}
            aria-disabled={!providers.google}
            className={`${btn} border border-neutral-300 bg-white text-black ${providers.google ? '' : 'pointer-events-none opacity-40'}`}
          >
            <GoogleMark /> Continua amb Google
          </a>
        </div>

        {(error || localError) && <p role="alert" className="mt-4 text-sm text-red-600">{error || localError}</p>}
        {none && !providers.local && !providers.signup && (
          <p className="mt-4 max-w-xs text-sm text-neutral-500">L&apos;inici de sessió no està configurat en aquest servidor.</p>
        )}

        {(providers.password || providers.admin || providers.signup) && (
          <form onSubmit={submitPassword} className="mt-8 flex w-full max-w-xs flex-col gap-2">
            <label htmlFor="sd-user" className="font-mono text-[11px] uppercase tracking-widest text-neutral-500">{creating ? 'Crea el teu compte' : 'Entra amb correu i contrasenya'}</label>
            {creating && (
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Com et diem?"
                autoComplete="name"
                aria-label="Nom"
                className="rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-black"
              />
            )}
            <input
              id="sd-user"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={creating ? 'Correu electrònic' : 'Correu (o admin)'}
              autoComplete={creating ? 'email' : 'username'}
              className="rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-black"
            />
            <div className="flex gap-2">
              <input
                id="sd-pass"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={creating ? 'Contrasenya (mín. 8)' : 'Contrasenya'}
                autoComplete={creating ? 'new-password' : 'current-password'}
                minLength={creating ? 8 : undefined}
                aria-label="Contrasenya"
                className="min-w-0 flex-1 rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-black"
              />
              <button type="submit" disabled={busy || !password} className="rounded-full bg-black px-5 text-sm font-semibold text-white disabled:opacity-40">{creating ? 'Crea' : 'Entra'}</button>
            </div>
            {providers.signup && (
              <button type="button" onClick={() => { setCreating((v) => !v); setLocalError(''); }}
                className="text-center text-xs text-neutral-500 underline-offset-2 hover:underline">
                {creating ? 'Ja tinc compte' : 'No tens compte? Crea\'n un'}
              </button>
            )}
            {providers.dev_hint && (
              <p className="text-center font-mono text-[11px] text-neutral-400">Mode prova local: admin + admin</p>
            )}
          </form>
        )}

        {providers.local && (
          <form onSubmit={submitToken} className="mt-8 flex w-full max-w-xs flex-col gap-2">
            <label htmlFor="sd-token" className="font-mono text-[11px] uppercase tracking-widest text-neutral-500">
              {none ? 'Accés local (sense Google ni Apple)' : 'Accés local'}
            </label>
            <div className="flex gap-2">
              <input
                id="sd-token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Token del propietari"
                className="min-w-0 flex-1 rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-black"
              />
              <button type="submit" className="rounded-full bg-black px-5 text-sm font-semibold text-white">Entra</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default function AuthGate({ children, requireAdmin = false }) {
  const [state, setState] = useState({ loading: true });
  const [error, setError] = useState('');

  useEffect(() => {
    const url = new URL(window.location.href);
    const err = url.searchParams.get('login_error');
    if (err) {
      setError(err);
      url.searchParams.delete('login_error');
      window.history.replaceState({}, '', url.pathname + url.search);
    }
    getAuthStatus()
      .then((s) => setState({ loading: false, ...s }))
      .catch(() => setState({ loading: false, offline: true, providers: {} }));
  }, []);

  if (state.loading) {
    return <div className="fixed inset-0 bg-white" aria-busy="true" />;
  }
  if (state.offline) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white p-6 text-center text-neutral-600">
        No es pot contactar amb el servidor. Comprova que està en marxa i torna-ho a provar.
      </div>
    );
  }
  if (!state.authenticated) {
    return <Login providers={state.providers || {}} error={error} />;
  }

  const user = state.user || {};
  const isAdmin = user.role === 'admin' || user.role === 'owner';
  if (requireAdmin && !isAdmin) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-white p-6 text-center text-neutral-700">
        <p>Aquesta zona és només per a administradors.</p>
        <Link href="/" className="rounded-full bg-black px-5 py-2.5 text-sm font-semibold text-white">Torna a l&apos;app</Link>
      </div>
    );
  }
  const label = user.name || user.email || (user.role === 'owner' ? 'Propietari' : 'Compte');
  return (
    <>
      {children}
      {user.role === 'admin' && !requireAdmin && (
        <a href="/admin" className="fixed right-3 top-12 z-40 rounded-full bg-white px-3 py-1 text-xs font-semibold text-black shadow">Panell d&apos;admin</a>
      )}
      {user.role === 'owner' && <ThemeToggle className="fixed right-3 top-3 z-40 border border-fg/15 bg-surf2" />}
      {user.role !== 'owner' && (
        <div className="fixed right-3 top-3 z-40 flex items-center gap-2 rounded-full border border-white/10 bg-black/70 py-1 pl-1 pr-3 text-xs text-white backdrop-blur">
          {user.picture ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.picture} alt="" className="h-6 w-6 rounded-full" referrerPolicy="no-referrer" />
          ) : (
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20">{label.charAt(0).toUpperCase()}</span>
          )}
          <span className="max-w-[9rem] truncate">{label}</span>
          <ThemeToggle className="text-white" />
          <button
            type="button"
            className="ml-1 underline-offset-2 hover:underline"
            onClick={async () => { await logout(); window.location.reload(); }}
          >
            Sortir
          </button>
        </div>
      )}
    </>
  );
}
