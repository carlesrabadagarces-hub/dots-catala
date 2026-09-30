'use client';

import React, { useEffect, useState } from 'react';

function apply(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('sd-theme', theme); } catch { /* private mode */ }
}

/** Switch between the soft dark theme and the grey light theme. */
export default function ThemeToggle({ className = '' }) {
  const [theme, setTheme] = useState('dark');
  useEffect(() => { setTheme(document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'); }, []);
  const next = theme === 'light' ? 'dark' : 'light';
  return (
    <button
      type="button"
      onClick={() => { apply(next); setTheme(next); }}
      title={next === 'light' ? 'Mode clar (gris)' : 'Mode fosc'}
      aria-label={next === 'light' ? 'Canvia al mode clar' : 'Canvia al mode fosc'}
      className={`flex h-7 w-7 items-center justify-center rounded-full text-sm transition hover:bg-fg/10 ${className}`}
    >
      <span aria-hidden="true">{theme === 'light' ? '🌙' : '☀️'}</span>
    </button>
  );
}
