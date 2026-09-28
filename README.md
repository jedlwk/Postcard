# Postcard

Describe a trip in plain words. Postcard turns it into a travel guide you can open anywhere: a tab for every stop, day-by-day plans, where to stay, hikes, festivals, weather, risks and logistics, with real photos and maps. It runs on your own Claude Code; no API key needed.

## Get started

**1. Install.** In Claude Code, run:

```
/plugin marketplace add jedlwk/Postcard
/plugin install postcard@postcard
```

**2. Make a guide.** Open Claude Code in the folder where you want your trips saved and type `/postcard`. A page opens in your browser: describe the trip, press **Generate guide**, and download it from the same page when it's done.

That's it. You need Python 3; anything else installs itself.

## Good to know

- **It takes a while.** Usually 30 to 90 minutes, because it actually researches the trip. The page shows a live estimate. Keep Claude Code open until it finishes.
- **Approvals.** With **Auto-approve safe steps** on, routine steps (web searches, reading pages, saving into your trips folder) run without asking. Anything else, or everything if you switch it off, appears as an Allow / Deny pop-up on the page. No answer in 5 minutes counts as Deny.
- **Private by default.** The page runs only on your computer (127.0.0.1) with a one-time link. Postcard does nothing outside a build or outside your trips folder.
- **The guide is one file.** Photos and fonts are built in, so it works offline and can be emailed or shared as is.
- **Prefer chat?** Just tell Claude Code about the trip and it builds the guide without the form.
