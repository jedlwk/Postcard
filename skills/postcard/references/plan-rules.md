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

A swap is a part of the plan with two or three real versions. The reader picks one at the top of the Overview, and every tab follows.

- **Build both, then let the reader choose.** Do not ask. When the user doubts a stretch ("the Hoh is far", "is anything worth a stop on the way?"), turn it into a swap.
- **The version the user asked for goes first.** It is the default and the one in the calendar file.
- **Two groups at most, three options at most.** More is a menu, not a plan.
- **Tag everything that changes.** Each day and each stay in a version carries `"swap": "group:option"`. Days that do not change carry no tag.
- **Each option gets a name and a note** of up to 14 words saying what it gives. The renderer adds the driving hours from `drive_h`.
- **Tell the trade once**, in the note. Then plan the version properly. Do not argue against a pick.

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
