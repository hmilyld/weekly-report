---
name: 日周报管理系统
description: 日历即记录格的工作记录系统 — 日报汇成周报与月报
colors:
  blueprint: '#f4f6f9'
  surface: '#ffffff'
  paper-inset: '#fafbfd'
  paper-sunk: '#f0f3f8'
  rule-hair: '#e6ebf2'
  rule-mid: '#d3dae6'
  rule-bold: '#aeb9c8'
  ink: '#111111'
  ink-secondary: '#565d68'
  ink-muted: '#6e757f'
  signal: '#0057ff'
  signal-hover: '#0046cc'
  signal-tint: '#eef3ff'
  cyan-monthly: '#0fa3b9'
  danger: '#c4271d'
  warning: '#9a5b00'
  success: '#0b7a3e'
typography:
  display:
    fontFamily: 'Saira Semi Condensed, Noto Sans SC, sans-serif'
    fontSize: '1.75rem'
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: '-0.032em'
  title:
    fontFamily: 'Saira Semi Condensed, Noto Sans SC, sans-serif'
    fontSize: '1.375rem'
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: '-0.032em'
  body:
    fontFamily: 'IBM Plex Sans, Noto Sans SC, sans-serif'
    fontSize: '0.875rem'
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: '-0.006em'
  label:
    fontFamily: 'IBM Plex Sans, Noto Sans SC, sans-serif'
    fontSize: '0.8125rem'
    fontWeight: 600
    lineHeight: 1.45
  data:
    fontFamily: 'IBM Plex Mono, ui-monospace, monospace'
    fontSize: '0.75rem'
    fontWeight: 400
    lineHeight: 1.6
rounded:
  xs: '2px'
  sm: '4px'
  md: '6px'
  lg: '10px'
  pill: '999px'
spacing:
  '1': '4px'
  '2': '8px'
  '3': '12px'
  '4': '16px'
  '5': '20px'
  '6': '24px'
  '8': '32px'
  '10': '40px'
  '12': '48px'
  '16': '64px'
components:
  button-primary:
    backgroundColor: '{colors.ink}'
    textColor: '{colors.surface}'
    rounded: '{rounded.sm}'
    padding: '0 16px'
    height: '40px'
  button-primary-hover:
    backgroundColor: '#2a2a2a'
  button-accent:
    backgroundColor: '{colors.signal}'
    textColor: '#ffffff'
    rounded: '{rounded.sm}'
    padding: '0 16px'
    height: '40px'
  button-outline:
    backgroundColor: 'transparent'
    textColor: '{colors.ink}'
    rounded: '{rounded.sm}'
    padding: '0 16px'
    height: '40px'
  button-ghost:
    backgroundColor: 'transparent'
    textColor: '{colors.ink-secondary}'
    rounded: '{rounded.sm}'
    padding: '0 16px'
    height: '40px'
  input:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    rounded: '{rounded.sm}'
    padding: '8px 12px'
    height: '40px'
  panel:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    rounded: '{rounded.lg}'
  day-cell:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    rounded: '0'
  badge:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink-secondary}'
    rounded: '{rounded.xs}'
    padding: '2px 8px'
  tab-active:
    backgroundColor: 'transparent'
    textColor: '{colors.ink}'
    padding: '0 2px'
---

# Design System: 日周报管理系统

## Overview

**Creative North Star: "The Record Grid"**

This is a working record book, not a dashboard. Every day of the month is a cell in a visible, hairline-ruled grid; writing a report means filling a cell, and a weekly or monthly report is that same grid gathered up. The visual system borrows the discipline of a construction drawing — a blueprint ground, one signal blue, mono numerals, a single diagonal slash — and spends it on exactly one thing: making a month of work legible at a glance.

The product is used in short, frequent visits (end of a workday, between meetings, on a phone), so familiarity beats expression everywhere a task happens. The identity lives in the frame: the wordmark, the ruled calendar, the mono date numerals, the slash that appears only where a cell is actionable.

