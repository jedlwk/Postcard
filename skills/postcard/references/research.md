# Research

## Contents
- What to research
- How to verify
- Festivals and dates
- Contingencies
- Weighting
- The second pass

## What to research

Do this before writing the plan.

- **Routing.** Real road and rail numbers per leg, the actual station or airport names (flag cities with two, like Venice Santa Lucia and Mestre), one-way rental fees and drop-off hours. Where a town sits on the route between two anchors, make it a same-day stopover, not a round trip.
- **Drive times.** Search every one. Remembered numbers run 30 to 50 percent too optimistic. A "2.5 to 3 hour" drive that was really 4 hours flipped a whole day's plan.
- **Weather.** Real climate normals for the travel month, from a named source. Add a "feels like" range (wind chill at 10°C or below, humidex above).
- **Places per stop.** Real, well reviewed places in Food, Markets, Nature, Culture, Nightlife and Festivals. Where a category is thin, say so.
- **Opening days and booking.** The weekly closing day per site, and whether booking is essential. Then check the day plan against it, for example a market planned on its closed day.
- **Stays.** Areas, not listings. Name a property only when it changes the day, like the only lodge inside a park.
- **Rules and fees.** Entry permits, timed tickets, park fees, visa or eTA, with the date each was checked.

## How to verify

- **No price, hour, closure or entry rule without a source and a date.** Put each in the plan's `sources` list.
- **Check each restaurant is still open** and each attraction has not moved. Venues move (TeamLab Borderless reopened in a new district) and hours change.
- **Say plainly what you could not confirm.** Leave `verification.status` as `partial`. The guide then shows a "not fully fact-checked" banner.
- **Far-future calendars are not published.** Say hours and dates reflect the current pattern.

## Festivals and dates

- Date each event from the **latest one or two real editions**, then project to the trip year.
- Store the **rule, not the date**: "third weekend of July" survives a year change, "July 18 to 20" does not.
- Tag confidence: `high` (rule locked, or published), `likely`, `uncertain` or `risk` (could move).
- Check the event still exists. Celebrations get cancelled and replaced. Never drop an event just because it is unconfirmed.

## Contingencies

When the trip has a real worry (wildfire smoke, monsoon, strikes), give it a `risks` section on the Overview tab.

- **Weigh the most recent season most**, on the user's exact dates. Say what locals do about it.
- **Count against the real travel window.** A "7 of 9 years" headline was wrong because it counted events outside the dates.
- **Link live monitors** and name the fallback (a road, a day to swap, a stop that can be dropped).

## Weighting

Markets, food, nature, festivals and neighbourhoods first. Museums only if unmissable. Flag real must-sees. With a car, pack tighter and route creatively. If the user overrules a caution, remove it entirely instead of rewording it.

## The second pass

After the guide is built, re-read the finished text and re-verify every name, date, price and "open" or "closed" claim. This found about 15 errors in the Seattle guide. Check specifically:

1. Every restaurant and venue is still open.
2. Weekday and date pairs.
3. Fees, permits and ticket release dates.
4. Anything copied from a past year.
5. Numbers that changed when the itinerary changed (nights, days, drive legs).

Then set `verification.second_pass` to true and `status` to `verified`.
