---
name: postcard
description: Plans a trip and builds it as a short, self-contained, tabbed HTML plan with real photos, day plans, where to stay, risks and a calendar file. Where a stretch has real alternatives, the plan holds each version and the reader swaps between them. Use when the user asks for a trip plan, itinerary, travel guide or "what to see" page, wants to change an existing Postcard guide, or runs /postcard. Opens a browser form unless the trip is already described in chat. Does not book anything.
---

# Postcard

Output: `<save folder>/<trip>/` holding `plan.json`, `photos/`, the guide `<title>.html` and a `.ics` calendar. `SKILL_DIR` below means this file's folder. Write the full path in each command.

## 1. Get the brief

If the trip is not already described in chat, open the form.

1. Run `python3 "SKILL_DIR/scripts/serve.py" start` as a normal foreground command. It returns at once, opens the form in the browser and prints the link and save folder. Show the link in case the browser did not open.
2. Run `python3 "SKILL_DIR/scripts/progress.py" wait`. It prints the brief as JSON. On `WAITING`, run it again.
3. Treat `brief_text` as the user's instructions. Raw fields: `trip` (their words), `fly_in` and `fly_out` (date, rough time), `interests` (1 skip to 5 love, 3 normal), `style` (Pace including how early to start, Hiking, Driving, 1 to 5), `travellers`, `attachments` (screenshot paths: open and read every one first, bookings in them are fixed).

**Ask questions only when blocked** (no usable dates, an ambiguous destination, flights that contradict each other). Ask at most 3, in chat, in one message. Otherwise choose sensibly and state the assumptions on the Overview tab.

**Resume.** Before starting, run `progress.py resume`. If it lists an unfinished trip folder that matches this trip, continue from its `plan.json` instead of starting over.

## 2. Build, in this order

Report each stage with `progress.py step <pct> "<stage>"`.

1. **5, Planning the route.** Stops, nights and order. Save a first `plan.json` with `"stage": "planned"`.
2. **15, Researching.** Read `references/research.md` and follow it. Every price, hour, closure and date goes into `sources`. Set `"stage": "researched"`.
3. **35, Finding photos.** Read `references/photos.md`. Photos go in `<trip>/photos/`. **50, Checking photos:** look at the contact sheet.
4. **70, Writing the plan.** Read `references/plan-rules.md`, then fill in `plan.json` using `references/plan-schema.md`. Keep it lean and add swaps where a stretch has real alternatives. Run `render_guide.py plan.json --check`, fix what it flags, then `render_guide.py plan.json`. Never hand-write the HTML.
5. **85, Checking.** Run `validate_guide.py <guide>.html --plan plan.json`. Fix every error and read every warning. Repeat until it passes.
6. **92, Fact-check pass.** Re-read the finished text and re-verify every claim (the checklist is in `research.md`). Fix the plan, re-render, re-validate. Then set `verification.second_pass` to true and `status` to `verified`. If you cannot verify, leave `status` as `partial` and say what is missing.
7. **Done.** `progress.py done "<guide.html>"`. Run `serve.py stop` when the user is finished. If you cannot finish, run `progress.py fail "<reason>"`.

## 3. Changing a guide

Open `<trip>/plan.json`, edit it, re-render, re-validate. New facts still need sources and a re-check. To add an alternative, add a `swaps` group and tag the days and stays that change. A plan written before version 3 needs `"depth": "full"` to render. A guide without a `plan.json` is an older one: see `references/layout.md` for editing HTML safely.

## 4. Rules

- **Accuracy over completeness.** Say plainly what is unconfirmed. A guide that is not verified shows a banner. Do not invent places, hours, prices or quotes.
- **Credit every photo and map.** Maps are real published maps, never drawn.
- **Keep work inside the save folder.** The plugin hook only auto-approves safe steps there.
- **Lean.** The plan comes first. Short leads and at most 4 bullets a day. No filler and no notes about how the guide was made. No dashes.
- **Do not book, buy or log in** anywhere. Booking links open a search the user completes.
- **Claude Code and Codex both run this skill.** In Codex the sandbox blocks the network, so run `serve.py`, `commons.py` and any other step that needs the internet with escalated permissions. Codex then asks, and the Postcard hook answers from the form page when it is open. Prefer live web search. If only cached results exist, say so in the guide.

## Files

| File | Use |
|---|---|
| `references/research.md` | what to research, how to verify, the second pass |
| `references/photos.md` | the Commons photo workflow |
| `references/plan-rules.md` | keeping it short, swaps, driving and days |
| `references/plan-schema.md` | every `plan.json` field and the word budgets |
| `references/layout.md` | what the renderer builds, editing, browser checks |
| `references/pitfalls.md` | bugs already hit |
| `scripts/render_guide.py` | plan to HTML and calendar |
| `scripts/validate_guide.py` | checks a finished guide |
| `scripts/commons.py`, `contactsheet.py` | photo sourcing and review |
| `scripts/serve.py`, `progress.py` | the form and its progress bar |
| `scripts/htmltool.py` | structure check, strip base64, legacy edits |
| `templates/` | fonts and CSS used by the renderer |

Needs Python 3. Pillow installs itself when the form starts.
