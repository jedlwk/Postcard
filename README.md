# Postcard

Describe a trip in your own words and Postcard turns it into a travel guide. Every stop gets its own tab with day plans, where to stay and what is on. Real photos and maps are built in. It runs on your own Claude Code, so there is no API key to set up.

## Get started

### 1. Install

In the Claude desktop app, go to **Settings** and open **Plugins**. Click **+ Add**.

![Settings, Plugins, then the + Add button](docs/1-plugins-add.png)

Choose **Add marketplace**.

![Add marketplace in the + Add menu](docs/2-add-marketplace.png)

Paste this in and confirm:

```
jedlwk/Postcard
```

Postcard now shows up in your plugin list. Search for "Postcard" if you don't see it, then click **Add** on it.

Postcard's page opens. It says "from postcard · 1 skill", with tabs for **Overview**, **Skills · 1** and **Hooks · 1**. Check that the switch at the top right is on (blue). That's it.

![Postcard's plugin page with the switch on](docs/3-postcard-on.png)

**Using Claude Code in a terminal instead?** Type these into Claude Code, one at a time. They will not work in your normal shell.

```
/plugin marketplace add jedlwk/Postcard
```

```
/plugin install postcard@postcard
```

### 2. Make a guide

Start a new Claude Code session and type `/postcard:postcard`. A page opens in your browser. Describe the trip, set the sliders if you like, and press **Generate guide**. When it is done, download the guide from the same page.

Guides are saved in the folder Claude Code is open in. With no folder open, they go to a `Postcard` folder in your home folder.

You need Python 3. Everything else installs itself.

## Good to know

**It takes a while.** Usually 15 to 30 minutes, because it actually researches the trip. The page shows a live estimate. Keep Claude Code open until it finishes.

**Approvals.** With **Auto-approve safe steps** on, routine steps run without asking. These are web searches, reading pages and saving into your trips folder. Anything else shows up as an Allow or Deny pop-up on the same page. So does everything, if you switch the toggle off. No answer in 5 minutes counts as Deny.

**It stays on your computer.** The page only runs on your own machine, with a one-time link. Postcard does nothing outside a build or outside your trips folder.

**The guide is one file.** Photos and fonts are built in. It works offline and you can email it as it is.

**Prefer chat?** Just tell Claude Code about the trip and it builds the guide without the form.

**Getting updates.** Go to **Settings**, then **Plugins**, open Postcard and click **Update**. Start a new session afterwards.
