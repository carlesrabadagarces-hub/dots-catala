/* Gives an SVG Dot its own life: it breathes, blinks, follows the pointer with its eyes,
   gets happy when touched, falls asleep when nobody is around and wakes up on movement.
   Pure DOM, no dependencies; the landing page inlines this file. */

export const DOT_LIFE_CSS = `
.dl{--lx:0;--ly:0}
.dl svg{overflow:visible;display:block}
.dl .dl-all{transform-box:fill-box;transform-origin:50% 100%;animation:dl-breathe var(--dl-speed,3.6s) ease-in-out var(--dl-delay,0s) infinite}
.dl .dl-eyes{transform-box:fill-box;transform-origin:center;transform:translate(calc(var(--lx)*3px),calc(var(--ly)*2px));transition:transform .14s ease-out}
.dl.dl-blink .dl-eyes{transform:translate(calc(var(--lx)*3px),calc(var(--ly)*2px)) scaleY(.08)}
.dl[data-state=sleepy] .dl-eyes{transform:translate(0,2px) scaleY(.22)}
.dl[data-state=sleepy] .dl-all{animation-duration:6s}
.dl[data-state=happy] .dl-all{animation:dl-hop .55s cubic-bezier(.2,.8,.3,1)}
.dl[data-state=talking] .dl-mouth{transform-box:fill-box;transform-origin:center;animation:dl-talk .28s ease-in-out infinite}
.dl[data-state=thinking] .dl-eyes{transform:translate(-3px,-3px)}
.dl .dl-arms{transform-box:fill-box;transform-origin:50% 40%;animation:dl-sway 4.4s ease-in-out var(--dl-delay,0s) infinite}
.dl .dl-shadow{transform-box:fill-box;transform-origin:center}
@keyframes dl-breathe{0%,100%{transform:scale(1,1)}50%{transform:scale(1.03,.97)}}
@keyframes dl-hop{0%{transform:scale(1.1,.86)}30%{transform:translateY(-16%) scale(.94,1.1)}60%{transform:translateY(0) scale(1.08,.9)}100%{transform:scale(1,1)}}
@keyframes dl-talk{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.5)}}
@keyframes dl-sway{0%,100%{transform:rotate(-2deg)}50%{transform:rotate(3deg)}}
@media (prefers-reduced-motion:reduce){.dl .dl-all,.dl .dl-arms,.dl[data-state=talking] .dl-mouth{animation:none}}
`;

const registry = new Set();
let started = false;
let lastActivity = Date.now();
let frame = 0;
let pointer = null;

function tick() {
  frame = 0;
  if (!pointer) return;
  registry.forEach((entry) => {
    const r = entry.el.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight) return;
    const dx = pointer.x - (r.left + r.width / 2);
    const dy = pointer.y - (r.top + r.height / 2);
    const d = Math.hypot(dx, dy) || 1;
    const k = Math.min(1, d / 220);
    entry.el.style.setProperty('--lx', ((dx / d) * k).toFixed(3));
    entry.el.style.setProperty('--ly', ((dy / d) * k).toFixed(3));
  });
}

function wake() {
  lastActivity = Date.now();
  registry.forEach((entry) => {
    if (entry.el.dataset.state === 'sleepy') entry.el.dataset.state = 'idle';
  });
}

function start() {
  if (started || typeof window === 'undefined') return;
  started = true;
  window.addEventListener('pointermove', (e) => {
    pointer = { x: e.clientX, y: e.clientY };
    wake();
    if (!frame) frame = requestAnimationFrame(tick);
  }, { passive: true });
  window.addEventListener('keydown', wake, { passive: true });
  window.addEventListener('scroll', wake, { passive: true });
  setInterval(() => {
    if (Date.now() - lastActivity > 25000) {
      registry.forEach((entry) => {
        if (!entry.el.dataset.state || entry.el.dataset.state === 'idle') entry.el.dataset.state = 'sleepy';
      });
    }
  }, 4000);
}

export function ensureLifeStyles() {
  if (typeof document === 'undefined' || document.getElementById('dot-life-css')) return;
  const style = document.createElement('style');
  style.id = 'dot-life-css';
  style.textContent = DOT_LIFE_CSS;
  document.head.appendChild(style);
}

/** Bring a container that holds a Dot SVG to life. Returns a function that stops it. */
export function attachLife(el, options = {}) {
  if (!el || typeof window === 'undefined') return () => {};
  ensureLifeStyles();
  start();
  el.classList.add('dl');
  el.style.setProperty('--dl-delay', `${-Math.random() * 3}s`);
  const entry = { el };
  registry.add(entry);
  let alive = true;

  const blink = () => {
    if (!alive) return;
    if (el.dataset.state !== 'sleepy') {
      el.classList.add('dl-blink');
      setTimeout(() => el.classList.remove('dl-blink'), 130);
      if (Math.random() < 0.18) setTimeout(() => { el.classList.add('dl-blink'); setTimeout(() => el.classList.remove('dl-blink'), 120); }, 260);
    }
    setTimeout(blink, 1800 + Math.random() * 3600);
  };
  const first = setTimeout(blink, 600 + Math.random() * 2000);

  const setState = (state, ms) => {
    el.dataset.state = state;
    if (ms) setTimeout(() => { if (alive && el.dataset.state === state) el.dataset.state = 'idle'; }, ms);
  };
  const onEnter = () => { if (!options.static) setState('happy', 600); };
  const onClick = () => { setState('happy', 600); if (options.onPoke) options.onPoke(); };
  el.addEventListener('pointerenter', onEnter);
  el.addEventListener('click', onClick);

  return () => {
    alive = false;
    clearTimeout(first);
    registry.delete(entry);
    el.removeEventListener('pointerenter', onEnter);
    el.removeEventListener('click', onClick);
    el.classList.remove('dl');
  };
}

/** Set a Dot's mood from outside: idle, talking, thinking, happy, sleepy. */
export function setMood(el, mood) {
  if (el) el.dataset.state = mood;
}
