# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Ohmychadwm Appearance is a standalone GTK4 Python app, lxappearance-style, for the **ohmychadwm** X11 desktop. It
sets the GTK theme, icons, cursor (+ size), font, light/dark style and the ohmychadwm **bar theme** / optional **bar
font**, and keeps every place those live in sync. It ships in `nemesis_repo`.

- **Language**: Python 3, GTK4 + PyGObject. Same look and layout conventions as fish-tweak-tool.
- **Entry point**: `usr/share/ohmychadwm-appearance/ohmychadwm-appearance.py`
- **Launcher**: `usr/bin/ohmychadwm-appearance` + short alias `usr/bin/oma` (relative symlink, same convention as ATT's `att`) · **Desktop entry**: `usr/share/applications/ohmychadwm-appearance.desktop`
- **Runs as the normal user.** All root work goes through ONE helper, `oma_root.py`, run once per Apply via
  `pkexec`: the `GTK_THEME` line in `/etc/environment` and installing the rebuilt binary. Never add other root
  escalation.
- **Design study** (offline, in Kiro-HQ): `STUDIES/OHMYCHADWM-APPEARANCE-STUDY.md`. It holds the options comparison
  and the reasons for this design.

## Architecture

```
usr/share/ohmychadwm-appearance/
├── ohmychadwm-appearance.py  # Gtk.Application + window, CSS, prefs window size
├── oma_gui.py                # the single page: drift banner, pickers, Apply (worker thread → GLib.idle_add)
├── oma_targets.py            # every settings target: read_all / current / drift / apply  (toolkit-free)
├── oma_chadwm.py             # config.def.h: theme include, managed font block, rebuild, restart (toolkit-free)
├── oma_scan.py               # discover GTK / icon / cursor themes (toolkit-free)
├── oma_env.py                # GTK_THEME line in /etc/environment: parse / force / release (pure, toolkit-free)
├── oma_system.py             # system cursor: /usr/share/icons/default + SDDM [Theme] CursorTheme/Size (pure)
├── oma_root.py               # the pkexec helper: --gtk-theme / --release-gtk-theme / --system-cursor / --install
├── oma_config.py             # app prefs (~/.config/ohmychadwm-appearance/prefs.json)
├── log.py                    # console logging (shared shape with the other Kiro tools)
└── oma.css
```

Module prefix `oma_` = **o**h**m**ychadwm **a**ppearance, mirroring fish-tweak-tool's `ftt_`.

## Write targets (read before touching oma_targets.py)

| Target | Fields |
|---|---|
| `/etc/environment` `GTK_THEME` (root, via `oma_root.py`) | theme. **Beats every file below** for GTK 3 and 4; read by pam_env, so changes show after re-login |
| `/usr/share/icons/default/index.theme` + SDDM conf (root, optional checkbox) | `Inherits=` cursor; SDDM `[Theme] CursorTheme`/`CursorSize` in the conf that already sets it (Kiro: `/etc/sddm.conf.d/kde_settings.conf`). SDDM ignores icons/default once CursorTheme is set, so write BOTH |
| `~/.config/gtk-3.0/settings.ini` | theme, icons, cursor, size, font. **Thunar reads this**: xfsettingsd is NOT running in ohmychadwm |
| `~/.config/gtk-4.0/settings.ini` | the same + `gtk-application-prefer-dark-theme` |
| `~/.gtkrc-2.0` | theme, icons, cursor, size, font (quoted strings) |
| gsettings `org.gnome.desktop.interface` | gtk-theme, icon-theme, cursor-theme, cursor-size, font-name, color-scheme |
| xfconf channel `xsettings` | /Net/ThemeName, /Net/IconThemeName, /Gtk/CursorThemeName, /Gtk/CursorThemeSize, /Gtk/FontName |
| `~/.icons/default/index.theme` | `Inherits=` cursor |
| `~/.Xresources` | `Xcursor.theme`, `Xcursor.size` → `xrdb -merge` + `xsetroot -cursor_name left_ptr` |

`current()` takes an active `GTK_THEME` first for the theme, then GTK 3 (what Thunar shows), then gsettings, then the Kiro default from `/etc/skel`. The cursor
size is the exception: GTK 3 `0` means "X default", so `Xcursor.size` wins.

## Gotchas — do not revert

- **Display name is capitalised: "Ohmychadwm".** Every user-visible string (window title, header, section
  titles, buttons, status lines, `.desktop` Name/Comment) says "Ohmychadwm". Paths, the binary, the package
  name, the app id and `--` CLI help stay lowercase `ohmychadwm`.
- **`GTK_THEME` is Kiro's real theme switch.** The ISO ships `GTK_THEME=Arc-Dawn-Dark` in `/etc/environment`, and
  ATT's themes page toggles that exact line. The "force" checkbox keeps it (rewrites it); unticking comments it out
  (`#GTK_THEME=…`, kept so it can be re-enabled, and ATT still recognises it). `oma_env.force` keeps the line's
  quoting style and rejects unsafe names. Never drop the line, and never set the theme only in `settings.ini` while
  the line is active, because nothing would change.
- `/usr/share/icons/default/index.theme` belongs to `default-cursors` but is a pacman **backup** file: edits survive
  upgrades (as `.pacnew`). Don't "protect" it some other way.
- **Reset to Kiro default covers everything**: GTK pickers from `/etc/skel`, force back on, system cursor checkbox on, the bar theme from the
  skel `config.def.h`, and the bar font block removed. Keep it complete when adding a setting.

- **xfconf: always use `xfconf-query`, never edit `xsettings.xml`.** xfconfd caches the channel and overwrites hand
  edits. `-n -t <type> -s` happily retypes an existing property (tested). The reset-then-create fallback is only a
  safety net.
- **Bar font = managed block after the last theme include.** Every `themes/*.h` defines its own `THEME_FONT`, so
  editing the `#ifndef THEME_FONT` fallback in config.def.h does nothing. The block uses `#undef` first (no
  redefinition warnings) and is regenerated whole. Only `THEME_FONT` and `THEME_FONTSIZE` are overridden; the theme's
  `THEME_FONTSTYLE` and the Nerd Font icon entries (`fonts[1]`, `menufonts`) stay as they are.
- **Rebuild must `make clean` first.** The Makefile only copies config.def.h → config.h when config.h is missing.
- **Restart = `xdotool key super+shift+r`.** dwm's `restart()` sets `running = 0` and exits 0; the `run.sh` loop
  relaunches it. There is no signal hook. Don't kill the process, because a non-zero exit after 5 s counts as a
  logout.
- Edit the **user** copy `~/.config/ohmychadwm/chadwm/config.def.h`, never `/etc/skel`.
- All file writes are line-based upserts (keys and comments the app doesn't own survive) with a one-time
  `<file>.oma-bak` backup. Keep it that way, and don't switch to configparser, which drops comments.
- ohmychadwm's own terminal scripts `scripts/apply-font-globally.sh` / `generate-chadwm-theme.sh` touch rofi/terminal
  fonts and theme generation. They are a different scope, so don't merge them in here.

## Code style

- ruff (`ruff.toml`, line length 120) must pass. One-line docstrings on public functions; none needed on `_private`
  ones.
- GTK callbacks name unused widget params `_widget`. Never `subprocess.call` from a callback; slow work runs in a
  daemon thread and reports back via `GLib.idle_add`.
- Test the toolkit-free modules with `HOME=$TMPDIR/fakehome python3 -c …` against copied config files, never against
  the real home.