**Key Characteristics:**

- Blueprint ground (`#f4f6f9`) with white panels; hairline rules (`#e6ebf2`) do the dividing, not shadows.
- One accent — signal blue `#0057ff` — for current selection, primary generative action, and the "today" ring.
- Condensed display type for titles and periods; IBM Plex Sans for body; IBM Plex Mono for dates, counts, versions, and tokens.
- Zero-radius calendar cells inside a rounded panel: the grid is the container, cells are ruled, not carded.
- A diagonal slash marks actionability; it never appears as decoration on static content.
- Light and dark are the same vocabulary, re-pointed token by token.

## Colors

The palette is restrained by design: two neutrals, one signal, three semantic states. Colour does a job or it does not appear.

- **Blueprint** (`#f4f6f9`) — the page ground. Everything that is not a working surface.
- **Surface / Paper Inset / Paper Sunk** (`#ffffff`, `#fafbfd`, `#f0f3f8`) — three tonal steps for panels, quiet fills, and pressed/selected states. Depth comes from these steps, not from shadows.
- **Rule Hair / Mid / Bold** (`#e6ebf2`, `#d3dae6`, `#aeb9c8`) — the grid. Hair draws the calendar and panel divisions; mid draws control borders; bold draws the heaviest dividers and the empty-cell plus.
- **Ink** (`#111111`) and its two steps (`#565d68`, `#6e757f`) — text, and the fill of the primary button.
- **Signal** (`#0057ff`) — current navigation item, focus ring, the today ring, weekly band, primary generative action. Its tint (`#eef3ff`) marks selected or "today" rows.
- **Cyan** (`#0fa3b9`) — the monthly band only.
- **Danger / Warning / Success** (`#c4271d`, `#9a5b00`, `#0b7a3e`) — destructive actions, overdue deadlines, urgent deadlines (within 3 days), and completed state.

**The Signal Rule.** Signal blue means "this is where you are" or "this is the action that produces something". It never fills a surface larger than a button, a row tint, or a 2px line.

**The Band Rule.** One colour per cadence, used identically in the calendar chip, the summary rail, and the legend: ink for a written daily record, signal for weekly, cyan for monthly.

## Typography

Two families, three voices, one mono.

- **Display — Saira Semi Condensed 600** (with Noto Sans SC for CJK). Page titles, panel titles, the period label, auth headlines. Tracking `-0.032em`. This is the only place where type is allowed to be a little condensed and a little loud.
- **Body — IBM Plex Sans 400/500/600** (with Noto Sans SC). Everything else: prose, labels, controls. Tracking `-0.006em`, line-height 1.6 for UI and 1.75 for report prose.
- **Data — IBM Plex Mono 400/500.** Dates, day numbers, counts, version strings, API tokens, deadline dates. Tabular numerals always.

Scale: 11 / 12 / 13 / 14 / 16 / 18 / 22 / 28 / 34 px. Steps between adjacent sizes are small (1.14–1.25) because a working screen has many type roles and exaggerated contrast becomes noise.

**The Measure Rule.** Report prose is capped at 72ch and centred nowhere — always left-aligned under its panel title. Chinese body text never exceeds ~38 characters per line on a phone.

## Layout

- Page frame: `max-width: 1100px`, centred, `24px` side padding on desktop and `16px` on phones. Settings-shaped pages use `736px` so the header rule and the column share one measure.
- The calendar is a 7-column CSS grid with `1px` gaps over the rule colour, wrapped in a `10px`-radius panel. Cells are square-cornered and share their rules; nothing inside a cell is carded.
- Breakpoint is structural, not fluid: `≥768px` uses a sticky top bar with inline navigation and the month grid; `<768px` uses a fixed top bar, a fixed bottom tab bar, and the week list. Type sizes never change with viewport width.
- Spacing rhythm: 4/8/12/16/20/24/32/40/48/64. More space above a section than below its heading.
- Touch targets are at least 40px; icon-only controls are 40×40 (32×32 in the compact size).

