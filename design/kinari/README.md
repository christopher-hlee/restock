# Handoff: Restock → Kinari

**To use it:** copy this folder into the repo as `design/kinari/`, then give Claude Code this prompt:

> Implement the Kinari design across the Restock dashboard (`monitor/static/index.html`), following `design/kinari/README.md`. Read the whole README before you start, especially "Where ui-check.py and the design collide". Keep every class and id it lists. Run `python3 ui-check.py` and the test suite, and don't push to main until both pass.

## Overview

Restock's dashboard is one file, `monitor/static/index.html`: the markup, one `<style>` block, and vanilla-JS string templates. It gets a new visual system called **Kinari**, which is ink on unbleached paper:

- warm washi (light) and sumi (dark) grounds
- Newsreader for names and headings, Hanken Grotesk for everything else
- square corners and no shadows
- a single shu-vermilion fill that only ever means **buy**

The scope is the whole app:

- the main page, on phone and desktop
- every sheet: drop, Add a watch, Edit, Details, and Why didn't this alert?
- sign-in, toasts, warnings and empty states

Both modes ship. There are no API, data or state-machine changes, and no control is removed.

## About the design files

`reference/` holds **design references built in HTML**. They are prototypes of the intended look, not production code.

- Recreate the design inside `index.html` using its existing patterns: render functions that return template strings, CSS custom properties, and one stylesheet.
- Don't port the reference's markup, its inline styles or its component runtime.

Two files are meant to be pasted in directly:

- `kinari-tokens.css`: the token blocks
- `glyphs.js`: the icon set

Where the reference and this README disagree, **the README wins**. The reference was drawn with sample data, and it leaves out some existing controls that must stay:

- Edit on rows
- delete on waiting rows
- Pause/Resume
- Watch sale

## Fidelity

High fidelity. Colours, type, spacing, radii, states and motion are final. Surfaces the reference doesn't draw are specified below in the same system: Edit, Details, Why didn't this alert?, Sign in, suggestions, warnings and empty states.

## Ground rules

1. **Keep every hook.** The classes and ids below are used by `ui-check.py` or the JS. Keep them, along with `data-e`, `data-h`, `data-key`, `data-tier` and `aria-pressed` wherever they appear today.
   - Classes: `.hdr .hdr-actions .counts .stat .group-label .row .name .meta .caption .kicker .state-eyebrow .bucket .deck .tn .bk-main .bk-name .bk-meta .items .item .item-main .item-title .item-meta .item-acts .overlay .sheet .bucket-sheet .sheet-head .sheet-actions .wait .fired .feed .sugg .x .btn-text .btn-ghost .theme .chip .chips .seg .intent .field .detect .warn .empty .dock .toast .hide .locked`
   - Ids: `#login #pw #loginErr #app #eyebrow #headline #counts #warnings #sheet #add #intents #aUrl #detect #kwField #aKw #sizeField #aSize #seg #saveBtn #addErr #aVendors #iUrl #iOut #eName #eUrl #eKw #eSize #eSeg #eWarn #eSave #eErr #build #themeColor`
2. **New classes are additive.** The only new ones are `.btn-buy`, `.btn-quiet`, `.strong`, `.glyph`, `.icon`, `.stat.buy` and the few wrappers named below.
3. **Nothing is removed.** Every existing control stays, restyled.
4. **Copy stays the repo's.** Every change is listed in [Copy changes](#copy-changes).
5. **One fill means buy.** `--accent` is only ever the background of size chips, Add to cart, Cart and the Buyable figure. These are never filled or accent-coloured:
   - links, tags and stars
   - the selected segment and the selected intent
   - Start watching, Sign in and the dock's Add a watch
6. **A state is a glyph and a word,** never colour alone.
7. **Square.** Radius 0 and no box-shadow depth, everywhere. The one rounded thing is the 4px sheet grab handle (2px radius).
8. **Nothing depends on hover.** `:hover` only mirrors `:active`, and only inside `@media (hover:hover)`. There are no transitions on buttons or rows.
9. **Sentence case.** Remove every `text-transform:uppercase` and wide `letter-spacing`: on labels, buttons, kickers, tags, stats, fields, the dock and `#build`. The header date line is the only uppercase text left.

## Where ui-check.py and the design collide

Read this before writing CSS. Each item was checked against `ui-check.py` on `main`.

1. **Contrast check vs the inverted Buyable figure: patch the check.**
   - The light-mode check compares each selector's text colour against `body`'s background.
   - The first `.stat span` on the page is now the Buyable label: white on vermilion. Its real contrast is 5.9:1, but against the washi page it scores about 1.1:1 and fails.
   - Fix the check so it measures against the nearest opaque ancestor. In `ui-check.py`, inside the `weak = page.evaluate("""…""")` block, replace this line:
     ```
     const bg = lum(getComputedStyle(document.body).backgroundColor);
     ```
     with:
     ```
     const bgOf = e => {
         for (let n = e; n; n = n.parentElement) {
             const c = getComputedStyle(n).backgroundColor;
             if (!/rgba\\(.*,\\s*0\\)$/.test(c)) return c;
         }
         return getComputedStyle(document.body).backgroundColor;
     };
     ```
   - Then, in the loop, change `const f = lum(getComputedStyle(e).color);` to:
     ```
     const f = lum(getComputedStyle(e).color), bg = lum(bgOf(e));
     ```
   - The backslashes are doubled because this JS sits inside a Python string, like the existing `\\d`.
   - If you'd rather not touch the check, there's a fallback: drop the inversion and colour only the Buyable numeral `--accent`. It's weaker, but it passes as is.
2. **The drop sheet scrolls itself.**
   - The check asserts that `.bucket-sheet` itself scrolls, and that `.sheet-head` stays pinned while it does.
   - Keep today's structure: `.bucket-sheet` is the scroll container, with a sticky `.sheet-head` at the top and a sticky `.sheet-actions` at the bottom.
   - The reference uses an inner scrolling list. Don't copy that.
3. **Motion timing.**
   - The check measures the sheet 250ms after the tap, and expects it gone 150ms after close. `getBoundingClientRect` includes transforms.
   - So the enter animation must be ≤200ms and start synchronously: force a reflow, don't wait for `requestAnimationFrame`.
   - Close must be instant.
4. **The theme model doesn't change.**
   - No attribute means dark; `data-theme="light"` means light. The choice is stored in `localStorage['restock-theme']`, and dark stays the default.
   - Don't follow `prefers-color-scheme`. The check runs in a light-preference browser and expects the toggle to go dark → light → dark, with the attribute removed at the end.
5. **`.dock .btn-accent` is how the check opens Add a watch on phones.** Keep `btn-accent` on that one button as a style-less hook (see Buttons).
6. **Sign in is found by `text=SIGN IN`** (case-insensitive), so the label stays "Sign in".
7. **Tap targets and row heights are already met by this spec.**
   - `.x` is 44×44 at every width: drop the inline `width:26px;height:26px` and the phone `!important` override.
   - `.btn-text` is 44px tall. Dock and sheet buttons are ≥44px.
   - Row limits: `.wait` 200, `.bucket` 170, `.feed` 160, `.sugg` 200, `.row` 420, and 260 for a sheet `.item`.
