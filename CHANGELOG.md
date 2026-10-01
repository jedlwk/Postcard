# Changelog

## 2.0.1

MIT license added.

## 2.0.0

Guides are now built from a plan file instead of hand-written HTML.

- **`plan.json` and `render_guide.py`.** The agent writes the content, a script builds the page. Same plan, same layout. Edits mean changing the plan and re-rendering.
- **`validate_guide.py`.** Checks tabs, links, images, weekday and date pairs, credits, file size, banned phrases and dashes, and that the guide is honest about its verification.
- **Sources and verification.** Every price, hour and date is listed with a check date. A guide that is not fully verified shows a banner.
- **Second pass.** The skill re-reads the finished guide and re-verifies every claim.
- **Calendar file and print layout.** A `.ics` file with the day plans, flights and booking deadlines, linked from the Overview tab. Printing shows every tab.
- **Resume.** A stopped build continues from its plan (`progress.py resume`).
- **Changing a guide** is part of the skill.
- **Clarifying questions** only when something blocks the plan.
- **Privacy.** Booking screenshots are deleted when a build finishes.
- **References rewritten.** The old recipe is split into short research, photos, layout, schema and pitfalls files.
- **Tests.** `python3 tests/run.py` covers the approval hook (Claude and Codex formats), the form server, the renderer and the checker. `tests/evals/` holds three sample trips and `tests/grade.py` grades a finished guide against them.
- **Codex** is marked beta until it has had a live run.

## 1.x

Form with sliders and examples, in-page approvals, Claude Code and Codex support, tabbed guides.
