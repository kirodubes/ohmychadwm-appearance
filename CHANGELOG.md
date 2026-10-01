# CHANGELOG

## 2026.10.01

### What Changed
- **Display name is now "Ohmychadwm"** in every user-visible string: window title (also shown in the
  ohmychadwm bar), page header, the bar section, buttons, status lines and the menu entry. Paths, binary and
  package name stay lowercase.
- **GTK_THEME support.** Kiro sets the GTK theme system-wide via `GTK_THEME` in `/etc/environment`, which beats
  every settings file, so the first version showed the wrong current theme and its theme changes had no visible
  effect. The app now reads `GTK_THEME` as the current theme. A **"Force this theme on every app
  (system-wide)"** checkbox (on by default, like Kiro ships) rewrites the line; unticking it comments the line out so
  apps follow the per-user settings, with a warning that some GTK 4 apps may keep their own look.
- **Reset to Kiro default now resets everything**: GTK pickers, `GTK_THEME` forced back on, the default bar theme,
  and no bar font override.
- **Login screen + system cursor.** New checkbox "Also use this cursor on the login screen and as the system
  default": writes `Inherits=` in `/usr/share/icons/default/index.theme` and `CursorTheme`/`CursorSize` under
  `[Theme]` in the SDDM config that sets it (Kiro: `/etc/sddm.conf.d/kde_settings.conf`). Both are needed, because
  SDDM ignores `icons/default` once its own `CursorTheme` is set. Shown in the drift banner, included in Reset, and
  part of the same single password prompt.
- Short launcher `oma`: a relative symlink `usr/bin/oma -> ohmychadwm-appearance`, the same convention as ATT's
  `att`.
- All root work (the `GTK_THEME` line + the bar binary install) goes through one pkexec helper, `oma_root.py`, so an
  Apply asks for the password at most once.
- Initial package: **ohmychadwm Appearance**, a GTK4 lxappearance-style tool for ohmychadwm. Why: one appearance
  choice lives in 7+ places (GTK 2/3/4, gsettings, xfconf, X cursor, the compiled bar), and lxappearance only writes
  GTK 2/3, so GTK 4 apps drifted away from Thunar (different icons, fonts, cursor sizes).
- One page with pickers for GTK theme, icons (with a live icon preview strip), cursor + size, font, light/dark
  style, and the ohmychadwm bar theme. There is an opt-in "also use this font for the bar" checkbox.
- An "out of sync" banner lists every settings file that disagrees, with **Fix all**.
- Apply writes every target. A bar change recompiles ohmychadwm with one pkexec prompt and offers a restart.
- "Reset to Kiro default" loads the look Kiro ships (read from `/etc/skel`).

### Technical Details
- Every chadwm theme header defines its own `THEME_FONT`, so the `#ifndef` fallback in `config.def.h` never fires.
  The bar font is instead overridden by a managed `#undef`/`#define` block placed after the last theme include. It
  is regenerated whole and removed when the checkbox is off.
- `make` only regenerates `config.h` when it is missing, so the rebuild is `make clean` → `make` (user) →
  `pkexec oma_root.py --install` (atomic copy to `/usr/local/bin/ohmychadwm`) → `make clean`, mirroring `chadwm/rebuild.sh`.
- Restart goes through `xdotool key super+shift+r`. dwm's `restart` exits 0 and the `run.sh` session loop relaunches
  it, and there is no signal hook to use instead.
- xfconf is written via `xfconf-query -n -t <type> -s`, never by editing `xsettings.xml`, because xfconfd caches
  and overwrites hand edits.
- Effective cursor size: `gtk-cursor-theme-size=0` means "X default", so the current size comes from
  `Xcursor.size`.
- File edits are line-based upserts (other keys and comments survive), with a one-time `.oma-bak` backup per file.
- Toolkit-free modules (`oma_targets`, `oma_chadwm`, `oma_scan`) are kept separate from the GTK layer so they can
  be tested against a scratch `HOME`.

### Files Modified
- `usr/share/ohmychadwm-appearance/oma_gui.py`, `ohmychadwm-appearance.py`, `usr/share/applications/ohmychadwm-appearance.desktop`, `README.md`, `CLAUDE.md` (display name)
- `usr/share/ohmychadwm-appearance/oma_env.py`, `oma_root.py`, `oma_system.py` (new)
- `usr/bin/ohmychadwm-appearance`, `usr/bin/oma` (symlink)
- `usr/share/applications/ohmychadwm-appearance.desktop`
- `usr/share/ohmychadwm-appearance/ohmychadwm-appearance.py`
- `usr/share/ohmychadwm-appearance/oma_gui.py`
- `usr/share/ohmychadwm-appearance/oma_targets.py`
- `usr/share/ohmychadwm-appearance/oma_chadwm.py`
- `usr/share/ohmychadwm-appearance/oma_scan.py`
- `usr/share/ohmychadwm-appearance/oma_config.py`
- `usr/share/ohmychadwm-appearance/log.py`
- `usr/share/ohmychadwm-appearance/oma.css`
- `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `LICENSE`, `ruff.toml`, `up.sh`, `setup.sh`, `.gitignore`, `kiro.jpg`
