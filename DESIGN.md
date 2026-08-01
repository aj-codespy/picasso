---
name: Design Library
description: A personal exhibition gallery for UI screenshots — a light-theme editorial museum of interface works, headed for open source
colors:
  bg: "#FAF7F2"
  surface: "#FFFFFF"
  surface-soft: "#F3EFE7"
  ink: "#1C1712"
  ink-soft: "#5C5548"
  faint: "#756E62"
  line: "#E5DFD2"
  line-strong: "#D3CCBB"
  placard: "#131110"
  accent: "#F97316"
  accent-deep: "#C2500A"
typography:
  display:
    fontFamily: "Instrument Serif, Georgia, 'Times New Roman', serif"
    fontSize: "clamp(3rem, 7vw, 5.4rem)"
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Instrument Serif, Georgia, 'Times New Roman', serif"
    fontSize: "1.9rem"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Geist', 'Segoe UI', Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace"
    fontSize: "10.5px"
    fontWeight: 400
    letterSpacing: "0.16em"
    textTransform: "uppercase"
  plate:
    fontFamily: "Instrument Serif, Georgia, 'Times New Roman', serif"
    fontSize: "1.6rem"
    fontStyle: "italic"
    lineHeight: 1
rounded:
  card: "14px"
  pill: "999px"
  chip: "4px"
  placard: "2px"
spacing:
  hero-pad: "92px"
  section: "64px"
  grid-row: "72px"
  grid-col: "40px"
  page-pad: "40px"
  page-pad-sm: "22px"
components:
  placard:
    backgroundColor: "{colors.placard}"
    textColor: "{colors.bg}"
    padding: "14px 18px 15px"
    overlap: "-24px"
  index-chip-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
  index-chip-idle:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.pill}"
  search-input:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "0px"
---

# Design System: Design Library

## Overview

**Creative North Star: "The Light Gallery"**

The Design Library is an exhibition on light. Interface works hang on warm gallery-white walls, each carrying a catalog number and an ink placard, and the design vocabulary scrolls past in a slow marquee like the gallery's own announcement board. The interface stays a quiet attendant: hairlines level, works breathing, nothing crowded.

The system is type-led and editorial: a serif catalog voice (Instrument Serif) for the masthead, plate numbers, and descriptions; small-caps monospace for metadata and wayfinding; warm paper whites with ink placards that stand off the wall. Brand orange #F97316 is the exhibition marker — rare, deliberate, always meaningful. On light grounds it deepens to #C2500A so it stays legible.

