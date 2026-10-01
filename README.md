# Ohmychadwm Appearance

One window to set the look of an **ohmychadwm** desktop: GTK theme, icon theme, mouse cursor, font, light/dark
style, and the ohmychadwm bar theme. Think lxappearance, but it keeps *every* place those settings live in sync.

## Why

On a tiling-WM desktop one appearance choice is stored in many files. GTK 2, GTK 3 (Thunar), GTK 4 and libadwaita
apps, the XFCE settings channel and the X cursor each read their own. lxappearance only writes the GTK 2/3 side, so
over time GTK 4 apps end up with different icons, fonts or cursor sizes than Thunar does.

Ohmychadwm Appearance writes all of them at once. It shows an **"out of sync"** banner when they disagree, with a
one-click **Fix all**.

## The system-wide theme (GTK_THEME)

Kiro sets `GTK_THEME` in `/etc/environment`, and that beats every settings file: GTK 3 and GTK 4 apps use it
whatever the files below say. The app treats it as the current theme and gives you the choice:

- **Force this theme on every app (system-wide)**: the Kiro default. A theme change rewrites the `GTK_THEME` line
  (asks your password once) and shows after you log out and back in.
- **Untick it** to comment the line out. Apps then follow your personal settings; some GTK 4 / libadwaita apps may
  keep their own look. Ticking it again brings the line back.

## Reset to Kiro default

**Reset to Kiro default** loads the look Kiro ships for *everything* the app touches: theme, icons, cursor, font and
style (from `/etc/skel`), `GTK_THEME` forced again, the system/login-screen cursor following yours again, the default bar theme (from the skel `config.def.h`) and no bar
font override. Press **Apply** to write it.

## What it sets

| Setting | Written to |
|---|---|
| Theme (system-wide) | the `GTK_THEME` line in `/etc/environment`: forced or commented out (backup `/etc/environment.oma-bak`) |
| Theme, icons, cursor, cursor size, font | `~/.config/gtk-3.0/settings.ini`, `~/.config/gtk-4.0/settings.ini`, `~/.gtkrc-2.0`, gsettings `org.gnome.desktop.interface`, XFCE `xsettings` channel (via `xfconf-query`) |
| Cursor (optional, system-wide) | `/usr/share/icons/default/index.theme` and the SDDM login screen (`[Theme] CursorTheme` / `CursorSize`), via the checkbox "Also use this cursor on the login screen and as the system default" |
| Cursor | also `~/.icons/default/index.theme` and `~/.Xresources` (applied live with `xrdb` + `xsetroot`) |
| Light / dark style | gsettings `color-scheme` + GTK 4 `gtk-application-prefer-dark-theme` |
| Bar theme | the active `#include "themes/…"` line in `~/.config/ohmychadwm/chadwm/config.def.h` |
| Bar font (optional) | a small managed block in the same `config.def.h` that overrides the theme's font |

Before it changes a file for the first time, the app keeps a copy of the original next to it as `<file>.oma-bak`.

## The ohmychadwm bar

ohmychadwm's bar is compiled into the window manager. When you change the bar theme or bar font, the app recompiles
ohmychadwm as your user and installs it with **one** password prompt (pkexec), shared with a `GTK_THEME` change in the same Apply. With `xdotool` installed it can then
restart ohmychadwm for you; otherwise press **Super+Shift+R**.

The bar font is opt-in ("Also use the font above for the bar"). The bar's tag icons need a Nerd Font, and the app
warns you when the chosen font isn't one.

## Install

On Kiro, from the Kiro repositories:

```bash
sudo pacman -S ohmychadwm-appearance
```

Launch it from the menu (**Ohmychadwm Appearance**), or run `ohmychadwm-appearance` (short: `oma`). Add `--debug` for extra console
output.

## Requirements

`ohmychadwm`, `python-gobject`, `gtk4`, `xfconf`, `polkit` (plus a running polkit agent for the password prompt).
Optional: `xdotool` for the restart button, `xorg-xrdb` to apply the cursor live.

<!-- KIRO-FUNDING-FOOTER:START — managed by Kiro-HQ/cascade-readme-footer.sh -->
## Help fund Kiro

Everything I build here stays free and open — always. If Kiro or any of these
tools have ever saved you time or taught you something, a small monthly
contribution helps keep the work going. Donations target break-even, nothing
more — the core always stays free for everyone.

- GitHub Sponsors: https://github.com/sponsors/erikdubois
- Patreon: https://www.patreon.com/c/kiroproject
- YouTube memberships: https://www.youtube.com/@ErikDubois/join
- Ko-fi: https://ko-fi.com/erikdubois
- PayPal: https://www.paypal.me/erikdubois
<!-- KIRO-FUNDING-FOOTER:END -->

## License

GPL-3.0. See [LICENSE](LICENSE).
