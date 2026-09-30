/* Dot avatars: one function draws any look as an SVG string (body in a 100x100 box, room around it for hats and capes).
   The same file is inlined in the landing page, so keep it dependency-free. */

export const OPTIONS = {
  shape: ['circle', 'tri', 'drop', 'hex', 'arch', 'square'],
  eyes: ['pill', 'round', 'happy', 'sleepy', 'wide', 'wink', 'heart'],
  mouth: ['none', 'smile', 'open', 'smirk', 'tongue'],
  hat: ['none', 'cap', 'beanie', 'tophat', 'crown', 'party', 'cowboy', 'wizard', 'chef', 'graduation', 'hardhat', 'antenna', 'flower'],
  glasses: ['none', 'round', 'square', 'shades', 'monocle', 'visor'],
  accessory: ['none', 'bowtie', 'tie', 'scarf', 'stethoscope', 'headphones', 'mustache', 'blush', 'badge', 'cape'],
};

export const PALETTE = ['#ff4d7d', '#ff8a3d', '#ffc21a', '#7cd13b', '#19c3a6', '#2fb5ff', '#2f7bff', '#7a4cf0', '#c04cf0', '#52657a', '#0a0a0a', '#f4f1ea'];

export const DEFAULT_LOOK = { shape: 'circle', color: '#7a4cf0', accent: '#0a0a0a', eyes: 'pill', mouth: 'none', hat: 'none', glasses: 'none', accessory: 'none' };

const SHAPES = {
  circle: 'M50 8a42 42 0 1 0 0.01 0Z',
  tri: 'M50 10C58 10 64 16 88 66C94 79 86 90 72 90H28C14 90 6 79 12 66C36 16 42 10 50 10Z',
  drop: 'M50 6C58 24 86 40 86 62A36 36 0 0 1 14 62C14 40 42 24 50 6Z',
  hex: 'M50 8L86 29V71L50 92L14 71V29Z',
  arch: 'M12 92V50A38 38 0 0 1 88 50V92Z',
  square: 'M36 14H64A22 22 0 0 1 86 36V64A22 22 0 0 1 64 86H36A22 22 0 0 1 14 64V36A22 22 0 0 1 36 14Z',
};
const A = { // top of head, eye line, chest line, highlight position
  circle: { top: 8, eye: 50, chest: 80, hl: [36, 30] }, tri: { top: 14, eye: 58, chest: 84, hl: [47, 38] },
  drop: { top: 8, eye: 62, chest: 88, hl: [38, 48] }, hex: { top: 8, eye: 50, chest: 80, hl: [38, 28] },
  arch: { top: 12, eye: 52, chest: 84, hl: [36, 28] }, square: { top: 14, eye: 50, chest: 78, hl: [30, 28] },
};

