/* One entry point to draw a Dot: plush art when the look has a body, the flat SVG otherwise. */
import { dotSvg } from './dotSvg';
import { dotSprite, isSpriteLook, ensureSpriteStyles } from './dotSprite';

export function renderDot(look, size, label) {
  if (isSpriteLook(look)) {
    ensureSpriteStyles();
    return dotSprite(look, size, label, '/dots/');
  }
  return dotSvg(look, size, label);
}
