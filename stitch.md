# RAVEN — UI Design Brief for Google Stitch

> Goal: redesign the RAVEN demo dashboard. The current build works but looks generic and
> "AI-default" (dark slate background, cyan→purple neon gradients, glowing borders). We want
> the opposite: **calm, editorial, minimal, premium**. Lots of whitespace, restrained color,
> excellent typography, content-first. Think the quiet confidence of Linear / Stripe docs /
> Vercel / Things 3 / a well-set print magazine — NOT a "cyberpunk AI dashboard".

---

## 1. Product context (so the screens carry real content)

RAVEN gives each AI agent a tiny **context passport**: only the facts that agent's role needs,
instead of dumping a user's entire memory into every agent (expensive + over-exposed). The demo
proves it three ways and is shown as a dashboard.

- **The problem visual:** a big messy pile of personal "memory" (chats, notes, receipts) with a
  few decision-critical facts buried inside.
- **The fix visual:** per-agent passports — each agent sees a 2–4 line slice, not the whole pile.
- **The proof:** a live benchmark — full memory scores 5/5 but is expensive; naive compression
  drops to 4/5; RAVEN keeps 5/5 at a fraction of the tokens.

Audience: hackathon judges. The UI must read clearly from 2 meters away and tell the story in
~30 seconds per screen.

---

## 2. Design principles

1. **Minimal, not empty.** Generous whitespace, clear hierarchy, one idea per region.
2. **Content-first.** The data (facts, passports, numbers) is the hero; chrome recedes.
3. **One accent color, used sparingly.** Color means something (kept vs dropped, the brand).
4. **Quiet surfaces.** Flat or near-flat cards, hairline borders, at most a very soft shadow.
5. **Typographic contrast does the work** — a refined serif display + clean sans + mono for data.
6. **Calm motion.** Subtle, fast (120–180ms) fades/slides only; no glow pulses, no parallax.
7. **Light theme by default** (paper-like). A dark variant is optional, but the primary look is light.

### Explicitly AVOID (this is what makes it look "AI-generic"):
- Dark navy/slate backgrounds with neon **cyan/purple gradients**; glowing/blurred borders.
- Glassmorphism (frosted translucent panels), heavy drop shadows, gradient-filled buttons.
- Emoji as UI icons; rounded-everything bubbles; "techy" monospace for body text.
- Rainbow data viz. Use one accent + neutrals + two semantic colors only.

---

## 3. Aesthetic direction

Editorial-minimal. A warm paper background, near-black ink, one deep restrained accent, and a
serif display face for headlines that gives it a "considered, trustworthy" feel (this is about
*credentials/passports*, so it should feel calm and precise, not flashy).

---

## 4. Design tokens

### Color (light theme — primary)
| Token | Hex | Use |
|---|---|---|
| `bg` | `#F7F6F2` | app background (warm paper) |
| `surface` | `#FFFFFF` | cards / panels |
| `surface-sunken` | `#F2F1EC` | insets (memory list, passport block) |
| `border` | `#E7E5DE` | hairline borders / dividers (1px) |
| `ink` | `#17181B` | primary text / headlines |
| `ink-muted` | `#5C6066` | secondary text, labels |
| `ink-faint` | `#9A9DA3` | meta, captions, placeholders |
| `accent` | `#0F6E5C` | brand / primary actions / active (deep teal-green) |
| `accent-soft` | `#E4F0EC` | accent backgrounds (active tab tint, selected card) |
| `kept` | `#1C7C4A` | "fact kept / constraint satisfied" (green) |
| `dropped` | `#B23A2E` | "fact dropped / constraint missed" (muted red) |
| `highlight-bg` | `#FBF0CE` | the buried "gold facts" highlight background |
| `highlight-ink`| `#7A5A00` | text on highlight |

Keep saturated color to <10% of any screen. Most of the UI is paper + ink + hairlines.

### Optional dark variant (secondary; only if Stitch offers a toggle)
bg `#15161A`, surface `#1B1D22`, border `#2A2D34`, ink `#ECEDEF`, ink-muted `#A3A7AE`, accent
stays `#2FA98F` (slightly lifted). Still flat — no gradients/glow.

### Typography (Google Fonts)
- **Display / headlines:** `Fraunces` (a soft, modern serif) — weights 400/500, optical size for
  large sizes. Used for the app title and section headlines. (Fallback: `Instrument Serif`.)
- **Body / UI:** `Inter` — 400/500/600. All labels, buttons, body, table text.
- **Data / numbers / passport text:** `IBM Plex Mono` — 400/500. Token counts, $ figures, the
  rendered passport block, fact-type tags.

Type scale (px / line-height / weight):
- Display title: 30 / 1.15 / Fraunces 500
- Section headline (panel `<h2>`): 13 / 1.2 / Inter 600, UPPERCASE, letter-spacing 0.08em, color `ink-muted`
- Body: 14 / 1.55 / Inter 400
- Small / meta: 12 / 1.5 / Inter 400, color `ink-muted`
- Big stat (e.g. "93%"): 40 / 1 / IBM Plex Mono 500
- Numbers in tables/meters: 13 / IBM Plex Mono 400

