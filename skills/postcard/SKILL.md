---
name: postcard
description: Build a photo-rich, self-contained, tabbed HTML trip guide (a tab per stop, day plans, where to stay, hikes, festivals, weather, risks, logistics). Use when the user asks for a trip document, itinerary, travel guide or "what to see" page, or to revise one. Starts with a browser form unless the brief is already in chat.
---

# Trip guide builder

Output is one HTML file: fonts and photos embedded as base64, no external
requests, no JavaScript (CSS-only tabs). Save it as `<trip>/<trip>.html`, one
folder per trip.

## 1. Get the brief

If the user hasn't described the trip in chat, use the form. `SKILL_DIR` below means this file's folder. Write it out as the full path in each command.

1. `python3 "$SKILL_DIR/scripts/serve.py" start --out "$PWD"` (Bash, `run_in_background: true`). Open the printed `TRIP_FORM_URL` (`open` / `xdg-open` / `start`).
2. `python3 "$SKILL_DIR/scripts/progress.py" wait` prints the brief as JSON. On `WAITING`, run it again.
3. While building, report progress with `progress.py step <pct> "<stage>"`: 5 Planning the route, 15 Researching, 35 Finding photos, 50 Checking photos, 75 Building, 90 Verifying. Finish with `progress.py done <file>`, or `progress.py fail "<reason>"` if you can't finish. Run `serve.py stop` when the user is finished.

The brief is open-ended: `trip` is the user's own description. Optional fields: `fly_in` / `fly_out` (date and rough time), `interests` (1 skip to 5 love, 3 is neutral), `pace` (1 very slow to 5 packed) and `attachments` (screenshot paths such as bookings; Read every one before planning). Decide stops, nights and order yourself, and state your assumptions in the Overview. Keep all work inside the output folder, because the plugin hook auto-approves only safe steps there.

## 2. Research (before any HTML)

- **Festivals and events:** date them from the latest real edition, then project to the trip year with a confidence tag (HIGH / LIKELY / AT RISK). Never omit an event because it's unconfirmed.
- **Weigh the most recent year most.** Include last season's smoke, closures and road outages on the user's exact dates, and what locals actually do about them.
- **Verify, don't recall.** Check every closure, drive time, opening hour, fee, and that each restaurant is still open. Say plainly when something can't be confirmed.
- **Content weighting:** markets, food, nature, festivals and neighbourhoods first. Skip museums unless unmissable, and flag real must-sees.
- **Stays:** name areas, not listings. Name a specific property only when it changes the day (e.g. the only lodge inside a park).

## 3. Photos

`commons.py find-cat` → `subcats` (not optional) → `list-cat` → `fetch`, then `contactsheet.py`, and look at the sheet. Match the season, credit every photo, never caption a substitute as the real place. Size: about 4–5 photos per night, at most 2 of one place. `imageprep.py` at 820×547, q58. Keep the whole file under about 12 MB.

Maps: use real published maps (NPS, Wikivoyage, Commons). Never draw your own.

## 4. Layout

Pattern and CSS: `references/tabbed-layout.css`. Design tokens and components: `references/build-recipe.md`.

- **Top:** hero, then the route strip, then a sticky tab bar: Overview · one tab per stop · layover (if any) · Logistics.
- **Overview tab:**
  - A day-by-day table; each row opens its stop.
  - A dated "book and check" list (what to book now, what to recheck and when).
  - A weather strip with a "feels like" band.
  - Risks, weighted to the latest season.
- **Each stop tab:**
  - Header and badges.
  - A gallery showing 2 full photos, with the map beside it (at most half width, click to enlarge via `:target`).
  - "Day by day" beside a side column: where to stay, know before you go, festivals, one fun fact.
  - Hikes.
  - A long reference list folded into `<details>`.
  - A "Next →" button.
- **Put information where it's used.** No "other notes" section: access rules go in their stop's tab, and car and flight details go in the day they happen.

## 5. Writing

Short, plain, specific. Few dashes, no filler ("genuinely", "single most", "it's worth noting"), and no notes about how the document was made. Put times, prices and names on the page. Cut repetition across tabs.

## 6. Verify before saying done

- `htmltool.py check` must PASS (nesting, placeholders, images).
- In a browser, check with JS (pages over ~8 MB screenshot blank; for visuals, use a copy with images swapped for placeholders): every tab opens, 0 broken images, no horizontal scroll at 375 px, and weekday labels match the dates.
- Final pass for hallucinations: re-check every name, date, price and "closed/open" claim added this session.
- Report anything unverified to the user.

## Scripts

`commons.py` sourcing · `contactsheet.py` visual audit · `imageprep.py` crop and encode · `htmltool.py check | lite | gallery` (import `find_close` / `replace_block` for block edits, never regex a closing tag) · `serve.py`, `progress.py` form and progress · `selftest.py`. Standard library only, except Pillow, which `serve.py start` installs if it's missing. Bugs already hit and their fixes: `references/pitfalls.md`.
