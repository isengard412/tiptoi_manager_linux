# tiptoi Manager for Linux

An unofficial, open-source manager for the Ravensburger **tiptoi** audio pen on
Linux, aiming for the same look and everyday features as the official
"tiptoi Manager" (which only exists for Windows and macOS).

> This project is not affiliated with or endorsed by Ravensburger.
> "tiptoi" is a trademark of Ravensburger AG.

## Basis

The functional core (pen detection/mounting, `.gme` downloads with resume,
install/verify, trash handling, catalog access, AppImage packaging) is based on
the excellent [tiptoi-linux](https://github.com/tokajer/tiptoi-linux) project
by tokajer, licensed under GPL-3.0. This repository is a continuation/fork of
that work, adding a UI that mirrors the official tiptoi Manager:

- left navigation rail (download / catalog / pen / help screens)
- product tile grid with cover art and filters
- pen status header with free space, firmware version and serial number
- firmware update flow
- DE/EN/FR/IT/NL wording aligned with the original application

## Status

Working today (see `docs/PLAN.md` for the roadmap):

- ✅ tiptoi-Manager look-alike shell: orange header with pen card, left nav
  rail, product tile grid, footer with version/serial/firmware
- ✅ catalog browse + search, category filter chips (Bücher, Spiele, Puzzle, …)
- ✅ real product covers fetched at runtime from Ravensburger's public CDN
- ✅ install / verify / delete / outdated with one-click "update all"
- ✅ firmware update flow (download, byte-sum checksum, staged as `update.upd`)
- ✅ CLI (`tiptoi …`, incl. `tiptoi pen firmware [--install]`)
- ✅ German UI aligned with the original wording; language choice in Optionen
  (System/DE/EN/FR/IT/NL — FR/IT/NL reuse the original application's wording
  wherever our strings match)
- ✅ self-update check against GitHub releases
- ⏳ audio sample previews, product detail overlay, account/WLAN-pen features
  (explicitly out of scope: login and purchases)

## Installation (from source)

Requires Python 3.11 or newer.

```
git clone https://github.com/isengard412/tiptoi_manager_linux.git
cd tiptoi_manager_linux
pip install '.[gui]'       # installs PySide6 for the desktop app
tiptoi-gui                 # desktop app
tiptoi --help              # command line
```

## Development

Run the tests:

```
pip install PySide6-Essentials
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -t .
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
