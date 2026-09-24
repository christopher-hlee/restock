/* Kinari glyphs and icons. Paste over GLYPH / WORD / INK in monitor/static/index.html.
   State glyphs: 12px, viewBox 0 0 12 12, currentColor, aria-hidden. They differ by
   shape alone, so a state never depends on colour. Keep the existing SUN / MOON
   constants for the theme button. */

const svg = (body, size = 12, box = '0 0 12 12', cls = 'glyph') =>
  `<svg class="${cls}" viewBox="${box}" width="${size}" height="${size}" aria-hidden="true">${body}</svg>`;
const RING = '<circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" stroke-width="1.4"/>';

const GLYPH = {
  in_stock:     svg('<circle cx="6" cy="6" r="4.5" fill="currentColor"/>'),                 // filled disc
  held:         svg(RING + '<path d="M6 1.5a4.5 4.5 0 0 0 0 9z" fill="currentColor"/>'),    // half-filled
  out_of_stock: svg(RING),                                                                  // hollow ring
  not_yet:      svg(RING + '<path d="M6 6V3.6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>'), // ring + clock hand
  watching:     svg(RING + '<circle cx="6" cy="6" r="1.6" fill="currentColor"/>'),          // ring + dot
  unknown:      svg('<circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="2.1 1.43"/>'), // dashed ring = no baseline
  failing:      svg('<path d="M6 1.3 10.9 10.4H1.1z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6 4.8v2.7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>'), // the only angular shape
  paused:       svg('<path d="M2.5 2h2.5v8H2.5zM7 2h2.5v8H7z" fill="currentColor"/>'),
  armed:        svg('<path d="M6 1 11 6 6 11 1 6z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><circle class="tick" cx="6" cy="6" r="1.6" fill="currentColor"/>', 12, '0 0 12 12', 'glyph armed'),
  backoff:      svg('<path d="M1.5 2h2v8h-2zM5 4h2v6H5zM8.5 6h2v4h-2z" fill="currentColor"/>'), // three descending bars
};

/* The 10-second redraw replaces rows. A negative delay keeps every Armed blink on
   one continuous clock instead of restarting it on each redraw. Use this, not
   GLYPH.armed, wherever Armed is rendered. */
const armedGlyph = () => GLYPH.armed.replace('class="tick"',
  `class="tick" style="animation-delay:-${Date.now() % 2400}ms"`);

const WORD = {in_stock: 'In stock', held: 'Held', out_of_stock: 'Sold out', not_yet: 'Not yet on sale',
  failing: 'Failing', unknown: 'No baseline', watching: 'Watching', paused: 'Paused',
  armed: 'Armed', backoff: 'Backing off'};

const INK = {in_stock: 'var(--in-stock)', held: 'var(--held)', out_of_stock: 'var(--muted)',
  not_yet: 'var(--muted)', failing: 'var(--failing)', unknown: 'var(--no-baseline)',
  watching: 'var(--text)', paused: 'var(--muted)', armed: 'var(--armed)', backoff: 'var(--armed)'};

const ICON = {
  star:    svg('<path d="M6 .9 7.5 4.1l3.5.4-2.6 2.4.7 3.5L6 8.7l-3.1 1.7.7-3.5L1 4.5l3.5-.4z" fill="currentColor"/>', 12, '0 0 12 12', 'icon'),
  x:       svg('<path d="M2 2l8 8M10 2l-8 8" stroke="currentColor" stroke-width="1.5"/>', 12, '0 0 12 12', 'icon'),
  disc:    svg('<circle cx="4" cy="4" r="3.5" fill="currentColor"/>', 8, '0 0 8 8', 'icon'),        // "your size" marker
  arrow:   '<svg class="icon" viewBox="0 0 14 10" width="14" height="10" aria-hidden="true"><path d="M1 5h11M8 1.2 11.8 5 8 8.8" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
  radio:   svg(RING, 12, '0 0 12 12', 'icon'),
  radioOn: svg(RING + '<circle cx="6" cy="6" r="2.2" fill="currentColor"/>', 12, '0 0 12 12', 'icon'),
  nophoto: svg('<path d="M6.4 4.6a1.6 1.6 0 1 1 2.1 1.5c-.3.1-.5.4-.5.7v.8l6.3 4.2H1.7L8 7.6" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" stroke-linecap="round"/>', 16, '0 0 16 16', 'icon'), // hanger
};

/* CSS that goes with these:
.glyph,.icon{display:block;flex:none}
@keyframes tick{50%{opacity:0}}
.glyph.armed .tick{animation:tick 2.4s steps(1) infinite}
@media (prefers-reduced-motion:reduce){
  .glyph.armed .tick{animation:none}
  .glyph.armed path{fill:currentColor}
}
*/
