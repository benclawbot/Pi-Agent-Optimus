---
name: deep-research
description: End-to-end research-to-deliverable workflow. Use when the user asks for deep research, a literature review, a synthesis report, a market scan, or a beautifully designed PDF/web report. Handles parallel source gathering, knowledge-base indexing, structured synthesis, and unique-design document generation. Triggers: "deep research", "research and produce", "make a report", "synthesize these sources", "write me a brief on", "research X and give me a PDF", "literature review", "build a report on".
---

# Deep Research & Beautiful Deliverable

Turn a vague research ask into a polished, uniquely-designed PDF (or HTML/Markdown) deliverable. Battle-tested workflow with parallel source gathering, BM25-backed synthesis, and a hand-built design system that avoids AI-generic aesthetics.

---

## When to use this skill

- User asks for **deep research**, **synthesis**, or a **report** on any topic
- User wants a **PDF** (or HTML) deliverable, not just an in-chat answer
- User explicitly says "make it beautiful" / "uniquely designed" / "not generic"
- Multi-source synthesis: 5+ primary sources to combine

**Do NOT use this skill for:**
- Single-source lookups (use `ctx_fetch_and_index` directly)
- In-chat answers (just answer)
- Tasks where the user wants a quick summary, not a deliverable

---

## The four-phase pipeline

### Phase 1 — Scoping (1 turn, ask before diving)

Clarify:
1. **Audience** — executives? engineers? mixed?
2. **Length** — 1 page brief, 5-10 page report, 20+ page deep-dive?
3. **Lens** — what dimensions to cover (e.g., "efficiency, capabilities, coding" → three sections)
4. **Format** — PDF? HTML only? Markdown?
5. **Sources** — user-provided, public web, arXiv-only, internal docs?
6. **Visual style** — editorial, technical, corporate-clean, dark, playful?

**Default if unspecified:** PDF, 10-15 pages, editorial style, web + arXiv sources.

State the plan in 5-8 bullets before running any fetches. Get user confirmation only if the ask is genuinely ambiguous.

### Phase 2 — Parallel source gathering (always parallel, never serial)

**Always batch fetches in one `ctx_fetch_and_index` call** with `concurrency: 4-8`. Single serial fetches burn turns and miss opportunity to discover cross-references.

**Source-selection heuristics:**
- Start with **primary sources** (vendor blogs, official docs, arXiv papers). Avoid SEO listicles.
- For AI/tech topics: Anthropic, LangChain, OpenAI, Google, Aider, Cognition, Cursor, Martin Fowler.
- For research papers: arXiv abstracts first, then full text.
- For product/company research: official changelogs, GitHub repos, engineering blogs.
- Aim for **20-30 sources** for a 10-15 page synthesis. Diminishing returns past 30.

**Failure handling:** HTTP 404 / 500 on a URL is normal. Don't retry — just note it and substitute a related source. Don't surface 404s to the user; they don't care.

**After fetching:** Run ONE `ctx_batch_execute` or `ctx_search` sweep with 15-20 specific query terms to extract cross-cutting themes. This is where the real synthesis happens — you can't do synthesis in your head from raw fetches.

### Phase 3 — Synthesis (in your head, not in the artifact)

Write the synthesis **before** you touch HTML. The artifact is just the carrier.

**Structure for a 10-15 page report:**

1. **Cover** — title, deck, signature strip
2. **TOC / State-of-play stats** — sets scope
3. **3-5 thematic sections** — each 2-3 pages, with one infographic each
4. **Reference architecture / synthesis diagram** — one big SVG pulling it together
5. **Failure modes / unsolved problems** — honesty builds trust
6. **Actionable playbook** — "ship this in week X" beats "consider doing Y"
7. **Sources** — organized by theme, not by fetch order

**Synthesis rules:**
- Every claim should trace to a specific source. Cite inline or in a sources section.
- "X is the best" → replace with "X has been adopted by Y and Z; the trade-off is..."
- Use **direct quotes** from primary sources for maximum credibility. 2-3 per section.
- Anti-AI-generic: avoid "delve into", "navigate the landscape", "in today's world", "harness the power". Cut every adverb that doesn't earn its place.

### Phase 4 — Build the deliverable

**Default: HTML → PDF via Playwright + Chromium.** See "Build pipeline" below.

**Design system that doesn't look AI-generated:**

The single biggest tell of AI-generated reports is that they all look the same — white background, sans-serif, blue accents, generic icons, "By the Numbers" stat blocks with rounded corners. Avoid all of it.

