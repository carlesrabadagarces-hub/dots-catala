'use client';

import React, { useEffect, useMemo, useRef } from 'react';
import { dotSvg, normalizeLook, OPTIONS } from '../lib/dotSvg';
import { attachLife } from '../lib/dotLife';

function hash(text) {
  let h = 0;
  for (let i = 0; i < text.length; i += 1) h = (h * 31 + text.charCodeAt(i)) >>> 0;
  return h;
}

/** Look used for Dots created before customisation existed. */
export function fallbackLook(bot) {
  const id = bot?.id || 'dot';
  const color = /^#[0-9a-fA-F]{6}$/.test(bot?.accent_color || '') ? bot.accent_color : undefined;
  return normalizeLook({ shape: OPTIONS.shape[hash(id) % OPTIONS.shape.length], color });
}

export default function DotAvatar({ bot, look, size = 40, className = '', alive = true, mood }) {
  const ref = useRef(null);
  const html = useMemo(() => dotSvg(look || bot?.look || fallbackLook(bot), size, bot?.name || 'Dot'), [look, bot, size]);
  useEffect(() => (alive && ref.current ? attachLife(ref.current) : undefined), [alive]);
  useEffect(() => {
    if (ref.current && mood) ref.current.dataset.state = mood;
    else if (ref.current && ref.current.dataset.state !== 'sleepy') ref.current.dataset.state = 'idle';
  }, [mood]);
  return (
    <span
      ref={ref}
      className={`inline-flex flex-none items-center justify-center ${className}`}
      style={{ width: size, height: size }}
      // The SVG is produced by dotSvg from a whitelisted look, never from free text.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