8. **Stat labels must never ellipsize.**
   - At 375px, five cells leave about 52px for a 13px label, and "Dropped" is about 51px.
   - So phone cells use 6px side padding. The reference draws 8px.

## Design tokens

`kinari-tokens.css` contains everything in this section.

### Colour

| Token | Light · washi | Dark · sumi | Used for |
|---|---|---|---|
| `--ground` | `#F4EFE6` | `#171513` | page, sheets, dock, sticky sheet head/foot |
| `--surface` | `#EAE3D6` | `#211E1B` | inputs, pressed quiet buttons, selected segment, toast |
| `--surface-quiet` | `#EFE9DE` | `#1C1A17` | pressed rows, selected intent, `.warn` box |
| `--rule` | `#D8CFBF` | `#3A342D` | section rules, dock top, sheet edges |
| `--border` | `#8C8173` | `#7A7063` | quiet-button and input borders (≥3:1), grab handle |
| `--rule-faint` | `#E4DCCD` | `#2A2622` | row separators |
| `--bright` | `#1C1A17` · 16.2:1 | `#F2EBDF` · 15.6:1 | headline, names, quiet-button labels |
| `--text` | `#2E2A25` · 13.0:1 | `#DDD5C8` · 12.4:1 | body, text buttons |
| `--text-dim` (= `--held`) | `#5E564C` · 6.6:1 | `#ADA497` · 7.6:1 | meta, kickers, stat labels, Held |
| `--muted` (= `--dim` = `--faint`) | `#6F665A` · 5.2:1 | `#948B7E` · 5.6:1 | times, least-important words, Sold out, Paused |
| `--accent` (shu) | `#B8321E` | `#E2553B` | **buy fill only** |
| `--accent-ink` | `#FFFFFF` · 5.9:1 on accent | `#170A06` · 6.0:1 | label on the buy fill |
| `--in-stock` | `#3E6B2E` · 5.9:1 | `#8FC27A` · 9.1:1 | In stock, back in stock |
| `--failing` | `#9B2D5A` · 6.9:1 | `#E88AAE` · 8.0:1 | plum, deliberately not red |
| `--armed` | `#8A5A00` · 5.6:1 | `#D9A441` · 8.5:1 | Armed, Backing off, slow lag, `.warn` edge |
| `--no-baseline` | `#1F5E86` · 6.4:1 | `#7FB0D6` · 8.0:1 | No baseline, coming soon |
| `--photo-bg` | `#E6DED0` | `#26221E` | photo well |
| `--focus` | `#1F5E86` | `#7FB0D6` | focus ring |
| `--scrim` | `rgb(28 26 23 / .45)` | `rgb(0 0 0 / .6)` | behind sheets |
| `--tint-in-stock` | `#E9EDDF` | `#1C2219` | In stock block |
| `--tint-failing` | `#F3E3E8` | `#251A1F` | Failing block |
| `--photo-blend` | `multiply` | `normal` | on product `<img>` |
| `--photo-edge` | `transparent` | `#2A2622` | 1px inset edge on photo wells |

- **Contrast.** Ratios are against `--ground`. On `--surface`, take off about 10%; every text token still clears 4.5:1.
- **Colour blindness.**
  - Vermilion (buy) and plum (failing) converge under protanopia; the glyph and word tell them apart.
  - In-stock green and armed ochre converge under deuteranopia; disc vs diamond tells them apart.
  - Check vermilion vs plum on a real phone in daylight.