**Editorial design language (default):**
- **Paper background:** `#f4efe6` (warm cream, not white)
- **Ink:** `#0e0f12` (near-black, not pure)
- **Accent:** `#d24a26` (vermillion, the spice)
- **Counterpoint:** `#1b6e6a` (deep teal)
- **Gold accent:** `#b8853a` (for tertiary)
- **Type:** Serif for display + body ("Iowan Old Style", "Hoefler Text", "Source Serif Pro", Georgia fallback), monospace for tech labels ("JetBrains Mono")
- **No rounded corners on stat blocks.** Sharp 1pt borders. Or 0.5pt dotted dividers.
- **No drop shadows.** No glassmorphism. No gradients on cards (gradients on cover only).
- **No emoji icons.** Use mono characters: ● ○ ⊘ ▸ ◆ ─ │ ╭ ╮ etc.
- **Two-column body** with 8mm column gap and 0.5pt column rule. Text fully justified with hyphens.
- **Drop-cap lead paragraphs** (first letter 42pt, vermillion, floats left).
- **Pull quotes** with 3pt vermillion left border, italic serif, column-span full width.
- **Callouts** with sharp 1pt borders, paper-2 background, vermillion mono label in caps.
- **Monospace metadata** in caps with letter-spacing for that "designed" feel.

**Infographic design — never just static boxes:**

Five recipes that always work:

1. **Radial taxonomy wheel** — center node + 4-6 satellites with spoke lines, each in different quadrant color. Use for taxonomies (4 ops of context, 4 types of X).
2. **Horizontal timeline** — baseline + event dots, alternating above/below with leader lines. Use for evolution (2023 → 2026).
3. **Data-flow diagram** — left = source (graph/code), arrow in middle, right = rendered output. Use for "how X becomes Y" (repo map → context).
4. **2x2 matrix** — axes labeled, quadrant fills at 6-16% opacity, points as colored circles with single-letter labels. Use for severity × likelihood.
5. **Stacked bar / phase progression** — 13 weekly segments at increasing height, color-graded by phase. Use for ramp plans, complexity curves.

**All five implemented as inline SVG.** Never use external image files. Use viewBox for resolution independence. Use `font-family` with monospace fallbacks. Always include caption + source line in monospace caps.

**Code blocks:** dark `#16181d` background, vermillion left border, full-column-span (not constrained to one column). Syntax-color spans: keyword (vermillion), string (sage green), comment (muted gray, italic).

**Tables:** monospace headers in caps on ink-black background, paper-cream text. Zebra rows. Numeric columns right-aligned or monospace-colored.

---

## Build pipeline (HTML → PDF)

### Step 1 — Scaffold the HTML

Single `<style>` block in `<head>`. No external CSS, no fonts (use system fallbacks). Use `@page { size: A4; margin: 12mm 11mm 14mm 11mm; }`. Define CSS variables for the palette.

**Layout rules that make it print well:**
- Use `column-count: 2` for body text. `column-rule: 0.5pt solid` for the divider.
- Use `break-inside: avoid` on h3, callouts, code blocks, pull quotes, table rows.
- Use `column-span: all` to break out of columns (for code blocks, tables, infographics, callouts).
- **Do NOT use `page-break-after: always` on every section.** This wastes the page and creates the "page-jump-per-section" feel the user hates. Only force page breaks for the cover and the most critical figures. Let content flow.
- Sections separated by 2.5pt top border + section number + title + kicker, then content flows.

### Step 2 — Write the body

For files >50KB, **split into chunks** and splice in Python. The `write` tool has a payload ceiling; multi-chunk is reliable. Pattern:
- `head.html` (CSS + body opener with `PLACEHOLDER_BODY`)
- `body-1.html` ... `body-N.html` (sections)
- Splice: `head.replace('PLACEHOLDER_BODY', ''.join(bodies))`

### Step 3 — Render with Playwright

```javascript
// render.cjs
const { chromium } = require('C:/Users/thoma/AppData/Roaming/npm/node_modules/playwright');
const { pathToFileURL } = require('url');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.resolve('final.html')).href, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.pdf({
    path: 'output.pdf',
    format: 'A4',
    printBackground: true,
    margin: { top: '0', right: '0', bottom: '0', left: '0' },
    preferCSSPageSize: true,
  });
  await browser.close();
})();
```

The global Playwright install path on this Windows box is:
`C:/Users/thoma/AppData/Roaming/npm/node_modules/playwright`