### Spacing, radius, elevation
- Spacing scale (px): 4, 8, 12, 16, 24, 32, 48. Page padding 32; card padding 20–24; gap between cards 16–20.
- Radius: cards 12, inputs/buttons 8, pills 999. Keep consistent; nothing more rounded than 12 except pills.
- Borders: 1px `border` everywhere. Prefer borders over shadows.
- Shadow: at most one, very soft — `0 1px 2px rgba(20,20,20,0.04)`. No glows.
- Max content width: 1200–1320px, centered.

---

## 5. App shell (every screen)

- **Top bar** (height ~64): left = wordmark "**RAVEN**" (Inter 600) + a one-line subtitle in
  `ink-muted` ("recipient-aware context compression for the agentic web"). No logo image needed.
  Right side empty (or a small "Fetch.ai · ASI:One" text chip in `ink-faint`).
- **Tab nav** below the bar: 3 text tabs — **Dashboard**, **RELAY**, **Compress**. Active tab =
  `ink` text with a 2px `accent` underline; inactive = `ink-muted`, no box. Pill-style is also ok
  but underline is cleaner/minimal.
- **Content area:** the active screen.

---

## 6. Screens to generate

### SCREEN 1 — Dashboard (the hero; 3-column layout)
Three equal-ish columns on desktop (left 1fr, middle 1.1fr, right 0.95fr), each a `surface` card
with 1px border, radius 12. Stack to one column under ~1000px.

**Column A — "User memory"**
- Panel headline: `USER MEMORY` with a count chip on the right: `38 items · 127 facts` (mono).
- Sub-caption (small, muted): "Everything you'd dump into an agent. The 5 decision-critical facts
  are buried (highlighted)."
- A scrollable list (max-height ~560px) of memory items. Each item: a `surface-sunken` rounded
  row (radius 8, padding 10–12), with a tiny uppercase `kind` label in `ink-faint` (e.g. CHAT,
  NOTE, RECEIPT) then the text in body size. Buried "gold" facts are shown inline with a
  `highlight-bg` marker behind the key phrase (e.g. **vegetarian**, **under $40**, **confirm
  before paying**, **5:30**, **loud**). 1–2 items should clearly show the highlight.
- A small "+ Upload a PDF / doc → memory" secondary button at the top of the list (outline style).

**Column B — "Agents · passports"**
- Headline: `AGENTS · RECIPIENT-AWARE PASSPORTS`.
- Sub-caption: "Raw: every agent gets all 127 facts (~2,758 tok). RAVEN: each gets only its slice."
- A vertical list of 4 **agent cards** (roles: restaurant, calendar, budget, writer). Each card:
  - Row 1: role name (Inter 600, capitalized) on the left; on the right a small pill in
    `accent`/`accent-soft` showing `211 tok · −93%` (mono).
  - Row 2 (small, muted): `sees 6 facts · denied 121 · ~$0.0002/send`.
  - Cards are clickable/expandable. The **expanded** state reveals the passport (see component
    spec): a list of the kept facts (each with a small `type` tag) and a monospace passport block.
  - Selected/expanded card: 1px `accent` border + `accent-soft` tint. Others plain.

**Column C — "Token meter · live decision"**
- Headline: `TOKEN METER · LIVE DECISION`.
- **Token meter:** two horizontal bars to compare:
  - "Raw — full memory to all 4 agents": a full-width bar in a neutral/`dropped`-tinted fill, label `11,032 tok`.
  - "RAVEN — tailored passports": a short bar (~7% width) in `accent`/`kept` fill, label `771 tok`.
  - Below: a big stat `93%` (mono, `kept` color) + caption "fewer context tokens delivered across the workflow".
- **Live benchmark:** a primary button "▶ Run decision benchmark (live)". When loading, show a
  small spinner + "agents deciding…". Results render as 3 rows (a tiny table / list):
  | condition | score | tokens |
  |---|---|---|
  | raw (full) | **5/5** (kept color) | 8,308 tok · ~$0.02 |
  | generic | **4/5** (dropped color) + "missed: confirm_before_pay" | 1,114 tok |
  | **RAVEN** | **5/5** (kept color) | 1,030 tok |
  - The RAVEN row is subtly emphasized (1px `accent` left border or `accent-soft` tint).
  - Footnote (small, faint): "RAVEN matches raw's quality at a fraction of the recurring cost;
    generic, at the same per-agent budget, drops the standing 'confirm before paying' rule.
    $ is a rough estimate; tokens are the real metric."

### SCREEN 2 — RELAY (agent → agent handoff compression)
A single wide `surface` card.
- Headline: `RELAY · AGENT → AGENT HANDOFF COMPRESSION`.
- Caption: "Forward the latest message + a compressed back-context passport, instead of the whole
  growing transcript."
- A clean table (hairline row dividers, right-aligned numeric columns in mono):
  | hop | full transcript | last message | RAVEN relay | vs full |
  |---|---|---|---|---|
  | → restaurant | 2,792 | 0 | 231 | 92% |
  | → budget | 2,895 | 103 | 225 | 92% |
  | → writer | 3,125 | 80 | 233 | 93% |
  | **TOTAL** | **8,560** | **183** | **751** | **91%** |
