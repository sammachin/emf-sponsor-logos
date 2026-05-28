# EMF Camp Sponsor Logos — Tildagon App

A Tildagon badge app that displays EMF Camp sponsor logos as a fullscreen slideshow. Includes a build script that scrapes the sponsor logos from the EMF Camp website.

## Features

- Fullscreen logo display with crossfade transitions
- Auto-advances every 4 seconds, or use left/right buttons to navigate manually
- IMU mode (press OK to toggle) — rotate the badge to cycle through logos, display counter-rotates to keep logos upright
- Logos fetched from Palladium, Gold, and Badge sponsor tiers

## Setup

Install the Python dependencies for the fetch script:

```
pip install requests beautifulsoup4 cairosvg Pillow
```

You'll also need [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html) to deploy to the badge:

```
pipx install mpremote
```

## Usage

### Fetch logos

Downloads sponsor logos from https://www.emfcamp.org/sponsors, converts SVGs to PNG, resizes them for the badge display, and updates the `_SPONSORS` list in `app.py`:

```
./fetch_sponsor_logos.py
```

### Deploy to badge

Connect your Tildagon via USB and run:

```
./deploy.sh
```

Or specify a serial port:

```
./deploy.sh /dev/cu.usbmodem83101
```

The app will appear in the badge launcher under the **Badge** category as **Sponsor Logos**.

### Controls

| Button | Action |
|--------|--------|
| Left / Right | Previous / next logo |
| OK | Toggle IMU mode |
| Cancel | Exit to launcher |