Use **CommonJS** (`.cjs`) — ESM import with absolute Windows paths throws `ERR_UNSUPPORTED_ESM_URL_SCHEME`.

### Step 4 — Verify visually

Render a few page screenshots to PNG and read them back to spot:
- Text overflow / column break in wrong place
- Diagram clipping
- White margins where content should fill
- Tables that span wrong number of columns

`python -c "import re; print(len(re.findall(rb'/Type\s*/Page[^s]', open('out.pdf','rb').read())))"` for page count.

---

## Gotchas hit (memorize these)

1. **ctx_batch_execute with `limit` parameter as string fails validation.** Pass nothing or as int. If you see "additional properties" errors, drop the field.
2. **ctx_fetch_and_index hits TLS errors on some doc sites** (saw it on `docs.swe-agent.com`). Substitute the source; don't retry. Use GitHub raw or the vendor blog instead.
3. **`<write>` and `bash heredoc` both fail silently on payloads >~25-30KB** without warning. Symptoms: file truncated mid-line, missing closing tags. Workaround: split content into multiple `write` calls and splice in Python.
4. **Playwright ESM import with absolute Windows path throws `ERR_UNSUPPORTED_ESM_URL_SCHEME`.** Use CommonJS (`.cjs`), not `.mjs`.
5. **PDF "no reader installed" on minimal Windows:** `assoc .pdf` / `ftype` may not exist in PowerShell. Fallback: `Start-Process 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'` with the PDF path — Edge has a built-in viewer.
6. **Pi's `todo` tool has no built-in side panel UI.** It manages files; visible progress requires either an extension that calls `ctx.ui.setWidget` (above editor) or `ctx.ui.custom` with `{ overlay: true }` for a real side panel. If the user wants progress visibility, build an extension — don't promise the todo tool will show it.
7. **First PDF draft always has "AI-generic" infographics** (boxes with labels, no data viz). Replace with the 5 recipe types above. Visual difference is dramatic.
8. **First PDF draft has forced page breaks between every section.** Wastes space, creates jarring jumps. Drop `page-break-after: always` everywhere except the cover.
9. **HTML screenshots from headless Chromium show sections on top of each other in a single viewport** — this is just the screenshot artifact, not the actual PDF. Verify by counting `/Type /Page` regex matches in the PDF bytes.
10. **For the `todo` tool, ALWAYS create todos at the START of a multi-step build, not after the user asks.** The user can see the file-based todo state, and a missing side panel during a long build is jarring.

---

## Quick-start template

When user says "deep research on X":

1. **Scope in one turn** — audience, length, lens, format. State 5-8 bullet plan.
2. **Fetch in parallel** — 1 `ctx_fetch_and_index` call with 4-8 URLs, concurrency 4. Aim for 20+ sources.
3. **Sweep with `ctx_batch_execute`** — 1 call with 15-20 query terms to extract themes.
4. **Write 3-5 sections in your head** — synthesis happens in the conversation, not in the artifact.
5. **Build HTML** — split into chunks > 30KB. Use editorial design system. 5 infographic types.
6. **Render → verify → fix → re-render.** 2-3 iterations is normal.
7. **Open the PDF** for the user. Always verify the file actually opened.

Total time: 5-10 minutes for a 10-15 page synthesis. 15-20 minutes for a 25+ page deep-dive.

---

## Anti-patterns to avoid

- ❌ Single sequential `ctx_fetch_and_index` calls. Always batch.
- ❌ White background, blue accent, rounded cards. Looks like every AI deck.
- ❌ One SVG "diagram" that's just labeled boxes connected by arrows.
- ❌ Forced page breaks between every section.
- ❌ "In conclusion" / "in today's rapidly evolving landscape" / "delve into".
- ❌ "Some experts say... others argue..." — pick a position, cite sources.
- ❌ Promising the `todo` tool will show a side panel — it won't without an extension.
- ❌ Running the full 30KB+ HTML through `<write>` in one shot. Split it.
- ❌ Closing the report with "I hope this helps!" or other LLM-assistant-isms.
- ✅ Hand-built SVG infographics with real data shapes.
- ✅ Editorial design (paper bg, serif body, mono metadata).
- ✅ Drop-cap leads, pull quotes, sharp-bordered callouts.
- ✅ Direct quotes from primary sources inline.
- ✅ "Ship this in week X" actionable playbook.
- ✅ Honest "what breaks" section — failure modes build trust.
- ✅ Code blocks span all columns, dark, syntax-colored.
- ✅ Continuous text flow with section dividers, not page breaks.
