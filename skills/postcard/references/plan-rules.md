# Plan rules

Rules from real itineraries. Apply them while you build `plan.json`.

## Contents
- Keep it short
- Swaps
- Driving and days
- Leave out

## Keep it short

The guide is a plan, not an essay. The renderer enforces the budgets in `references/plan-schema.md`.

- A day has one short lead and up to 4 short bullets. Times, places and numbers go first.
- One idea per bullet. If a bullet needs a second sentence, cut it or move it to `risks`.
- No hike cards, shortlists, extra place lists, reading or fun facts unless the user asked. Then set `"depth": "full"`.

## Swaps

A swap lets the reader move whole blocks of the trip. A block is a stop: Olympic, Rainier, Seattle. The reader picks an order at the top of the Overview, and the tabs, dates, route and day plans follow.

- **Swap blocks, not days.** Reorder two stops, or put one stop in place of another. Never swap single days or single meals. That is too fine to be useful.
- **Fixed ends stay fixed.** The arrival flight and the departure flight pin the first and last stop. Only the middle blocks move.
- **Write each order out.** Tag every day and stay in an order with `"swap": "order:<option>"`. Give each stop a `dates` (and `tab_sub`) for each order. Give each option a `tabs` list with the stop ids in that order.
- **The order the user asked for goes first.** It is the default and the one in the calendar file.
- **Say what each order costs in the note**, up to 14 words: a fixed-date event it misses, a booking that moves. The renderer adds the driving hours from `drive_h`.
- **Two orders is usually enough.** Three options at most.
- **Do not ask which order.** Build both when the user doubts the order, and let them choose.

## Driving and days

- **Put `drive_h` on every day with a drive.** Use routed times. Remembered times run short.
- **Flag any day over about 5 hours.** Move the night, not the sights. Sleep near the next early start.
- **Check the weekday against every opening time.** Many markets and museums close Monday and Tuesday. Move the stop, then record the source.
- **State the fixed windows.** Gate queues, crowd peaks, tides for coast stops, last entry, last ferry or toll.
- **Late arrival:** after about 20:00, tell the user to call the stay ahead. Put dinner before the check-in.
- **Spare time goes to one real stop**, not more driving.
- **A stretch between two anchors** gets a second look. List what is open on that weekday before you call it a pass-through.

## Leave out

- Anything closed, unreachable or unconfirmed for the dates goes in `risks`, not in a day.
- A stop the user chose that is weak (an outlet mall is shopping, not local) gets one honest word in the note, then it is planned.
- Facts from snippets or third-party pages keep `verification.status` at `partial`.