const clean = (v, list, fallback) => (list.includes(v) ? v : fallback);
const hex = (v, fallback) => (/^#[0-9a-fA-F]{6}$/.test(v || '') ? v : fallback);

function darken(h, k) {
  const n = parseInt(h.slice(1), 16);
  const c = [n >> 16, (n >> 8) & 255, n & 255].map((x) => Math.round(x * (1 - k)));
  return `rgb(${c.join(',')})`;
}
function lum(h) {
  const n = parseInt(h.slice(1), 16);
  return (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
}

export function normalizeLook(look) {
  const l = look || {};
  return {
    shape: clean(l.shape, OPTIONS.shape, DEFAULT_LOOK.shape),
    color: hex(l.color, DEFAULT_LOOK.color),
    accent: hex(l.accent, DEFAULT_LOOK.accent),
    eyes: clean(l.eyes, OPTIONS.eyes, DEFAULT_LOOK.eyes),
    mouth: clean(l.mouth, OPTIONS.mouth, DEFAULT_LOOK.mouth),
    hat: clean(l.hat, OPTIONS.hat, DEFAULT_LOOK.hat),
    glasses: clean(l.glasses, OPTIONS.glasses, DEFAULT_LOOK.glasses),
    accessory: clean(l.accessory, OPTIONS.accessory, DEFAULT_LOOK.accessory),
  };
}

function hatSvg(h, t, c) {
  const cx = 50;
  switch (h) {
    case 'cap': return `<path d="M31 ${t + 15}Q31 ${t - 4} 50 ${t - 4}Q69 ${t - 4} 69 ${t + 15}Z" fill="${c}"/><path d="M52 ${t + 12}H82Q88 ${t + 12} 88 ${t + 17}H52Z" fill="${darken(c, .18)}"/>`;
    case 'beanie': return `<path d="M30 ${t + 16}Q30 ${t - 8} 50 ${t - 8}Q70 ${t - 8} 70 ${t + 16}Z" fill="${c}"/><rect x="28" y="${t + 12}" width="44" height="9" rx="4" fill="${darken(c, .22)}"/><circle cx="50" cy="${t - 10}" r="6" fill="${darken(c, .1)}"/>`;
    case 'tophat': return `<ellipse cx="50" cy="${t + 10}" rx="27" ry="6" fill="${c}"/><rect x="34" y="${t - 22}" width="32" height="32" rx="4" fill="${c}"/><rect x="34" y="${t + 1}" width="32" height="6" fill="#ff4d7d"/>`;
    case 'crown': return `<path d="M32 ${t + 12}L30 ${t - 10}L41 ${t - 1}L50 ${t - 14}L59 ${t - 1}L70 ${t - 10}L68 ${t + 12}Z" fill="#ffc21a" stroke="#e0a000" stroke-width="1.5" stroke-linejoin="round"/><circle cx="50" cy="${t + 3}" r="3" fill="#ff4d7d"/>`;
    case 'party': return `<path d="M50 ${t - 30}L69 ${t + 12}H31Z" fill="${c}"/><path d="M40 ${t - 8}L60 ${t - 8}M36 ${t + 2}L64 ${t + 2}" stroke="#fff" stroke-width="3" opacity=".7"/><circle cx="50" cy="${t - 31}" r="5" fill="#ffc21a"/>`;
    case 'cowboy': return `<path d="M14 ${t + 12}Q24 ${t + 18} 34 ${t + 8}L66 ${t + 8}Q76 ${t + 18} 86 ${t + 12}Q78 ${t + 20} 50 ${t + 20}Q22 ${t + 20} 14 ${t + 12}Z" fill="${c}"/><path d="M33 ${t + 10}Q30 ${t - 14} 42 ${t - 10}Q50 ${t - 4} 58 ${t - 10}Q70 ${t - 14} 67 ${t + 10}Z" fill="${c}"/><rect x="33" y="${t + 3}" width="34" height="5" fill="${darken(c, .3)}"/>`;
    case 'wizard': return `<path d="M50 ${t - 40}Q56 ${t - 22} 70 ${t + 12}H30Q44 ${t - 10} 50 ${t - 40}Z" fill="${c}"/><ellipse cx="50" cy="${t + 12}" rx="26" ry="5" fill="${darken(c, .2)}"/><path d="M44 ${t - 6}l2 4 4 .5-3 3 1 4-4-2-4 2 1-4-3-3 4-.5Z" fill="#ffc21a" transform="scale(.8) translate(11 ${t * .25})"/>`;
    case 'chef': return `<circle cx="38" cy="${t - 4}" r="11" fill="#fff"/><circle cx="62" cy="${t - 4}" r="11" fill="#fff"/><circle cx="50" cy="${t - 9}" r="13" fill="#fff"/><rect x="34" y="${t + 3}" width="32" height="11" rx="3" fill="#fff" stroke="#dcdcdc"/>`;
    case 'graduation': return `<path d="M50 ${t - 10}L84 ${t + 2}L50 ${t + 14}L16 ${t + 2}Z" fill="${c}"/><path d="M34 ${t + 8}V${t + 20}Q50 ${t + 26} 66 ${t + 20}V${t + 8}L50 ${t + 14}Z" fill="${darken(c, .25)}"/><path d="M80 ${t + 3}V${t + 20}" stroke="#ffc21a" stroke-width="2"/><circle cx="80" cy="${t + 22}" r="3" fill="#ffc21a"/>`;
    case 'hardhat': return `<path d="M28 ${t + 16}Q28 ${t - 8} 50 ${t - 8}Q72 ${t - 8} 72 ${t + 16}Z" fill="#ffc21a"/><rect x="22" y="${t + 13}" width="56" height="6" rx="3" fill="#e0a000"/><rect x="45" y="${t - 8}" width="10" height="20" fill="#e0a000"/>`;
    case 'antenna': return `<path d="M50 ${t + 2}V${t - 16}" stroke="${c}" stroke-width="3"/><circle cx="50" cy="${t - 19}" r="6" fill="#ff4d7d"/>`;
    case 'flower': return `<g transform="translate(58 ${t + 2})"><circle r="4" cx="0" cy="-8" fill="#ff4d7d"/><circle r="4" cx="8" cy="0" fill="#ff4d7d"/><circle r="4" cx="0" cy="8" fill="#ff4d7d"/><circle r="4" cx="-8" cy="0" fill="#ff4d7d"/><circle r="4" fill="#ffc21a"/></g>`;
    default: return '';
  }
}

function eyesSvg(kind, y, ink) {
  const xs = [37, 63];
  const pill = (x, h = 16, w = 7) => `<rect x="${x - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" rx="${w / 2}" fill="${ink}"/>`;
  const arc = (x, d) => `<path d="M${x - 6} ${y + 3}Q${x} ${y - 7} ${x + 6} ${y + 3}" fill="none" stroke="${ink}" stroke-width="3.4" stroke-linecap="round" ${d || ''}/>`;
  return xs.map((x, i) => {
    switch (kind) {
      case 'round': return `<circle cx="${x}" cy="${y}" r="6" fill="${ink}"/><circle cx="${x + 1.6}" cy="${y - 2}" r="1.8" fill="#fff"/>`;
      case 'happy': return arc(x);
      case 'sleepy': return `<path d="M${x - 6} ${y}Q${x} ${y + 6} ${x + 6} ${y}" fill="none" stroke="${ink}" stroke-width="3.4" stroke-linecap="round"/>`;
      case 'wide': return pill(x, 22, 9);
      case 'wink': return i === 0 ? arc(x) : pill(x);
      case 'heart': return `<path d="M${x} ${y + 7}C${x - 11} ${y} ${x - 6} ${y - 9} ${x} ${y - 3}C${x + 6} ${y - 9} ${x + 11} ${y} ${x} ${y + 7}Z" fill="#ff2d55"/>`;
      default: return pill(x);
    }
  }).join('');
}

function mouthSvg(kind, y, ink) {
  const m = y + 20;
  switch (kind) {
    case 'smile': return `<path d="M43 ${m - 2}Q50 ${m + 7} 57 ${m - 2}" fill="none" stroke="${ink}" stroke-width="3" stroke-linecap="round"/>`;
    case 'open': return `<path d="M43 ${m - 3}Q50 ${m + 12} 57 ${m - 3}Z" fill="${ink}"/><path d="M46 ${m + 4}Q50 ${m + 8} 54 ${m + 4}" fill="#ff6b81"/>`;
    case 'smirk': return `<path d="M44 ${m}Q52 ${m + 4} 58 ${m - 4}" fill="none" stroke="${ink}" stroke-width="3" stroke-linecap="round"/>`;
    case 'tongue': return `<path d="M43 ${m - 3}Q50 ${m + 5} 57 ${m - 3}" fill="none" stroke="${ink}" stroke-width="3" stroke-linecap="round"/><path d="M48 ${m + 1}v6a3 3 0 0 0 6 0v-6Z" fill="#ff6b81"/>`;
    default: return '';
  }
}

function glassesSvg(kind, y, c) {
  switch (kind) {
    case 'round': return `<g fill="rgba(255,255,255,.18)" stroke="${c}" stroke-width="2.6"><circle cx="37" cy="${y}" r="11"/><circle cx="63" cy="${y}" r="11"/><path d="M48 ${y}H52" fill="none"/></g>`;
    case 'square': return `<g fill="rgba(255,255,255,.18)" stroke="${c}" stroke-width="2.6"><rect x="25" y="${y - 9}" width="24" height="18" rx="4"/><rect x="51" y="${y - 9}" width="24" height="18" rx="4"/><path d="M49 ${y}H51" fill="none"/></g>`;
    case 'shades': return `<g fill="${c}"><path d="M24 ${y - 8}H49Q48 ${y + 12} 37 ${y + 12}Q26 ${y + 12} 24 ${y - 8}Z"/><path d="M51 ${y - 8}H76Q74 ${y + 12} 63 ${y + 12}Q52 ${y + 12} 51 ${y - 8}Z"/><rect x="47" y="${y - 7}" width="6" height="3"/></g><path d="M28 ${y - 4}l6 -0" stroke="#fff" stroke-width="2" opacity=".5" stroke-linecap="round"/>`;
    case 'monocle': return `<circle cx="63" cy="${y}" r="12" fill="rgba(255,255,255,.2)" stroke="${c}" stroke-width="2.6"/><path d="M73 ${y + 9}Q84 ${y + 20} 80 ${y + 36}" fill="none" stroke="${c}" stroke-width="1.6"/>`;
    case 'visor': return `<rect x="22" y="${y - 10}" width="56" height="20" rx="10" fill="${c}" opacity=".88"/><rect x="28" y="${y - 6}" width="20" height="3" rx="1.5" fill="#fff" opacity=".45"/>`;
    default: return '';
  }
}

function accessorySvg(kind, chest, c, eyeY) {
  const y = chest;
  switch (kind) {
    case 'bowtie': return `<path d="M50 ${y}L34 ${y - 8}V${y + 8}Z M50 ${y}L66 ${y - 8}V${y + 8}Z" fill="${c}"/><circle cx="50" cy="${y}" r="4" fill="${darken(c.startsWith('#') ? c : '#000000', .25)}"/>`;
    case 'tie': return `<path d="M46 ${y - 4}H54L57 ${y + 4}L50 ${y + 22}L43 ${y + 4}Z" fill="${c}"/><path d="M46 ${y - 4}H54L52 ${y - 8}H48Z" fill="${darken(c, .25)}"/>`;
    case 'scarf': return `<path d="M22 ${y - 6}Q50 ${y + 8} 78 ${y - 6}V${y + 4}Q50 ${y + 18} 22 ${y + 4}Z" fill="${c}"/><path d="M62 ${y + 6}V${y + 24}H73V${y + 4}Z" fill="${darken(c, .2)}"/>`;
    case 'stethoscope': return `<path d="M32 ${y - 10}Q30 ${y + 14} 50 ${y + 14}Q70 ${y + 14} 68 ${y - 10}" fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round"/><circle cx="50" cy="${y + 16}" r="5" fill="#c9d1d9" stroke="${c}" stroke-width="2"/>`;
    case 'headphones': return `<path d="M18 ${eyeY}V${eyeY - 20}Q18 ${eyeY - 44} 50 ${eyeY - 44}Q82 ${eyeY - 44} 82 ${eyeY - 20}V${eyeY}" fill="none" stroke="${c}" stroke-width="5" stroke-linecap="round"/><rect x="10" y="${eyeY - 12}" width="12" height="26" rx="6" fill="${c}"/><rect x="78" y="${eyeY - 12}" width="12" height="26" rx="6" fill="${c}"/>`;
    case 'mustache': return `<path d="M50 ${eyeY + 15}Q44 ${eyeY + 8} 34 ${eyeY + 14}Q38 ${eyeY + 22} 50 ${eyeY + 17}Q62 ${eyeY + 22} 66 ${eyeY + 14}Q56 ${eyeY + 8} 50 ${eyeY + 15}Z" fill="${c}"/>`;
    case 'blush': return `<ellipse cx="27" cy="${eyeY + 12}" rx="6" ry="3.4" fill="#ff5f8a" opacity=".55"/><ellipse cx="73" cy="${eyeY + 12}" rx="6" ry="3.4" fill="#ff5f8a" opacity=".55"/>`;
    case 'badge': return `<circle cx="66" cy="${y}" r="7" fill="#ffc21a" stroke="#e0a000" stroke-width="1.5"/><path d="M66 ${y - 3.5}l1.4 2.9 3.2.4-2.3 2.2.6 3.1-2.9-1.5-2.9 1.5.6-3.1-2.3-2.2 3.2-.4Z" fill="#fff"/>`;
    default: return '';
  }
}

const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function dotSvg(look, size = 96, label = 'Dot') {
  const l = normalizeLook(look);
  const a = A[l.shape];
  const ink = lum(l.color) > 0.62 ? '#14171c' : '#ffffff';
  const inkEyes = lum(l.color) > 0.5 ? '#14171c' : '#ffffff';
  const cape = l.accessory === 'cape'
    ? `<path d="M22 ${a.chest - 14}L6 ${a.chest + 26}Q20 ${a.chest + 20} 34 ${a.chest + 24}Z M78 ${a.chest - 14}L94 ${a.chest + 26}Q80 ${a.chest + 20} 66 ${a.chest + 24}Z" fill="#ff4d7d"/>` : '';
  const chestItems = l.accessory === 'cape'
    ? `<path d="M30 ${a.chest - 6}Q50 ${a.chest + 6} 70 ${a.chest - 6}" fill="none" stroke="#ff4d7d" stroke-width="5" stroke-linecap="round"/><circle cx="50" cy="${a.chest}" r="4" fill="#ffc21a"/>`
    : accessorySvg(l.accessory, a.chest, l.accent, a.eye);
  const headphonesFirst = l.accessory === 'headphones';
  const body = `<path d="${SHAPES[l.shape]}" fill="${l.color}"/><path d="${SHAPES[l.shape]}" fill="url(#none)"/>`
    + `<ellipse cx="${a.hl[0]}" cy="${a.hl[1]}" rx="13" ry="7" transform="rotate(-28 ${a.hl[0]} ${a.hl[1]})" fill="#fff" opacity=".28"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -34 120 140" width="${size}" height="${size}" role="img" aria-label="${esc(label)}">`
    + cape + (headphonesFirst ? chestItems : '') + body
    + eyesSvg(l.eyes, a.eye, inkEyes) + mouthSvg(l.mouth, a.eye, inkEyes)
    + glassesSvg(l.glasses, a.eye, l.glasses === 'shades' || l.glasses === 'visor' ? '#14171c' : l.accent)
    + (headphonesFirst ? '' : chestItems)
    + hatSvg(l.hat, a.top, l.accent)
    + '</svg>';
}

export function randomLook() {
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  return normalizeLook({
    shape: pick(OPTIONS.shape), color: pick(PALETTE.slice(0, 10)), accent: pick(['#0a0a0a', '#ffffff', '#ff4d7d', '#2f7bff', '#ffc21a', '#19c3a6']),
    eyes: pick(OPTIONS.eyes), mouth: pick(OPTIONS.mouth), hat: pick(OPTIONS.hat), glasses: pick(OPTIONS.glasses), accessory: pick(OPTIONS.accessory),
  });
}