**Key Characteristics:**
- Warm gallery-white walls (#FAF7F2) — never cold white, never gray
- Ink placards (#131110) overlapping card bottoms — the signature geometry, now inverted: dark label on light wall
- Catalog plate numbers ("No. 07") in italic serif as the recurring signature
- The vocabulary marquee — a slow-scrolling word-strip in the hero that announces the collection's taxonomy
- Hairline rules (1px) as the only structural lines
- Orange as the exhibition marker only: plate numbers, active selection, focus, idea dashes

## Colors

A two-material palette: the warm light wall and the ink label. All neutrals carry warmth.

### Primary
- **Exhibition Orange** (#F97316): the marker on dark surfaces — plate numbers on ink placards (6.72:1), the active index chip background (ink text 6.48:1), marquee dots, the hero bloom. On light backgrounds it deepens to **Accent Deep** (#C2500A, 4.42:1 on bg, 4.72:1 on white) for the italic "Library", view-toggle underline, focus ring, and idea dashes. Full-strength orange on light text fails contrast (2.62:1) and is never used for text on light.

### Neutral
- **Gallery Wall** (#FAF7F2): page background. Warm paper white, the light everything hangs on.
- **Card Ground** (#FFFFFF): work cards, chip surfaces, modal room.
- **Raised Ground** (#F3EFE7): image backdrops inside cards, component chips, code chips.
- **Ink** (#1C1712): primary text (16.6:1 on bg).
- **Ink Soft** (#5C5548): secondary text (6.9:1) — tagline, meta, fact values.
- **Faint** (#756E62): tertiary text (4.72:1) — count, labels, placeholders, footer.
- **Line** (#E5DFD2): hairlines, borders. **Line Strong** (#D3CCBB): hover borders, input rules.
- **Placard** (#131110): the ink label — dark on light, paper text at 16.1:1.

### Named Rules
**The One Material Rule.** The ink placard (#131110) exists only as physical labels — placards and the modal's dark accents. It never becomes a page surface; the wall stays light and the ink stays rare.

## Typography

**Display Font:** Instrument Serif (with Georgia fallback) — self-hosted woff2 at `src/fonts/`
**Body Font:** system sans stack (SF Pro / Inter / Geist / Segoe UI / Roboto)
**Label/Mono Font:** system monospace stack (SF Mono / Menlo)

**Character:** Instrument Serif gives the catalog its voice — used at large sizes and in italic for plate numbers and the marquee words. The sans carries UI quietly. The mono carries data (counts, metadata, colophon) in small caps.

### Hierarchy
- **Display** (400, clamp(3rem, 7vw, 5.4rem), 1.0, -0.03em): the masthead only.
- **Headline** (400, 1.9rem, 1.15, -0.02em): section heads, modal title (2rem).
- **Plate** (400 italic, 1.6rem–2.2rem, 1): catalog numbers.
- **Stat Number** (400 italic, 2.4rem): hero statistics.
- **Title** (600, 10.5px, 0.14em, uppercase): placard titles.
- **Body** (400, 13px–13.5px, 1.6): facts, ideas, meta.
- **Description** (Instrument Serif 400, 1.08rem, 1.6, max 46ch): the curator's note.
- **Label** (mono 400, 10.5px, 0.16em, uppercase): count, view toggle, fact keys, colophon.

### Named Rules
**The Serif-Does-Catalog Rule.** Instrument Serif is reserved for exhibition voice: masthead, plate numbers, marquee, descriptions, stats. UI chrome (chips, inputs, metadata) is never serif.

## Layout

A single centered content column, max width 1560px, 40px page padding (22px below 900px). Vertical rhythm: hero 92px top padding; marquee 64px below the stats; catalog bar 38px; index 58px; walls 64px; "How it works" 110px; footer 110px above its hairline.

The collection uses `repeat(auto-fill, minmax(340px, 1fr))` (min 280px on small screens) with gallery spacing: 72px rows, 40px columns. Cards are 16:10 with a 14px radius; the ink placard overlaps each card's bottom-left by 24px.

Responsive: below 900px the modal stacks to one column, image caps at 40vh, catalogue rows collapse, the how-grid stacks, and page padding drops to 22px.

## Elevation & Depth

Light theme depth: cards lift with a soft offset shadow (`0 1px 2px` + `0 8px 24px` warm-black at 5–6%), intensifying on hover (`0 34px 64px` at 18%) — the work opens toward you. The ink placard carries the system's deepest shadow (`0 16px 34px` at 30%) because a label physically stands off a wall; hover deepens it and lifts the placard 6px.

The hero has one atmospheric layer: a warm skylight gradient behind the masthead — cream-to-wall with a faint orange bloom (radial glows at 13–16% opacity). On top of the bloom sits a **fading pixel-dot grid**: a two-layer halftone field (20px cells, offset 10px, ink dots at 50% opacity) masked to melt away down the hero and animated with a 120s slow drift (`dot-drift`). Pure background, no content, no borders; the mask guarantees it is gone before the marquee.

## Shapes

Square and architectural: cards at 14px radius (the one soft corner in the system), component chips 4px, search and inputs square, modal room 16px. The only circles: the marquee dots (7px) and the tag pills (999px) and the close button (50%). The one recurring silhouette: the ink placard overlapping the card's bottom-left, carrying plate number, title, and metadata.

## Motion

Calm and authored, all `cubic-bezier(0.22, 1, 0.36, 1)`:
- **Rise** (0.8s): hero title, tagline, stats, marquee enter in sequence (0 / 0.08 / 0.14 / 0.2 / 0.28s delays).
- **Hang** (0.7s): works enter with staggered delays (i × 40ms, capped 360ms).
- **Marquee** (46s linear infinite): the vocabulary scrolls; pauses on hover. Two identical groups → seamless loop.
- **Dot drift** (120s linear infinite): the hero's pixel-dot field drifts one cell, seamlessly.
- **The work opens** (0.5s): a **focus / recede** choreography — the hovered work's `flex-grow` jumps to 2 while its row-mates drop to 0.6, so it **physically takes ~5/8 of its row** (just under two-thirds; height grows in proportion via the 16:10 frame) and the neighbors visibly cramp into the remaining space — nothing dims, opacity stays 1. The hovered work rises to `z-index` 5, its frame border strengthens, its shadow deepens (`0 34px 64px` at 18%), and its image zooms 1.05. The ink placard lifts 6px and its label **unfolds downward** (grid-template-rows `0fr → 1fr`) revealing the full curator note: description, all tags, and components, capped at 520px wide. The label grows below the work, never over it, so the enlarged piece stays fully visible.
- **Curtain** (0.35s): modal entrance.
- Hover: work grows to ~5/8 of its row (just under 2/3), image scales 1.05, placard lifts with deeper shadow and unfolds its label.
- `prefers-reduced-motion: reduce` collapses all animation and stops the marquee and dot drift.

## Components

### Hero
- **Style:** masthead "Design *Library*" — display serif, "Library" italic in Accent Deep; count right-aligned in mono small caps. Serif tagline with an italic strong. Three real stats (works / vocabularies / components) computed from the data. Below: the vocabulary marquee — 24 top tags by frequency, italic serif words separated by orange dots, scrolling 46s, duplicated for a seamless loop, `aria-hidden`.

### Search Field
- **Style:** underline-only input — transparent, no box, 1px bottom rule in Line Strong. Drawn SVG magnifier (1.5px stroke) left. Focus: underline → Accent Deep; placeholder Faint.

### View Toggle
- **Style:** text-only small-caps mono, "Wall" / "Catalogue". Idle Faint; active Ink with a 1px Accent Deep underline.

### Index Chip (vocabulary filter)
- **Idle:** white card, 1px Line border, Ink Soft text, pill, mono count in Faint, 1px shadow. Hover: border → Line Strong, lifts 1px.
- **Active:** Exhibition Orange background, Ink text (6.48:1), orange glow shadow `0 4px 14px` at 28%.

### Work (the hung piece)
- **Card:** white, 1px Line border, 14px radius, 16:10, image covers to top on Raised Ground, soft offset shadow. The wall is built as flex **rows** (3 works per row, 2 on tablet, via JS grouping that mirrors the CSS column math), so a hovered work can physically reflow its row.
- **Hover — "the work opens":** focus / recede — the hovered work's flex-grow goes 1 → 2 while its row-mates drop to 0.6: it grows to **~5/8 of the row width** (just under two-thirds; height proportional via 16:10), and the neighbors visibly cramp into the remaining space. Nothing dims (opacity 1 throughout). The hovered work rises to z-index 5, frame border → Line Strong with a deep shadow, image zooms 1.05. The placard lifts 6px and its label unfolds downward (grid-rows `0fr → 1fr`) showing the full curator note: description, all tags, components. No modal, no overlay — the work itself grows.
- **Placard:** Ink (#131110), 14px 18px padding, overlapping the card bottom by 24px, 2px radius, deep shadow. Plate number in italic serif orange (6.72:1), title in 10.5px tracked uppercase paper, meta line in #A9A294. On hover the label unfolds below (description in serif paper text, tag pills at #C9C2B2 on hairline borders, components in mono #A9A294) — pinned by `top: calc(100% - 73px)` so it grows downward, never over the work; capped at 520px wide so it stays label-like on a ~5/8-width card.
- **Hover:** border → Line Strong, work grows to ~5/8 of its row (just under 2/3), image scales 1.05, placard lifts with deeper shadow and unfolds its label.

### Viewing Room (modal)
- **Backdrop:** 55% warm-dark curtain over the page.
- **Room:** Card Ground, 1px Line border, 16px radius, two columns (1.35fr image / 1fr placard), stacking below 900px. Close: 40px circle, white, border Line, hover → Accent Deep.
- **Placard Full:** deep-orange italic plate number, serif headline, serif description (max 46ch), then ruled fact rows (Tags as pills, Components as 4px chips, Palette as text, Ideas as list with 2px deep-orange dashes). Hairline rules divide facts.

### How It Works
- **Style:** three columns (stack below 900px). Each step: top hairline, italic serif "No. N" in Accent Deep, sans heading, 13px description, inline `code` chips for commands. All claims factual — the actual pipeline (drop → `picasso update` → joins the wall).

### Colophon (footer)
- Left: "Design Library" in italic serif. Right: mono small caps, Faint — "An exhibition of interface works / Vision analysis by NVIDIA NIM · Self-hosted Instrument Serif · No dependencies". Above a 1px top hairline.

## Do's and Don'ts

### Do:
- **Do** keep the wall light and the ink rare — a dark label on a light wall is the system's signature.
- **Do** deepen orange to #C2500A on light grounds; reserve full #F97316 for dark surfaces (placard numbers, chip fills).
- **Do** use orange for one meaning at a time: selection, numbering, or focus.
- **Do** hang works with gallery spacing — 72px rows, 40px columns; let them breathe.
- **Do** set plate numbers in italic Instrument Serif with leading zeros ("No. 07").
- **Do** keep every small text ≥4.5:1 — Faint on wall (4.72:1), Ink Soft (6.9:1), Ink on orange (6.48:1), orange on placard (6.72:1).

### Don't:
- **Don't** use the ink placard color as a page background — it exists only as physical labels.
- **Don't** put full-strength orange text on light backgrounds (2.62:1 fails); use Accent Deep or put orange on dark.
- **Don't** add drop shadows to frames; only the placard and card lift off the wall.
- **Don't** use serif for UI chrome; the catalog voice stays with the catalog.
- **Don't** break the placard's card overlap — it is the gallery's signature geometry.
- **Don't** remove the marquee or make it fast; the slow vocabulary scroll is the hero's life.