- Two badges below: a `kept` pill "RAVEN keeps 'vegetarian' on 3/3 hops" and a `dropped` pill
  "last-message keeps it on only 1/3".
- Footnote (faint): "RAVEN costs a little more than last-message-only but preserves the standing
  back-context constraints last-message silently drops — at 91% below the full-transcript
  broadcast. Single illustrative scenario; savings are scale-driven."

### SCREEN 3 — Compress anything
A single `surface` card, comfortable form layout.
- Headline: `COMPRESS ANYTHING FOR AN AGENT`.
- Caption: "Paste a memory blob, pick a recipient role, get its passport."
- A `role` dropdown (restaurant / calendar / budget / writer).
- A multiline textarea (min-height ~130px, mono or body), pre-filled with an example memory.
- A primary button "Compress".
- Result area: a small meta line ("facts kept: 2 · 49 tok (raw 82)") + a monospace passport block
  (the rendered passport).

### Global states to design (show these explicitly):
- **Loading:** subtle text "loading…" or a thin spinner; never a full-screen blocker.
- **Error / backend down:** a single inline banner in `dropped` tint: "⚠ Backend not reachable —
  start it with `uvicorn …`". Calm, not alarming.
- **Empty:** e.g. compress with no relevant facts → quiet muted message.

---

## 7. Component spec (reusable)

- **Button (primary):** solid `accent` fill, white text, radius 8, 11px/18px padding, Inter 600,
  no gradient. Hover = 6% darker. Disabled = 50% opacity.
- **Button (secondary/outline):** `surface` fill, 1px `border`, `ink` text. Used for Upload.
- **Card:** `surface`, 1px `border`, radius 12, padding 20–24, optional 1px soft shadow.
- **Panel headline (`h2`):** the uppercase tracked label style above; with an optional right-aligned
  count chip (mono, `accent`).
- **Pill / badge:** radius 999, 2–8px padding, 11–12px. Variants: `accent`, `kept` (green on
  `#EAF5EE`), `dropped` (red on `#FBEAE7`), `neutral` (ink-muted on `surface-sunken`).
- **Memory item:** `surface-sunken` row, radius 8; `kind` micro-label; body text; `<mark>` uses
  `highlight-bg`/`highlight-ink`.
- **Agent card:** as described; collapsed + expanded states.
- **Passport block:** `surface-sunken` (or a faint `#0d0d0d` only in dark mode), 1px border,
  radius 8, IBM Plex Mono 12px, with section labels "HARD CONSTRAINTS" / "RISK FLAGS" / "CONTEXT"
  in `ink-muted` and "- " bulleted facts. This is a code-like block but tasteful.
- **Fact row (in expanded passport):** a small uppercase `type` tag in `accent` (e.g. DIETARY,
  BUDGET_LIMIT, PERMISSION) + the fact text.
- **Token meter bar:** rounded (radius 6) horizontal bars; raw = neutral/red-tint, RAVEN = accent;
  width encodes token ratio; numeric label inside or trailing in mono.
- **Result row (benchmark):** score in large mono colored by kept/dropped; condition name; tokens.
- **Tabs:** underline-active as described.
- **Toast/banner:** inline, `dropped` tint for errors, `kept`/muted for success.
- **Spinner:** thin 2px ring, `accent` or `ink`; small.

---

## 8. Microcopy (use verbatim where possible)
- Title: "RAVEN" · subtitle "recipient-aware context compression for the agentic web"
- Tabs: "Dashboard", "RELAY (agent→agent)", "Compress anything"
- Memory caption: "Everything you'd dump into an agent. The 5 decision-critical facts are buried (highlighted)."
- Benchmark button: "▶ Run decision benchmark (live)" / loading "agents deciding…"
- The numbers in §6 are the real demo numbers — keep them.

---

## 9. Responsive
- ≥1000px: 3-column dashboard. <1000px: single column, cards stack in order A → B → C.
- Tables: allow horizontal scroll on narrow screens rather than wrapping.
- Tap targets ≥40px on touch.

## 10. Accessibility
- Body text contrast ≥ 4.5:1 (ink on bg passes). Don't encode meaning by color alone — kept/dropped
  rows also carry text ("5/5" / "missed: …").
- Visible focus ring (2px `accent`, 2px offset) on interactive elements.

## 11. Deliverables I want from Stitch
1. The **Dashboard** screen (3 columns, all components populated with the §6 content).
2. The **RELAY** screen.
3. The **Compress** screen.
4. The collapsed + expanded **agent card** states; the **error banner** state.
5. A small **design-system page** (colors, type scale, buttons, pills, meter bar) so I can map
   tokens to CSS variables.

> Implementation note (for me, after Stitch): I'll translate the generated design system into the
> existing Next.js app — CSS variables in `frontend/app/globals.css` and the components in
> `frontend/app/page.js` (MemoryPane, AgentsPane/AgentCard, Meter, Benchmark, RelayView,
> CompressBox). Keeping the same component structure, so a clean token + layout spec is what
> matters most.