- **Legacy names.** Every old token still resolves, aliased in the tokens file, so inline `var(--dim)` and similar in the templates keep working. Delete each alias once nothing uses it.
- **Browser chrome.**
  - `theme-color` is `#171513` in dark and `#F4EFE6` in light. Update all three places that set it: the `<meta>` default, the head script, and `paintThemeButtons()`.
  - Add `<meta name="color-scheme" content="light dark">`. It stops Android WebView (Telegram's in-app browser) from applying algorithmic darkening.

### Type

Replace the Fraunces + Work Sans link with:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Hanken+Grotesk:wght@400;500;600&display=swap" rel="stylesheet">
```

The stacks are in the tokens file as `--serif`, `--sans` and `--mono`:

- **Newsreader (`--serif`):** 400 and 500 only; never set a serif at 600. Use `font-optical-sizing:auto`.
- **Hanken Grotesk (`--sans`):** 400, 500 and 600. This covers every button, chip, price, figure, label and body text.
- **Mono (`--mono`):** the system mono stack, with no download. Only for URLs, errors and the build line.

| Role | Face | Size / weight / line-height | Colour |
|---|---|---|---|
| Date line `#eyebrow` | sans | 12 / 500 / 1.3, uppercase, 0.06em tracking | `--text-dim` |
| Headline `#headline` | serif | 28 phone · 40 desktop / 400 / 1.1, −0.01em, `text-wrap:balance` | `--bright` |
| Sheet title `.sheet h2` | serif | 26 / 400 / 1.1, −0.01em | `--bright` |
| Section title `.group-label h2` | serif | 19 / 500 / 1.2 | `--bright` |
| Names (product, collection, store) | serif | 17 / 500 / 1.25 | `--bright` (Held name: `--text`) |
| Waiting-row name | sans | 15 / 400 / 20px | `--text` |
| Body | sans | 15 / 400 / 1.45 | `--text` |
| Meta, kickers | sans | 13 / 400 / 1.35–1.4 | `--text-dim` |
| State words | sans | 13 / 500 / 1.35 | state colour |
| Tags, "no photo" | sans | 12 / 600 (tags) | — |
| Stat figures | sans | 24 / 500 / 1 | `--bright` |
| Prices | sans | 15 / 500 | `--bright` |
| Buttons | sans | 15 (text buttons 14) | see Buttons |
| Build line, URLs, errors | mono | 12 (build) · 13 · 16 in inputs | — |

- Every price, count and time uses `font-variant-numeric: tabular-nums lining-nums`.
- `body` keeps `text-wrap:pretty` and `-webkit-font-smoothing:antialiased`.
- `body` itself is set in the sans at 15px, line-height 1.45.

### Space, layout, shape

- **Spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64. Exact component values are given below; a few are 3/5/6/10/14 for optical fit.
- **Gutter `--gutter`:** 16px below 600px, 32px from 600px, 48px from 1200px. On phones keep the existing `max(var(--gutter), env(safe-area-inset-left/right))`.
- **Content:** max-width 1120px, centred.
- **Bleed `--bleed`:** 16px. The In stock and Failing blocks extend 16px past the content edge on each side, so on a phone they run edge to edge.
- **Breakpoint:**
  - At ≤820px it's the phone layout: dock, stacked header, bottom sheets. This is the same boundary as today and as ui-check.
  - Above 820px it's the desktop layout.
- **Shape:** radius 0 and no elevation. The only rings allowed are:
  - fan photos: `box-shadow:0 0 0 2px var(--ground)`
  - photo wells: `outline:1px solid var(--photo-edge); outline-offset:-1px`
  - focus
- **Focus:** `:focus-visible{outline:2px solid var(--focus); outline-offset:2px}`. Full-width rows (`.bucket`, `.intent`) use `outline-offset:-2px`.
- **Links:** `a{color:var(--bright); text-decoration-thickness:1px; text-underline-offset:3px}`, with hover (inside `hover:hover`) going to `--text`. Links wrapping titles inside rows use `color:inherit; text-decoration:none`. No accent links anywhere.

### Motion

| What | Spec |
|---|---|
| Sheet enter, phone | `transform: translateY(100%) → none`, 200ms `cubic-bezier(.2,.8,.2,1)` |
| Modal enter, desktop | `opacity 0 → 1` plus `translateY(8px) → none`, 200ms, same curve |
| Scrim | `background-color: transparent → var(--scrim)`, 200ms linear |
| Close (sheet, modal, scrim) | instant |
| Toast | in: opacity 0 → 1 while rising 8px, 160ms ease-out; holds 4s; out: opacity → 0 over 160ms, then removed |
| Armed glyph | centre dot blinks: `@keyframes tick{50%{opacity:0}}`, `2.4s steps(1) infinite`, phase kept continuous with `armedGlyph()` |
| Buttons, rows | none (instant pressed states) |
| `prefers-reduced-motion: reduce` | sheet, scrim and toast take 1ms; Armed is a static filled diamond |

Motion applies to `#add` only. `#login` is a page, not a sheet, so it never animates.

The original design PDF said 240ms for the sheet; this spec uses 200ms because of the ui-check timing in item 3 above.

## Components

### Buttons

There are three styles, which replace the old five (`btn-accent`, `btn-ghost`, `btn-text`, `chip`, `chip.primary`).

**Buy: `.btn-buy`.** Add it to size chips, Add to cart, and Cart in the drop sheet.

- **Colour and shape:** `background:var(--accent); color:var(--accent-ink)`, no border, radius 0.
- **Type:** Hanken 15px, 600, line-height 1, tabular.
- **Layout:** inline-flex, centred, `gap:8px`.
- **Sizes:**
  - size chips: min 56×48px, `padding:0 16px`
  - Cart (sheet): min 64×44px, `padding:0 16px`
  - Add to cart: min-height 48px, `padding:0 20px`, width auto
- **States:**
  - `:active`: `filter:brightness(.88); transform:translateY(1px)`
  - hover (inside `hover:hover`): `filter:brightness(.88)`
  - disabled: `opacity:.45`
- **Sold-out sizes** stay absent, as today; they're never shown disabled.
- **Your-size chip** content: `ICON.disc` (8px), the size, `ICON.arrow` (14×10), then "cart", with 8px gaps. For example: ● M → cart.
- **`.chips`:** `display:flex; flex-wrap:wrap; gap:8px`. Chips size to their content (`flex:none`); drop `flex:1` and `flex:1.5`.

**Quiet: `.btn-quiet`.** Restyle the existing `.btn-ghost` identically, and use either class.

- **Colour and shape:** transparent, `1px solid var(--border)`, `color:var(--bright)`, radius 0.
- **Type:** Hanken 15px, 500, line-height 1, sentence case, `white-space:nowrap`.
- **Size:** min-height 44px, `padding:0 16px` (14px in the Failing row).
- **States:** `:active` and hover give `background:var(--surface)`. Disabled is `opacity:.45`; Check now uses this while it runs.
- **`.btn-quiet.strong`** is the one primary action of a sheet: Sign in, Start watching, Save changes and Look. It adds `border-color:var(--bright); font-weight:600; min-height:48px`.
- **`.theme`** is 44×44px with `padding:0`. Keep the 18px SUN/MOON icons.
- **Markup swap:**
  - Every `btn-accent` becomes `btn-quiet strong`, with one exception: the dock's Add a watch becomes `btn-ghost btn-accent`. There, `btn-accent` is only the ui-check hook.
  - Delete all `.btn-accent` style rules and leave a comment saying why the class survives.
  - Inspect's `class="btn"` becomes `btn-quiet strong`.

**Text: `.btn-text`.**

- **Colour:** no background or border, `color:var(--text)`.
- **Type:** Hanken 14px, 500, underlined (1px thick, `text-underline-offset:3px`).
- **Size:** min-height 44px, inline-flex, centred, `padding:0 8px; margin-inline:-8px`. The hit box grows without shifting alignment.
- **States:** hover and active go to `--bright`.
- **Destructive:** Delete uses `color:var(--failing)`.
- **Inline colours:** remove every other inline colour on text buttons (`--muted`, `--dim`, `--accent`), so they are all `--text`.
- **Placement:** in a section header, the text button sits right with `margin:-6px -8px -6px auto`.

**Dismiss / close: `.x`.**

- **Size:** a 44×44 box at every width. Use `ICON.x` (12px) instead of `&times;`.
- **Colour:** no border or background, `color:var(--muted)`. The sheet's close button uses `--text`.
- **Edge alignment:** at a right edge, `margin-right:-14px` so the glyph lines up with the text edge.
- **States:** hover and active go to `--bright`. It never turns red; dismissing isn't an error.

### Inputs: `.field`

- **`input`:**
  - Shape: min-height 48px, `padding:0 14px`, `background:var(--surface)`, `1px solid var(--border)`, radius 0.
  - Text: `color:var(--bright)`, 16px at every width.
  - Font: Hanken for text and password fields. Mono for URL fields: `#aUrl`, `#eUrl`, `#iUrl`.
  - Placeholder: `--muted`.
  - `:focus`: `outline:2px solid var(--focus); outline-offset:2px`, with the border unchanged. Remove the accent border.
  - Long URLs scroll inside the input natively. Anywhere a URL is displayed as text, it gets `overflow-wrap:anywhere`, or an ellipsis when it must stay on one line. Never let a URL break mid-letter across a fixed box.
- **`label`:**
  - Layout: flex, `justify-content:space-between; gap:12px`.
  - Type: 13px, 500, line-height 1.3, `--text-dim`, sentence case.
  - The hint span on the right is 13px, 400, `--muted`.
- **Spacing:** 8px between label and input, and 24px between fields (`.field{margin-top:24px}`).
- **`#detect` / `.detect`:**
  - Unboxed: no background or border.
  - First line: 13px, line-height 1.35, `--text-dim`, with the store name at 600 in `--bright`. For example: **RAGTAG** · Shopify collection · checks the catalogue feed.
  - `.l2`: 13px, `--text-dim`.
  - `.detect.bad`: `--failing` text, led by `GLYPH.failing`.

### Segmented control: `.seg`

- **Box:** `1px solid var(--border)`, radius 0.
- **Buttons:** `flex:1`, min-height 48px, transparent, Hanken 15px, 500, tabular, `--text-dim`.
- **Pressed (`[aria-pressed="true"]`):** `background:var(--surface); box-shadow:inset 0 0 0 1px var(--bright); color:var(--bright); font-weight:600`.
- **Not filled.** This replaces today's accent fill.

### Intent cards: `.intent`

- **List:** a stack with `gap:8px`. This replaces the border-top separators.
- **Card:** min-height 56px, `padding:10px 14px`, `1px solid var(--border)`, radius 0, transparent, left-aligned text.
  - Grid `12px 1fr`, gap 12px.
  - On desktop, grid `12px 1fr 240px`, keeping `.ex`.
- **Content:**
  - `.q`: Hanken 15px, 400, `--text`. No longer serif.
  - Glyph: `ICON.radio` in `--muted`.
  - `.ex`: 13px, `--muted`, desktop only as today.
- **Selected (`[aria-pressed="true"]`):**
  - The card gets `background:var(--surface-quiet); border-color:var(--bright)`.
  - `.q` goes `--bright`, 500, and the glyph is `ICON.radioOn` in `--bright`.
  - Remove the accent left border.
  - `openAdd()` and `pickIntent()` set the glyph colour inline to `--accent`/`--muted`. Change that to `--bright`/`--muted`.

### Tags: `.tag`

- **Style:** inline-flex, 12px, 600, line-height 16px, `padding:2px 6px`, `1px solid currentColor`, radius 0, `white-space:nowrap`.
- **Also:** no tracking, and `margin-left:0`.

| `arrivalTag()` returns | Class | Colour |
|---|---|---|
| released, now buyable | `tag now` | `--bright` |
| back in stock | `tag now back` (add `back`) | `--in-stock` |
| relisted | `tag relisted` (add) | `--muted`, dotted border |
| coming soon | `tag soon` | `--no-baseline` |
| unverified → text becomes "unverified?" | `tag unverified` (add) | `--muted` |
| not covered (inspect) | `tag` | `--muted` |

### State glyphs and words

- **Swap in `glyphs.js`.** It replaces `GLYPH`, `WORD` and `INK`, and adds `ICON` and `armedGlyph()`. Include the CSS in its footer.
- **`.state-eyebrow`:**
  - Layout: `display:inline-flex; align-items:center; gap:6px`.
  - Type: 13px, 500, line-height 1.35, in the state colour, sentence case.
  - Remove the inline `letter-spacing:.18em` in `armedBadge()` and `backoffBadge()`.
- **Time:**
  - When an eyebrow carries a time, render it as `<span class="when"> · 12s ago</span>`: 400, `--muted`, tabular.
  - Give `eyebrowFor()` a third argument for the time.
- **Several eyebrows on one line** (In stock + Armed + Backing off) sit in a `flex-wrap:wrap; gap:4px 12px` row.
- **Multi-line state text:** glyphs get `margin-top:4px` so they align with the first 20px line.

| State | Glyph | Word | Colour |
|---|---|---|---|
| in_stock | filled disc | In stock | `--in-stock` |
| held | half-filled circle | Held | `--held` |
| out_of_stock | hollow ring | Sold out | `--muted` |
| out_of_stock + `ever_buyable === false` | ring + clock hand (`not_yet`) | Not yet on sale | `--muted` |
| watching | ring + centre dot | Watching | `--text` |
| unknown | dashed ring | No baseline | `--no-baseline` |
| failing | triangle + bar | Failing | `--failing` |
| paused | two bars | Paused | `--muted` |
| armed | diamond, blinking dot | Armed | `--armed` |
| backing off | three descending bars (`backoff`) | Backing off | `--armed` |

- The Armed badge drops the `.pulse` wrapper and its `armpulse` keyframes; use `armedGlyph()`.
- `backoffBadge()` uses `GLYPH.backoff`, not `GLYPH.paused`.

### Value signals

- **★ worth pricing:** `ICON.star` (12px) in `--bright`, plus the count at 13px, 600, tabular. It's never accent; change `.star`'s colour to `--bright`.
- **Landed cost:** "≈$403 landed" at 13px, `--text-dim`, tabular, `white-space:nowrap`. It sits on the price line after the store price. Price and landed are separate `nowrap` items in a `flex-wrap:wrap` row.
- **Lag:** "3m behind" in `--muted`. `.lag.slow` (past 5 minutes) turns `--armed` and is led by `GLYPH.backoff`, so the change never relies on colour alone.

### Photos: `.tn` and `.shot`

- **The well:**
  - Square (`aspect-ratio:1`), `background:var(--photo-bg)`, `overflow:hidden`, radius 0.
  - `outline:1px solid var(--photo-edge); outline-offset:-1px`. The edge only shows in dark mode.
  - No hatch patterns anywhere.
- **The `<img>`:** `display:block; width:100%; height:100%; object-fit:cover; mix-blend-mode:var(--photo-blend)`. In light mode, white product backgrounds melt into the well.
- **`.shot`:**
  - It becomes an `<img>` in a well, like `.tn`, instead of `background-image`, so that `cover` and the blend behave the same everywhere.
  - Remove the inline coloured borders.
- **Sizes:**

  | Where | Size |
  |---|---|
  | drop fan | 56px |
  | In stock | 96px |
  | Held, Failing | 72px |
  | sheet item | 96px |

  These apply at every width. Request thumbnails with `thumb(src, 56)` and `thumb(src, 96)`; `thumb()` already doubles the size for retina.
- **Failing:** the photo gets `filter:grayscale(1)` to show the state is stale.
- **No photo:**
  - The well shows a centred column (gap 6px) with `ICON.nophoto` (16px, `--muted`) and the words "no photo" (12px, `--muted`).
  - Render the placeholder only when there's no src.
  - On an `<img>` error, replace the img with the placeholder. Never layer the placeholder under an image: with multiply, it would show through white backgrounds.

### Section header: `.group-label`

It changes from a tracked-caps line to a row:

```html
<div class="group-label"><h2>Just dropped</h2><span class="n">· 15</span><button class="btn-text" …>Clear</button></div>
```

- **Row:** `display:flex; align-items:center; gap:8px; margin-top:32px; padding-top:12px; border-top:1px solid var(--rule); min-height:32px`.
- **`h2`:** serif 19px, 500, line-height 1.2, `--bright`, `margin:0`.
- **`.n`:** Hanken 15px, `--text-dim`, tabular. For Waiting it reads "· 20 · nothing to do".
- **Content below:** starts 8px under drops, feeds and alerts; 6px under waiting rows; 12px under the tinted blocks.

## Screens / views

### Main page: phone (≤820px)

One column, in this order:

1. Header
2. `#warnings`, if any
3. Just dropped
4. **In stock** (new header)
5. **Held** (new header)
6. **Failing** (new header)
7. From your feeds
8. Waiting
9. Stores you might watch
10. Recent alerts
11. `#build`
12. The fixed dock

`.body` gets `padding:0 var(--gutter) calc(76px + env(safe-area-inset-bottom))`.

**Header**

- **`.hdr`:** `padding:24px var(--gutter) 0`, flex column, `gap:10px`. Remove the bottom border; the first section's rule separates it.
- **Row 1:** `#eyebrow` (min-height 20px), e.g. "YOUR LIST · WEDNESDAY 23 SEPTEMBER".
- **Row 2:** `display:flex; flex-wrap:wrap; align-items:flex-end; gap:18px 48px`. It holds `h1#headline` (`flex:1 1 300px; min-width:0`) and `#counts` (`flex:1 1 330px; min-width:0`). On a phone they stack.
- **`#counts` / `.counts`:** `display:flex` with no outer border.
- **`.stat`:**
  - Layout: `flex:1 1 0; min-width:0`, flex column, `gap:5px`, `padding:10px 6px 9px`.
  - Every cell except the first gets `border-left:1px solid var(--rule)`.
  - `.stat b`: Hanken 24px, 500, line-height 1, `--bright`, tabular lining. No longer serif.
  - `.stat span`: 13px, line-height 1.2, `--text-dim`, nowrap, `overflow:hidden; text-overflow:ellipsis`. The ellipsis must never trigger.
- **Tones:** in `render()`, `stat()` sets the tones.

  | Stat | Tone | Look |
  |---|---|---|
  | Buyable | `'buy'` (was `'ok'`) | `.stat.buy`: `background:var(--accent)`; numeral and label in `--accent-ink` |
  | Dropped | `''` (was `'ok'`) | ink |
  | Held, To read | `''` | ink |
  | Broken | `'bad'` | `.stat.bad`: numeral stays `--bright`, followed by `GLYPH.failing` in `--failing` (6px gap) |
  | any stat at 0 | `'zero'` | `.stat.zero b`: `--muted` |

  Only a non-zero Buyable fills.

**Headline states**

- "Nothing to act on" gets a `quiet` class and turns `--text-dim`.
- The copy itself is unchanged: "N things to act on", "Nothing to act on", "Nothing watched yet".

### Main page: desktop (>820px)

- **Page:** the content is centred at max-width 1120px plus gutters.
- **Header:**
  - `padding-top:48px`.
  - Row 1: `#eyebrow` on the left and `.hdr-actions` on the right. The actions are theme (44×44), Why no alert? and Add a watch, all quiet, with `gap:8px`.
  - Row 2: `h1` at 40px on the left; `.counts` on the right with `max-width:440px`.
  - Restructure the header markup into those two rows. `.hdr-title` and `.hdr-side` may be reused or replaced; nothing tests them.
- **Two columns.** In `render()`, build `main` and `side` strings and output:
  ```html
  <div class="cols"><div class="col-main">…</div><aside class="col-side">…</aside></div>
  ```
  - `.cols`: `display:flex; flex-wrap:wrap; align-items:flex-start; column-gap:48px`. It's `display:block` on a phone, so source order gives the phone order.
  - `.col-main`: `flex:1 1 560px; min-width:0; max-width:720px`. It holds Just dropped, In stock, Held, Failing and From your feeds.
  - `.col-side`: `flex:1 1 300px; min-width:0; max-width:352px`. It holds Waiting, Stores you might watch and Recent alerts.
  - Make `.col-side` `position:sticky; top:0` only while it is shorter than the viewport. Otherwise leave it static, so Recent alerts can never be trapped off-screen.
  - When `.col-main` would be empty ("Nothing to act on"), render everything in one column. Waiting then sits directly under the header.
  - Below about 1010px the side column wraps under the main one.
- **Everything else:** no dock. `#build` goes under both columns.

### Just dropped: `.bucket`

The whole row is the existing `<button class="bucket">`.

- **Row:** `display:flex; align-items:center; gap:16px; width:100%; min-height:88px; padding:14px 0; border-top:1px solid var(--rule-faint)`. No bottom border on the last row.
  - Pressed or hovered: `background:var(--surface-quiet)`.
- **`.deck` (fan):** a fixed 132×56 box, even with one photo, so text aligns across rows.
  - Up to three `.tn` squares at 56px, absolutely positioned at left 0, 36px and 72px, with z-index 3, 2 and 1.
  - Each has `box-shadow:0 0 0 2px var(--ground)`.
  - No brightness filters.
  - Feed buckets have no `.deck` at all.
- **`.bk-main`:** flex column, `gap:2px`, `flex:1; min-width:0`.
  - `.k` kicker: 13px, line-height 1.3, `--text-dim`. Omit it when empty, as today.
  - `.bk-name`: serif 17px, 500, line-height 1.25, `--bright`, `overflow-wrap:anywhere`.
  - `.bk-meta`: 13px, line-height 1.35, tabular. The count (`<b>`) is `--text` at 400, then " · newest 7s ago" in `--text-dim`.
- **Star:** it moves out of `.bk-meta` to the right edge of the row, as "★ 3". `flex:none`, `--bright`, 13px, 600, gap 4px. Keep the `title`.
- **Remove `.bk-go`** ("View ›"). The row itself is the affordance.

### In stock: `.row.act`

```
div.row.act                   margin:12px calc(-1*var(--bleed)) 0; padding:16px var(--bleed) 12px;
                              background:var(--tint-in-stock); display:flex; flex-direction:column; gap:12px
  div.row-top                 flex; gap:14px; align-items:flex-start
    .shot (96)                photo well
    div.row-text              flex column; gap:3px; min-width:0
      state line              [disc] In stock · your size <span.when> · 12s ago</span>  [+ Armed] [+ Backing off]
      span.kicker             brand, 13px --text-dim, on its own line above the name
      span.name               serif 17/500 --bright
      span.meta               <span.price>$345</span> · watching <b>M</b> · M, L returned · every 5m
  div.chips                   buy chips, preferred size first (max 6, as today)
  div.row-foot                flex; justify-content:space-between; align-items:center; gap:8px; margin-top:-6px
    span.caption              [disc --bright] your size · each chip is that size's cart link   (13px --text-dim)
    span.actions              Edit · Details (text buttons, gap 8px)
```

- **Several In stock rows:** each is its own tinted block, 8px apart.
- **Meta line:** `.meta` is 13px, line-height 1.4, `--text-dim`, with `<b>` in `--text` at 500. The first bit (the price) is wrapped in `.price`: 15px, 500, `--bright`, tabular, nowrap.
- **Caption:** "your size · " and the disc only appear when a preferred size leads.
- **No named sizes:**
  - With a cart URL: one buy button, "Add to cart", captioned "cart permalink · skips product page".
  - Without one: a **quiet** "Open product", captioned "no cart link · opens the product page".
- **Aria label:** the preferred chip's becomes "Add size M, your size, to cart".

### Held: `.row`

```
div.row                       display:flex; gap:14px; align-items:flex-start; padding:16px 0 4px   (no tint, no border)
  .shot.sm (72)
  div.row-text                gap:3px
    state line                [half-circle] Held · not your size <span.when> · 2m ago</span>   (--held)
    span.kicker               brand
    span.name                 serif 17/500 in --text (calmer than --bright)
    span.meta                 $110 · in stock in <b>L</b> only · you watch <b>M</b> · nothing sent, and nothing wrong
    div.actions               margin-top:8px; flex-wrap; gap:8px 16px
                              Also alert on L (quiet) · Edit · Details (text)
```

### Failing: `.row.broken`

```
div.row.broken                margin:12px calc(-1*var(--bleed)) 0; padding:16px var(--bleed) 12px calc(var(--bleed) - 2px);
                              background:var(--tint-failing); border-left:2px solid var(--failing); display:flex; gap:14px
  .shot.sm (72)               the watch's photo, grayscale(1); placeholder if none (replaces the hatched block)
  div.row-text                gap:3px
    state line                [triangle] Failing · stale state   [+ Armed] [+ Paused · after 14 failures]
    span.kicker               brand
    span.name                 serif 17/500 --bright
    div.err                   mono 13px/1.4 --failing; overflow-wrap:anywhere; -webkit-line-clamp:3; title = full error
    span.meta                 14 failures · the in stock reading you see is 2h old   (tabular --text-dim, own line)
    div.actions               margin-top:8px; flex-wrap; gap:8px
                              Fix URL · Check now · Pause/Resume (quiet, padding 0 14px) · Details (text, NEW → detail(id))
```

Details is new here: the error is now clamped to 3 lines, and the Details sheet shows it in full.

### From your feeds

- The section is "From your feeds · N", with a Clear text button.
- Rows are the same `.bucket` as drops, without the fan. The ui-check counts these rows as buckets, so the class must stay.
- No min-height: `padding:14px 0`.
- Content follows the repo: kicker, name, then "1 to read · newest 22m ago".

### Waiting: `.wait`

```
div.wait     display:grid; grid-template-columns:minmax(0,1fr) auto auto;
             grid-template-areas:"n n wa" "s t wa"; column-gap:12px; align-items:center; padding:6px 0
  span.n     area n; line-height:20px; overflow-wrap:anywhere
             <span.k> store 13px --text-dim, inline, margin-right 8px </span> name 15px --text  <span> · size M 13px --muted</span>
  span.s     area s; inline-flex; gap:6px; 13px/500; state colour; glyph for EVERY state (see table)
  span.p     display:none (price lives in Details)
  span.t     area t; 13px --muted tabular; nowrap; justify-self:end   "31s ago · 5m" (shown on phones too now)
  span.wa    area wa; align-self:center; Edit (text) + × delete (44×44, margin-right -14px)
```

- **No per-row borders.** Every fifth row gets a divider:
  ```css
  .wait:nth-child(5n+1):not(:first-child){border-top:1px solid var(--rule-faint); margin-top:6px; padding-top:12px}
  ```
- **List:** starts 6px under the header.
- **Delete:** keep the existing × and its `removeWatch()` confirm.
- **Wrapping:** long statuses wrap within area `s`, e.g. "Watching · 1,204 tracked · 1,188 in the feed now". They never share a track with the name, which is the bug ui-check guards against.
- **Details sheet:** stop reusing `.wait` for its check list (see Details).

### Stores you might watch: `.sugg`

The section is "Stores you might watch · N". On desktop it's in the side column.

- **Row:** `display:grid; grid-template-columns:minmax(0,1fr) auto; gap:4px 16px; align-items:center; padding:14px 0; border-top:1px solid var(--rule-faint)`. No last-child border.
- **`.sn`:** serif 17px, 500, line-height 1.25, `--bright`, `overflow-wrap:anywhere`.
  - `.sn .k` (the city) is a block line above it: 13px, `--text-dim`, sentence case, `margin-bottom:2px`.
- **`.sb`:** 13px, line-height 1.4, `--text-dim`, with `<b>` in `--text` at 500.
- **`.sa`:** Watch sale and Watch new become `chip mini btn-quiet`, min-height 44px, `gap:8px`.
  - Desktop: column 2, spanning both rows.
  - Phone: `grid-column:1/-1`, with the buttons at `flex:1`.

### Recent alerts: `.feed`

The section is "Recent alerts · N", with "Clear all" as a text button on the right.

```
div.feed     display:flex; align-items:flex-start; gap:10px; font-size:14px; line-height:20px
  span.t     flex:none; width:54px; padding-top:12px; 13px --muted tabular; nowrap
  span.fm    NEW wrapper; flex:1; min-width:0; padding-top:12px; overflow-wrap:anywhere; -webkit-line-clamp:3 (title = full)
             <span.fs> kind 500 --bright </span><span.fw> · evName · note  --text-dim </span>
  button.x   44×44; margin-right:-14px; --muted
```

- The kind word is `--bright` for every kind except "Watch broke", which is `--failing` and led by `GLYPH.failing`.
- Links inside `.fw` use `color:inherit`, with no underline.
- Keep `slice(0, 25)`.

### Footer: `#build`

- Replace the inline style in `start()` with `padding:40px 0 24px; font:12px/1 var(--mono); color:var(--muted)`, and drop the `caption` class.
- The text stays "BUILD 6410bff" (literal capitals in the string).

### Dock: `.dock` (phone only)

- **Position and look:** `position:fixed; left:0; right:0; bottom:0; z-index:50`, `background:var(--ground)`, `border-top:1px solid var(--rule)`, no shadow.
- **Padding:** `12px max(var(--gutter), env(safe-area-inset-right)) calc(12px + env(safe-area-inset-bottom)) max(var(--gutter), env(safe-area-inset-left))`.
- **Layout:** `display:flex; gap:8px`.
- **Contents:**
  - theme: 44×44, `flex:none`
  - Why no alert?: quiet, `flex:1`
  - Add a watch: `btn-ghost btn-accent`, i.e. quiet (not filled), `flex:1`
- **Buttons:** min-height 44px, `padding:0 12px`, no letter-spacing.
- **Wide screens:** hidden above 820px.

### Sheets: shared chrome (`#add.overlay > .sheet`)

**Phone (≤820px)**

- **`#add`:** `align-items:flex-end; padding:0`, scrim behind.
- **`.sheet`:**
  - Size: `width:100%; max-height:92vh; max-height:92dvh; overflow-y:auto; overscroll-behavior:contain`.
  - Look: `background:var(--ground)`, border only on top (`1px solid var(--rule)`), radius 0.
  - Padding: `0 var(--gutter)`.
- **Grab handle:** `.sheet::before` is 36×4px, `background:var(--border)`, `border-radius:2px`, `margin:8px auto 6px`.
  - In the drop sheet, move the handle into `.sheet-head::before` so it stays pinned; that sheet's own `::before` is hidden.
- **Title block:** `h2` at 26px. `.sub` is 13px, line-height 1.4, `--text-dim`, `margin:6px 0 0`. The body starts 24px below.
- **`.sheet-actions`:**
  - Pinned: `position:sticky; bottom:0; z-index:2; background:var(--ground); border-top:1px solid var(--rule)`.
  - Full bleed: `margin:24px calc(-1*var(--gutter)) 0; padding:12px var(--gutter) calc(12px + env(safe-area-inset-bottom))`.
  - Layout: flex, centred, `flex-wrap:wrap; gap:8px 16px`.
  - The strong quiet button takes `flex:1`.

**Desktop (>820px)**

- **`#add`:** `align-items:center; justify-content:center; padding:40px 20px`.
- **`.sheet`:**
  - `max-width:720px; max-height:86vh; overflow-y:auto`.
  - `border:1px solid var(--rule)`, `padding:28px 32px 0`. No handle.
- **`.sheet-actions`:** `margin:24px -32px 0; padding:16px 32px 20px`.

**Open and close.** Only `showSheet()` and `closeSheet()` change:

- `showSheet()`:
  1. Remove `.hide`.
  2. Add `body.locked`.
  3. Force a reflow (`void o.offsetWidth`).
  4. Add `.open`.
- The CSS animates `#add .sheet` from its closed pose to `#add.open .sheet`, and the scrim `#add` → `#add.open`, per Motion.
- `closeSheet()`: remove `.open`, add `.hide`, and remove `body.locked`, all at once.
- A 10-second redraw that replaces `#add`'s innerHTML while it's open simply appears in the open pose. That's correct.

### Drop sheet: `.bucket-sheet`

The structure stays as today (see collision 2).

**Head (`.sheet-head`)**

- Pinned: `position:sticky; top:0; z-index:2; background:var(--ground)`.
- Layout: `display:flex; align-items:flex-start; gap:12px`. Padding is `2px 0 14px` on phone (after the handle) and `28px 0 16px` on desktop. No bottom rule.
- **Left column:** flex, `gap:3px`.
  - `.eyebrow` kicker: 13px, line-height 1.3, `--text-dim`. Not caps; scope the caps style to `.hdr .eyebrow`.
  - `h2`: 26px, `margin:0`, `overflow-wrap:anywhere`.
  - `.sub`: 13px, line-height 1.35, `--text`, tabular. For example: "12 buyable items · newest 7s ago".
- **Close:** a 44×44 `.x` in `--text`, `margin:-4px -14px 0 0`.

**Item (`.item`)**

```
div.item          display:grid; grid-template-columns:96px minmax(0,1fr); gap:12px; padding:16px 0;
                  border-top:1px solid var(--rule-faint)   (first row keeps it; there is no rule under the head)
  div.item-media  NEW; flex column; align-items:flex-start; gap:8px
                  a[tabindex=-1] > .tn (96)  ·  the tag, moved here from .item-main .k
  div.item-main   flex column; gap:3px; min-width:0
    div           flex; gap:6px; align-items:flex-start:  ★ (margin-top 4px, if starred) + .item-title
                  .item-title: serif 17/500, line-height 20px, --bright, 2-line clamp, title attr = full title
    div           flex-wrap; align-items:baseline; column-gap:8px:  .price (15/500 --bright) + "≈$403 landed"
    div.item-meta 13px/1.35 --muted tabular:  7s ago · 3m behind   (.lag.slow → --armed + backoff glyph)
    div.item-acts margin-top:8px; flex; gap:8px:
                  Cart (buy, a.chip.mini.btn-buy) · Open / Read (quiet, a.chip.mini.btn-quiet) · × (margin-left:auto)
```

- "Open" is always quiet now, even when there's no Cart.
- The "no link" fallback caption is 13px, `--muted`.

**Footer (`.sheet-actions`)**

- "Open the store" becomes a quiet button, `a.btn-ghost`, with `flex:1` and centred text.
- "Clear all 12" is a text button, `margin-right:-8px`.

### Add a watch (`openAdd()`)

- **Title:** "What do you want to be told about?"
- **Sub:** "Three different questions. Pick the one you'd actually ask out loud."
- **Body:** blocks 24px apart.
  1. Intent cards (see Components).
  2. `URL` field, with the hint "paste it, we'll identify it". `#aUrl` is mono 16px, followed by `#detect`.
  3. `#kwField`: the Keywords field, with its note.
  4. `#sizeField`: **still a text input** (`#aSize`, placeholder "m, l"). Sizes are free-form (32, 9, 48, M), so the reference's S/M/L/XL chips aren't built in this pass.
     - The note under it gets `class="warn note"` (see Warnings).
  5. How often: `.seg` with 45s / 5m / 15m.
- **Actions:** Start watching (`#saveBtn`, `btn-quiet strong`, `flex:1`), Cancel (text), and `#addErr` (13px, `--failing`).
- **Suggested store filter:** `#aVendors` keeps the boxed `.warn` style.

### Edit watch (`edit()`)

- **Title and sub:** "Edit watch", and "brand · title" as the sub.
- **Fields:**
  - Name: Hanken, 16px.
  - URL: mono 16px, with the hint "strategy · kind".
  - Keywords or Size preference, each with a `warn note`.
  - How often: `.seg`.
  - `#eWarn`: boxed `.warn`.
- **Actions:** Save changes (`#eSave`, `btn-quiet strong`), Cancel (text), Pause watching / Resume watching (text), and Delete (text, `--failing`, `margin-left:auto`), plus `#eErr`. On a phone the actions wrap inside the sticky footer.

### Details (`detail()`)

- **Head:**
  - `h2` is the watch name.
  - `.sub` is the URL link: mono 13px, `--text-dim`, underlined, `overflow-wrap:anywhere`.
- **State:** the state eyebrow, plus " · every 5m".
- **Size:** "Watching size **M**" as `.meta`.
- **Error:** `last_error` in full (mono 13px, `--failing`, unclamped).
- **Checks:**
  - A section header reads "Last N checks", with `margin-top:24px`.
  - Each check row uses a **new `.check` class** instead of `.wait`: `display:grid; grid-template-columns:72px 56px 48px minmax(0,1fr); gap:12px; padding:8px 0; border-top:1px solid var(--rule-faint); font-size:13px`, tabular.

  | Column | Content |
  |---|---|
  | time | `--muted` |
  | result | `GLYPH.in_stock` + "ok" in `--in-stock`, or `GLYPH.failing` + "fail" in `--failing` |
  | HTTP status | mono, `--text-dim` |
  | error or state | mono, `--text-dim`, nowrap, ellipsis |

  - Drop the inner `max-height:300px` scroll box; the sheet already scrolls.
- **No checks yet:** `.empty`.
- **Actions:** Close (quiet).

### Why didn't this alert? (`openInspect()` / `runInspect()`)

- **Head:** title "Why didn't this alert?", then the sub.
- **Field:** `Product URL` (`#iUrl`, mono 16px).
- **Actions:** Look (`btn-quiet strong`) and Close (text).
- **Loading:** "Asking the store…" as `.sub`, in `--text-dim`.
- **Summary:** `.sub`, with the product title in `<b>` at 500 in `--bright`.
- **Source rows (`.fired`):**
  - Row: `display:grid; grid-template-columns:minmax(0,1fr) auto; gap:4px 16px; align-items:baseline; padding:12px 0; border-top:1px solid var(--rule-faint)`.
  - `.fi .k`: the label, as a 13px `--text-dim` block. For example: "Catalogue feed · what we poll".
  - The value after it is a glyph plus a word at 15px, 500:

    | Value | Glyph | Colour |
    |---|---|---|
    | Buyable | disc | `--in-stock` |
    | Not buyable | ring | `--muted` |
    | Did not say | dashed ring | `--no-baseline` |

  - `.ft`: the note, 13px, `--muted`. It sits right on desktop and wraps under on a phone (`grid-column:1/-1`).
- **Watch verdict rows:** same layout. The watch name is `.k`, followed by an optional `tag` "not covered". The verdict is 15px `--text`, and "swept …" goes in `.ft`.
- **"Already sent about this":** the lines are 13px `--text`, tabular.
- **Disagreement, notes, errors, and "Nothing is watching this store.":** boxed `.warn`.

### Sign in (`#login`)

- **Page:** `#login.overlay` gets `background:var(--ground)`, not the scrim, because it *is* the page.
  - Phone: aligned to the top, `padding:24px var(--gutter)`.
  - Desktop: centred.
- **Card (`.sheet`):** max-width 420px, `1px solid var(--rule)` all round, `padding:32px` (24px 18px on phone). No handle and no animation.
- **Content:**
  - `h2` "Restock".
  - `.sub` "Enter your dashboard password." at 13px, `--text-dim`.
  - `#pw` at 48px, Hanken 16px.
- **Actions:** these are static (not sticky, no rule). "Sign in" is `btn-quiet strong`, min-width 120px. `#loginErr` is 13px, `--failing`.
- **Optional hint:** the design PDF suggested adding "Faster: send /login to Muz". Add it only if the Telegram bot really has a `/login` command.

### Toast (`toast()`)

- **Position:** fixed, centred with `left:50%; transform:translate(-50%, 0)`.
  - Phone: `bottom:calc(88px + env(safe-area-inset-bottom))`, `width:calc(100% - 32px)`.
  - Desktop: `bottom:24px`, `max-width:480px`.
- **Look:** `background:var(--surface); border:1px solid var(--border); color:var(--bright)`, 14px, line-height 1.4, `padding:12px 16px`, radius 0, no shadow.
- **Variants:** `.toast.bad` uses `--failing` for border and text. `.toast.good` uses an `--in-stock` border with `--bright` text.
- **Behaviour:**
  - Set `role="status"`.
  - Add `.show` after a forced reflow; this is the enter.
  - After 4s, remove `.show`. After 160ms more, remove the node.

### Warnings and notes: `.warn`

- **Boxed `.warn`** is for things you must notice:
  - `#warnings` ("Telegram is not configured — …")
  - `#eWarn` and `#aVendors`
  - inspect disagreements, notes and errors

  Style: `background:var(--surface-quiet); border-left:2px solid var(--armed); padding:12px 14px; margin:16px 0 0`, 13px, line-height 1.45, `--text`. `<b>` is `--bright` at 600, and `.mono` stays 13px.
- **`.warn.note`** (add `note`) is plain helper text under the Keywords and Size preference fields in Add and Edit.
  - Style: no background, border or padding; `margin:0`; 13px, line-height 1.4, `--text-dim`. `<b>` is `--text` at 500.

### Empty and quiet states

- **Nothing watched yet:**
  - The headline reads "Nothing watched yet" and every stat is a muted 0.
  - `.empty`: 15px, line-height 1.45, `--text-dim`, `padding:24px 0`, `border-top:1px solid var(--rule)`. The repo copy stays, followed by a quiet "Add a watch" button (`openAdd()`) 16px below.
- **Nothing to act on:**
  - The headline turns `--text-dim` and the stats are zeros.
  - On desktop it becomes one column, with Waiting directly under the header.

## Interactions & behaviour

These all behave as today:

- Tapping a drop row calls `openBucket()`.
- Size chips open their cart URL in a new tab.
- Also alert on L, Check now, Pause/Resume, Clear, Clear all, dismiss, delete, the `confirm()` prompts, and Escape or tapping the scrim to close.

What changes:

- **Enter motion** for sheets and toasts, as in Motion. Everything closes instantly.
- **Pressed states** are instant: buy uses brightness(.88) + 1px down; quiet uses `--surface`; rows use `--surface-quiet`. Hover mirrors these only inside `@media (hover:hover)`.
- **Focus-visible rings** go on every control (see Space, layout, shape).
- **The 10-second refresh** still re-renders `#sheet`. Keep `renderBucket()`'s signature check and its `scrollTop` restore. Armed uses `armedGlyph()`, so its blink doesn't restart.
- **Theme:** the toggle logic doesn't change. The icon shows where a tap goes: a sun in dark, a moon in light.
- **Reduced motion:** sheets, scrim and toasts take 1ms, and Armed is static.

## State management

There is no new app state. The code changes are:

- `stat()` tones: Buyable → `'buy'`, Dropped → `''`.
- `render()` builds main and side columns, adds the In stock, Held and Failing headers, and marks the headline `quiet` when there is nothing to act on.
- `eyebrowFor(state, extra, time)` takes a separate time.
- `arrivalTag()` adds the `back`, `relisted` and `unverified` classes.
- `waitRow()` shows a glyph for every state, with `not_yet` and `backoff`.
- `showSheet()` and `closeSheet()` handle the `.open` class.
- `toast()` sets `role="status"` and runs the `.show` lifecycle.
- `thumb()` renders the no-photo placeholder and swaps to it on error.

## Copy changes

Everything else keeps its current wording. Sentence case is a CSS change only; the strings already are.

1. New section headers: "In stock · N", "Held · N", "Failing · N".
2. The your-size chip goes from "M ⟶ cart" to "● M → cart". Both marks are SVG, and the words are the same.
3. The size caption becomes "● your size · each chip is that size's cart link" when a preferred size leads.
4. The tag "unverified" becomes "unverified?".
5. Inspect sources: "buyable / not buyable / did not say" become "Buyable / Not buyable / Did not say", each with a glyph.
6. Field labels: "Url" becomes "URL", and "Product url" becomes "Product URL". They were only ever seen through an uppercase transform.
7. The Failing row gains a "Details" text button.
8. Drop rows lose "View ›".
9. The preferred chip's aria-label becomes "Add size M, your size, to cart".

## Implementation order and checks

1. Paste `kinari-tokens.css` in place of both token blocks. Swap the font link, theme-color values and color-scheme meta.
2. Base styles: body type, links, focus ring, radius 0. Strip uppercase, tracking and transitions.
3. Buttons: add the classes in every template, swap `&times;` for `ICON.x`, remove the inline colours and sizes.
4. Paste `glyphs.js` plus its CSS. Update `eyebrowFor`, `armedBadge`, `backoffBadge` and `waitRow`.
5. Header, stats and dock.
6. Section headers and the two-column wrapper in `render()`.
7. Rows: bucket, act, held, broken, feeds, wait, sugg, feed, and photos.
8. Sheets: shared chrome and motion, then drop, Add, Edit, Details, Inspect and Sign in.
9. Toast, warnings and empty states.
10. Verify:
    - Apply the `ui-check.py` contrast patch, then run `python3 ui-check.py`. It must pass at all five widths.
    - Run `monitor/venv/bin/python -m pytest monitor/tests -c monitor/pytest.ini`.
    - Compare `/tmp/ui-*.png` (dark) and `/tmp/ui-*-light.png` against `reference/Kinari Reference.dc.html`.
    - Test on a real phone in daylight: vermilion vs plum, and light mode inside Telegram.
    - Pushing to `main` deploys within five minutes, so push only after all of the above pass.

## Assets

- **Fonts:** Newsreader (400/500, optical sizes) and Hanken Grotesk (400/500/600) from Google Fonts. Mono is the system stack.
- **Icons:** every glyph and icon is inline SVG in `glyphs.js`: the ten state glyphs, star, ×, arrow, your-size disc, radio and the no-photo hanger. Keep the existing SUN/MOON theme icons.
- **Photos:** there are no image assets. Product photos come from the stores through `thumbUrl()`, as today. The reference shows grey placeholders.

## Files

| File | What it is |
|---|---|
| `README.md` | This spec |
| `kinari-tokens.css` | Paste-ready token blocks, both modes, legacy aliases, gutters |
| `glyphs.js` | Paste-ready `GLYPH` / `WORD` / `INK` / `ICON` / `armedGlyph()`, plus their CSS |
| `reference/Kinari Reference.dc.html` | Open in a browser. It shows the phone at 393px (main page, drop sheet, Add a watch) and desktop at 1280px, in light and dark, plus a glyph legend |
| `reference/RestockMain.dc.html`, `RestockDropSheet.dc.html`, `RestockAddWatch.dc.html` | The components the reference renders, driven only by the tokens. Read their inline styles for any exact value not stated here |
| `reference/support.js` | The runtime the `.dc.html` files need |

In the repo, the changes go into `monitor/static/index.html`. `ui-check.py` changes only by the contrast patch.
