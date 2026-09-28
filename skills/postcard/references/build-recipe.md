# Meta-Prompt: Build a Trip Infographic Like This One, In One Shot

Paste this whole document as the instructions for a fresh Claude session (with
Bash, Read, Write, Edit and a browser preview available), together with the
specific trip details — destinations, dates, flights, traveller preferences.

It is written from lessons learned across many rounds of building real
multi-city trip documents. Follow it and you should not need the iterative
back-and-forth those sessions went through.

If you're running this as the `postcard` skill, `scripts/` already
implements the mechanical parts (§3, §12) and `references/pitfalls.md` holds the
bug catalogue. If you're reading this standalone, everything is described in
enough detail to reimplement.

---

## 0. Before you start

Confirm, and ask only where a different reading would change the work:

- Exact stops and their order
- Trip dates (or at least month and year) and total duration
- Home city, and carrier/routing for the bookend flights
- Whether there's a rental car on any leg — this changes routing flexibility
- Any preference overrides; the defaults below assume none stated

## 1. Output format

A single self-contained HTML file. Fonts and photos embedded as base64 data
URIs, no external requests, no JavaScript anywhere — every interactive element
(tabs, carousels, badges) is pure CSS.

This is a hard requirement, not polish: Claude Artifacts run under a strict CSP
that blocks external font, image and script loads. A document that depends on a
CDN renders naked.

## 2. Research phase — before writing any HTML

**Logistics and routing.** Confirm flight routes and durations if the user names
carriers. Per inter-city leg: real road and motorway numbers, real station names
(flag cities with more than one — Venice's Santa Lucia vs. Mestre is a classic
trap), realistic drive times, rental pickup and drop-off logistics including
one-way fees, and the actual economics of advance train booking. On frequent
high-speed corridors, booking early is about *price*, not availability — say so
rather than implying a scarcity that isn't real.

Verify drive times against real sources. A quoted 2.5–3h Seattle→Winthrop turned
out to be ~4h, which flipped a "depart in the afternoon" recommendation into
"depart by midday." When a number feeds into same-day planning advice, check it.

**Apply the drive-through stopover pattern.** If a town sits directly on the
route between two anchors, route it as a same-day stopover — arrive, explore a
few hours, continue by evening — rather than a round-trip day trip from one end.
Look for this more than once if the route allows.

**Weather.** Real climate normals per stop for the actual travel month, from
Climate-Data.org or similar. Don't estimate from general knowledge.

**Festivals, events, public holidays.** For anything without a fixed date rule,
look up the **most recent one or two actual editions** to establish the real
pattern, then extrapolate. Don't write "sometime in July" — commit to a range and
label your confidence.

Derive the rule, not the date. "Third weekend of July" survives a year change;
"July 18–20" does not. Real examples: Seafair Torchlight is the Saturday eight
days before the first Sunday of August. Vancouver Pride is tied to the BC Day
long weekend, *not* the commonly assumed last Sunday of July.

Check whether an event is annual or biennial, and whether it still exists —
Vancouver's Celebration of Light was cancelled outright for funding reasons, and
Victoria's Symphony Splash was replaced by a flexible series. Both would have
been silently wrong if carried forward from an old year.

**Attractions by category, per stop.** Genuine well-reviewed places, not invented
ones: Food & Drink, Markets & Shopping, Nature & Views, History & Culture,
Nightlife & Vibes. Aim for 8–12+ per category where the destination supports it,
mixing famous names with strong local picks. Where a category is genuinely thin,
say so rather than padding — honesty about coverage beats the appearance of
completeness.