## Elevation & Depth

Depth is tonal first and shadowed second.

- Panels: `1px` hairline border, no shadow at rest.
- Overlays (modals): `--shadow-lg`, a 24–56px offset blur plus a tight contact shadow. Never a zero-offset coloured halo.
- Popovers/toasts: `--shadow-md`.
- A control that gains a border on hover does not also gain a shadow; a control that gains a shadow does not gain a border.

## Shapes

- Radius: `2px` (badges, chips), `4px` (buttons, inputs, small controls), `6px` (icon tiles), `10px` (panels, modals, calendar shell). Pills only for the scrollbar thumb.
- Borders are always `1px`. The only 2px line in the product is the focus ring and the "today" inset ring.
- The diagonal slash is the single decorative stroke: 18×2px at −45°, on the wordmark, and revealed inside an actionable calendar cell on hover/focus.

## Components

- **Button.** Variants: primary (ink block, the one loud control per view), accent (signal, the generative action), outline (default), ghost (secondary in toolbars and footers), danger (destructive, icon or text), danger-solid (confirming a destructive dialog). Sizes: 40px, 32px (compact), 44px (auth). Every button carries default/hover/focus/active/disabled/loading; loading swaps the label for one spinner without changing width.
- **Field.** Label + control + hint, with an optional tag beside the label. Inputs are 40px tall, 16px text (iOS zoom), `4px` radius, `1px` mid border; focus adds a 1px signal border and a 1px inset ring — no second outline. Errors replace the hint and set `aria-invalid`.
- **Panel.** The only container. Header (title + icon + actions) / body / footer (right-aligned actions on a sunk ground). Nested panels are never allowed.
- **Modal.** 560px (420px compact), sheet-style from the bottom below 768px. Focus is trapped, Esc closes, focus returns to the trigger, background scroll is locked, and the close button is a 40px icon button.
- **Calendar cell.** Rest: white, mono day number, record chip, up to 4 lines of preview. Hover/focus: inset ground, plus in the empty area, slash at the corner. Today: 2px signal inset ring and a signal day number. Outside month: inset ground, muted text.
- **Week row.** Date column (mono + weekday + optional "今天" badge) / body / actions. Today tints the row and colours the date column; it never uses a coloured side stripe.
- **Task row.** Toggle / text + deadline / actions. Overdue shows a danger deadline with "· 已逾期"; urgent (≤3 days) shows a warning deadline with "· 即将到期". Rows are divided by hairlines inside one panel, never separate cards.
- **Tabs & segmented control.** Desktop: underlined text tabs with a mono count, 2px signal underline. Phone: segmented control with a raised white selected segment. Both use `aria-pressed`, not incomplete tab roles.
- **Badge.** Mono, 11px, `2px` radius; neutral by default, `badge-accent` for roles and "today", `badge-danger` for destructive state.
- **Empty state.** Drawn icon tile, one line naming what is missing, one line naming the next step, and the action itself.
- **Toast.** Top centre, below the navigation, surface with mid border and `--shadow-md`, 3s.

## Do's and Don'ts

- Do keep one accent. If a new element needs emphasis, use weight, size, or a tonal step first.
- Do keep dates, counts, versions, and identifiers in mono with tabular numerals.
- Do let hairline rules do the dividing; reach for a shadow only for something that floats above the page.
- Do write the action on the button ("保存", "删除用户") and name the consequence in the confirm dialog.
- Do keep the same component vocabulary across screens: if save looks different in two places, one of them is wrong.
- Don't put a coloured side stripe on rows, cards, or alerts.
- Don't nest panels, or wrap a list row in its own card.
- Don't use `window.confirm` — destructive actions go through the confirm dialog.
- Don't add decorative motion; the only authored transitions are state changes, the modal entrance, and the slash reveal.
- Don't introduce a second radius scale, a second accent hue, or a new font family for a new screen.