**Opening days and booking requirements.** Verify the weekly closing day per site
(don't assume "closed Monday"), and whether booking is essential, recommended or
unnecessary. Then **cross-check the day-by-day plan against it** — this catches
real scheduling bugs, like a market scheduled on a day it's closed.

**A few verified fun facts** per stop, each checked against a real source.

Flag throughout that far-future calendars aren't published yet: hours, closures
and festival dates reflect the current pattern, not a confirmed calendar.

## 3. Photo sourcing

Wikimedia Commons. Public domain or CC-licensed, free to embed.

**Categories beat search.** Resolve a category name first
(`list=search&srnamespace=14`), then list its members
(`generator=categorymembers`). Full-text search crosses continents without
warning — see `pitfalls.md` for the roll of shame.

**Filter for season using capture metadata — but only where season is visible.**
Request `iiprop=extmetadata` and read `DateTimeOriginal`; prefer files shot in the
target months. Also filter to `width >= 1100` and a landscape aspect (reject
anything wider than 3:1 — those are page banners and scanned scrolls).

Scope the month filter to **nature, gardens and foliage**. A cathedral facade
looks identical in April and October, so constraining city subjects to the travel
month just shrinks the candidate pool until the ranking is forced onto whatever
survives. On an October Italy document that produced an engraving for San Miniato,
a 19th-century albumen print for the Colosseum, a mosaic lunette for the Florence
Duomo and a porcelain dinner service for another. Dropping the month constraint
for Milan/Venice/Florence/Rome — while keeping it for the Dolomites, where larch
colour and snow are the whole point — fixed most of them in one pass.

**Also exclude non-photographic material explicitly.** Commons categories are full
of plans, engravings, lithographs, postcards, paintings, models, maps and
inscriptions, and they are often the largest files in the category, so they win on
size. Keep a standing avoid-list.

**Always drill to a sub-category — this is the highest-leverage move in photo
sourcing.** A broad category holds whatever a handful of prolific uploaders
happened to shoot, which skews heavily toward close-ups and details. Ranking a
broad category by resolution and season produced, in a real test: a *cat* as the
top Fushimi Inari result, no deer anywhere in Nara Park, and four interior
ceiling shots for Tōdai-ji.

Don't guess the narrower name — **enumerate it**. `subcats` lists what actually
exists, and Commons' sub-category names are semantic:

| Broad category gives you | Sub-category gives you |
|---|---|
| `Arashiyama` → maple close-ups, a cosmos field | `Sagano Bamboo forest` → the swept path through the grove |
| `Kiyomizu-dera` → roof brackets, a dragon painting | `Main Hall, Kiyomizu-dera` → the stage above red maples |
| `Nara Park` → seed pods, bare trees | `Deer in Nara` → sika deer |
| `Fushimi Inari-taisha` → power lines, a cat | `Fushimi-Inari-taisha sembon-torii` → the vermilion tunnel |
| `Tōdai-ji` → ceilings and pillars | `Buildings of Tōdai-ji` → the Great Buddha Hall |

**Middle levels are often pure containers holding no files at all.** `Buildings
of Tōdai-ji` and `Gates of Todaiji` both return zero files directly — they only
hold further sub-categories. A plain listing looks like a dead end. Use `--deep 2`
to pool the leaves; that turned "0 usable" into 262 with the Daibutsuden
exteriors on top.

**Rank by subject within the category.** Score candidates against title,
description **and the file's own categories** (`--prefer daibutsuden,hall
--avoid interior,ceiling`). Per-file categories are what rescue bare filenames:
`- panoramio - ESU.jpg` carries no description but sits in "Towers in Japan", and
`Fox0290.jpg` sits in "Inari fox statues". Strip licence and upload bookkeeping
categories first or they pollute the match.

Keyword scoring nudges; it doesn't decide. Two of the corrected picks above only
came right after seeing them on a contact sheet.

**Then audit visually anyway.** Build a labelled contact-sheet montage —
thumbnails in a grid with index, place and capture month drawn on each — and
look at it. This is the step that catches what metadata can't: a "wildflower
meadow" with snow and no flowers, an autumn-red garden, six near-identical
frames of one sunset, or a category that turns out to be about skiing.

**Use the 900px `iiurlwidth` thumbnail as the source.** It's already larger than
the final crop. Downloading multi-megabyte originals wastes time and bandwidth.

**Two hosts, two User-Agents.** The API needs a descriptive bot UA with contact
info; the file host at `upload.wikimedia.org` needs a real browser UA and 403s
the bot one. Download **serially** with ~1.3s between requests — parallel
fetching trips 429 quickly.

**Credit every photo.** Most files are CC BY / BY-SA and attribution is a licence
condition. Carry photographer and licence in the caption.

## 4. Fonts

Embed as `@font-face` with base64 `woff2`. A system that works well for this
content:

- **Display serif** — Fraunces (warm, editorial, variable weight)
- **Body sans** — Archivo
- **Utility mono** — IBM Plex Mono, for dates, data, tags and badges

Fetch via the Google Fonts CSS API with a real browser UA, take the `.woff2`
URLs, download, base64-encode, embed. Variable fonts often return the same file
for every requested weight — dedupe URLs before downloading.

## 5. Design system

- **Warm paper palette**, not stark white: `--paper: #f2efe6`,
  `--paper-raised: #fbf9f2`, ink `#211f19` / `#58554a` / `#8a8677`
- **One accent colour per chapter**, used for that chapter's headings, badges and
  dots
- **A separate category-colour system** for the reference tabs, constant across
  every stop: Food=amber, Markets=green, Nature=teal, Culture=blue,
  Nightlife=purple, Festivals=rose
- **A confidence-tag system** for dates: `FIXED` / `LIKELY` / `UNCERTAIN`, three
  distinct visual treatments
- **Full dark mode** — define tokens in `:root`, then override in **both**
  `:root[data-theme="dark"]` and `@media (prefers-color-scheme: dark)`. Every
  time. Grep each new token; expect three hits.
- **Wide page** — ~1400px max-width with an even 1fr/1fr split, not a narrow
  centred column

## 6. Page structure

1. **Full-bleed hero** — the single most striking photo, dark gradient scrim,
   title, one-sentence pitch. Busy photos need both a deepened scrim *and* a
   `text-shadow` on the text, so legibility doesn't depend on the gradient being
   right for every photo.
2. **Route strip** — stop nodes (name, nights, dates, accent dot) joined by "via"
   segments labelled with transport mode. Bookend with the traveller's home city
   and flight details so it reads home→home. Horizontally scrollable.
3. **Weather section**, once and consolidated — one row per stop, a low→high bar
   in that stop's accent, with a comfort-band overlay.
4. **Any trip-wide risk section** the user is anxious about — wildfire smoke, monsoon,
   strikes. Put it near the top, not buried at the bottom, with live monitoring
   links and a concrete fallback plan. See §11.
5. **One chapter per stop** — see §7.
6. **Logistics section** — real routing detail for every non-flight leg.
7. **Footer** — the tag legend and an honest accuracy disclaimer.

## 7. Chapter anatomy

- Heading, date range with **day-of-week** ("Fri–Sun, Aug 27–29, 2027"), night count
- **Date ranges use checkout convention.** If the last night is Monday and you
  leave Tuesday morning, the range ends Tuesday. Ending it Monday reads as one
  night short and contradicts how every booking site writes it.
- **Badge row** — category badge, an intensity meter as filled dots, one or two
  vibe pills
- **Photo gallery** — see §8
- **Day-by-day list** — each day is a short bold one-line lead, *not* a
  paragraph, followed by concrete bullets. Small category badge next to each
  date. `MUST-SEE` tags inline on genuine highlights.
- **Hike cards** where the stop has named trails — see §9
- **Side column** — Worth Knowing, Fun Fact, Festivals list, Further Reading
- **Drive-through stopover box** if one applies — dashed border, real-size image,
  explicit "on the way, not a detour"
- **Explore-more tabs** — see §10

**Present genuinely open slots as options, don't pick.** Where the user hasn't
decided, write two or three labelled alternatives into the day itself
("Option: X" / "Option: Y") and note nothing needs deciding until the morning.
Reserve single commitments for things actually fixed.

## 8. Photo galleries

A horizontal scroll-snap carousel per chapter. Pure CSS.

**Count scales with nights**, roughly 4–5 per night: 2N→12, 3N→16, 4N→20. Cap at
two photos of any one place so there's real variety.

Each slide carries three caption lines: **what it is**, **where it is**, and the
**photo credit**.

```css
.gallery-scroll {
  display: flex; gap: 14px; overflow-x: auto; overflow-y: hidden;
  scroll-snap-type: x mandatory; scroll-behavior: smooth;
  padding: 2px 2px 14px; -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
}
.gallery-slide { flex: 0 0 auto; width: min(76vw, 430px); scroll-snap-align: center; }
.gallery-slide img { width: 100%; height: 290px; object-fit: cover;
                     border-radius: var(--radius); box-shadow: var(--shadow); }
@media (max-width: 640px) { .gallery-slide { width: 84vw; }
                            .gallery-slide img { height: 230px; } }
```

This snaps; it does not wrap around. True infinite looping needs JavaScript —
say so rather than implying it loops.

**Budget.** 820×547 at quality 58, progressive: 80 photos = ~5.6MB on disk,
~7.5MB base64, whole document ~8.6MB. Pre-cropping to roughly the display ratio
means `object-fit: cover` has almost nothing left to trim.

**Galleries and lightboxes don't coexist.** The old pattern stored every photo
twice — thumbnail plus full-size modal copy. At 80 photos that's unworkable.
Drop the lightboxes, size the carousel images properly, and tell the user
plainly that click-to-enlarge is gone.

## 9. Hike cards

For each named trail: name, a mono stats row (distance in **both** mi and km,
gain in **both** ft and m, difficulty, time, star rating), the **exact trailhead**
with drive time from the base town, the **parking pass required**, one line on why
it's worth doing, and a conditions caveat.

The caveats carry the real value: "get there before 9am or face the 1–2 hour gate
queue", "only ~16 parking spaces", "a July WTA report notes weak afternoon snow
bridges", "this is a 2–2.5 hour drive each way, a separate day not an add-on".

**Verify AllTrails URLs by loading them.** Do not construct them from trail
names. Note that AllTrails' GPS distances run slightly longer than park signage,
and say which you're quoting.

**Two badges per card**, both always present:

1. **Priority** — Must-do / Highly recommended / Good to have. Keep must-dos
   scarce; three out of fourteen keeps the tier meaningful. Also swap the card's
   left border colour on must-dos so they're scannable without reading.
2. **Payoff** — Ridge panorama, Rainforest icon, Waterfall, Alpine lake, Big
   climb, Crowd escape, Easy win, Fjord view, Glacier close-up.

```css
.hike-badges { display: flex; flex-wrap: wrap; gap: 6px; margin: 7px 0 2px; }
.hike-tier {
  font-family: 'IBM Plex Mono', monospace; font-size: 9.5px; letter-spacing: .09em;
  text-transform: uppercase; font-weight: 600; padding: 4px 9px; border-radius: 6px;
  white-space: nowrap;
}
.hike-tier.t-must { background: var(--must-see-tint); color: var(--must-see);
                    border: 1px solid var(--must-see); }
.hike-tier.t-high { background: var(--cat-nature-tint); color: var(--cat-nature);
                    border: 1px solid var(--cat-nature); }
.hike-tier.t-good { background: transparent; color: var(--ink-faint);
                    border: 1px solid var(--line); }
.hike-trait {
  font-family: 'IBM Plex Mono', monospace; font-size: 9.5px; letter-spacing: .06em;
  text-transform: uppercase; padding: 4px 9px; border-radius: 999px;
  border: 1px dashed var(--line); color: var(--ink-soft); white-space: nowrap;
}
.hike-card.is-must { border-left-color: var(--must-see); }
```

Add a one-line legend to the first hikes header explaining the two badge types.

## 10. Explore-more — sidebar tabs, pure CSS

Six tabs per stop: Food & Drink, Markets & Shopping (merged, they overlap),
Nature & Views, History & Culture, Nightlife & Vibes, and **Festivals, Events &
PH** — which consolidates all festival and holiday info for that stop in one
place. Don't also duplicate it in a sidebar card.

A day-trip location gets its **own** small dashed box above the tabs, not folded
into the six categories.

```html
<div class="explore-tabs">
  <input type="radio" name="milan-tabs" id="milan-t1" class="tab-radio" checked>
  <input type="radio" name="milan-tabs" id="milan-t2" class="tab-radio">
  <div class="tabs-layout">
    <div class="tabs-sidebar">
      <label for="milan-t1" class="tab-label">Food &amp; Drink<span class="count">(10)</span></label>
      <label for="milan-t2" class="tab-label">Markets &amp; Shopping<span class="count">(10)</span></label>
    </div>
    <div class="tabs-panel">
      <div class="tab-panel-content"><ul class="cat-list">...</ul></div>
      <div class="tab-panel-content"><ul class="cat-list">...</ul></div>
    </div>
  </div>
</div>
```

```css
.explore-tabs input.tab-radio { position: absolute; opacity: 0; width: 0; height: 0;
                                pointer-events: none; }
.tabs-layout { display: grid; grid-template-columns: 250px 1fr; gap: 18px;
               align-items: start; }
.tabs-sidebar { display: flex; flex-direction: column; gap: 4px;
                position: sticky; top: 24px; }
.explore-tabs .tab-panel-content { display: none; }

/* Positional, not ID-based - identical rules work for every stop's block */
.explore-tabs input:nth-of-type(1):checked ~ .tabs-layout .tab-panel-content:nth-of-type(1)
  { display: block; }
.explore-tabs input:nth-of-type(1):checked ~ .tabs-layout .tab-label:nth-of-type(1)
  { background: var(--cat-food-tint); color: var(--cat-food); }
/* repeat for 2..6 */

@media (max-width: 760px) {
  .tabs-layout { grid-template-columns: 1fr; }
  .tabs-sidebar { position: static; }   /* MUST come after the sticky rule */
}
```

Three traps live in that block — the scoped hide rule, real `id`/`for` pairs, and
the source-order sticky override. All three are in `pitfalls.md`.

**List item styling.** Give each `<li>` a bullet, a `border-bottom` divider and
padding, and keep the area label inline with an en-dash. Without dividers,
intra-item and inter-item spacing look identical and the list reads as mush.

**Recognition tags.** Michelin tags only where verified per-restaurant, and state
plainly when a city has no Michelin coverage at all rather than silently having
no tags. Community/Reddit picks only where a genuine citation exists — link the
subreddit honestly rather than inventing a thread URL.

## 11. Contingency sections

When the user has a specific anxiety about the trip — wildfire smoke, monsoon,
strikes, crowding — build it a real section near the top rather than a footnote.

What made one work:

- **Honest base rates.** The first framing ("7 of 9 years had disruption") was
  misleading because it counted events outside the actual travel window. Checked
  year-by-year against the real dates, the risk was far lower and concentrated at
  one specific stop. Recalculate against the actual window.
- **Live monitoring links** so the user can check for themselves.
- **A structural escape hatch.** The at-risk stop sat between two others, so it
  could be dropped entirely with no cascade — and the document says so.
- **Time-sensitive practicalities**, like insurance that must be bought within
  14–21 days of the first deposit.

## 12. Building and verifying on a multi-megabyte file

You cannot Read a 9MB HTML file into context. Work around it:

- Strip base64 payloads into a `lite.html` copy — a 9MB file becomes ~350KB and
  is greppable and readable.
- Edit via Python scripts with `assert html.count(anchor) == 1` before every
  replacement, and write the file only at the end so a failed assertion corrupts
  nothing.
- Walk depth to find a block's closing tag. Never regex for it.
- Keep image base64 out of the model's own output entirely: write HTML with
  `{{PLACEHOLDER}}` tokens, substitute via a script that reads the files directly.

## 13. Content weighting

Unless told otherwise, weight markets, neighbourhood vibes, cultural events and
nature slightly above formal history and museums — but never drop genuine
must-sees, just flag them. With a rental car, lean toward a denser, more creative
itinerary rather than the most conservative pacing.

**When the user overrides a caution, drop it entirely.** A well-sourced warning
about driving straight off a long-haul flight was answered with "do not worry
about the drive, I drove in US before." The right response is to remove it from
the document, switch the recommendation, and keep only the neutral logistics.
Re-raising a declined concern in softer wording isn't diligence.

## 14. Final checklist

- [ ] No `{{PLACEHOLDER}}` tokens left
- [ ] Stack-based nesting validation passes — count balance is **not** enough
- [ ] Every image loads: 0 broken by `naturalWidth`, 0 duplicates, 0 external srcs
- [ ] No `loading="lazy"` on inline base64
- [ ] Every photo visually verified — right subject, right season
- [ ] Every photo credited
- [ ] Every date claim tagged and traced to a real recent edition
- [ ] Day plans cross-checked against opening-hours research
- [ ] Every new CSS token present in light root **and** both dark blocks
- [ ] `<meta charset="UTF-8">` present
- [ ] `document.documentElement.scrollWidth <= window.innerWidth` — no overflow
- [ ] Tested at the mobile breakpoint, not just desktop
- [ ] Prose swept for stale numbers after any itinerary change

---

Treat this as a living recipe. Update it when new feedback changes the pattern.
