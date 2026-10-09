"""GTK4 GUI for ohmychadwm-appearance: one page, five pickers, one Apply."""

import os
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

import log  # noqa: E402
import oma_chadwm  # noqa: E402
import oma_env  # noqa: E402
import oma_scan  # noqa: E402
import oma_screen  # noqa: E402
import oma_system  # noqa: E402
import oma_targets  # noqa: E402

_CURSOR_SIZES = [16, 24, 32, 48, 64]

_ROOT_HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oma_root.py")

# Standard freedesktop icon names — every complete icon theme ships these.
_PREVIEW_ICONS = [
    "folder",
    "user-home",
    "folder-download",
    "user-trash",
    "utilities-terminal",
    "internet-web-browser",
    "text-x-generic",
    "image-x-generic",
    "audio-x-generic",
    "preferences-system",
]

_FUNDING = [
    ("GitHub Sponsors", "https://github.com/sponsors/erikdubois", "best value — almost all goes to the project"),
    ("Ko-fi", "https://ko-fi.com/erikdubois", "buy a coffee — one-off tip"),
    ("Patreon", "https://www.patreon.com/kiroproject", "membership tiers + perks"),
    ("YouTube membership", "https://www.youtube.com/@ErikDubois/join", "join on YouTube"),
    ("PayPal", "https://www.paypal.me/erikdubois", "direct one-off"),
]


# ── Generic helpers ──────────────────────────────────────────────────────────


def _section(title):
    lbl = Gtk.Label(label=title, xalign=0)
    lbl.add_css_class("section-title")
    return lbl


def _muted(text=""):
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.add_css_class("plugin-desc")
    lbl.set_wrap(True)
    return lbl


def _row_label(text):
    lbl = Gtk.Label(label=text, xalign=0)
    lbl.set_valign(Gtk.Align.CENTER)
    return lbl


def _dropdown(names, current):
    """Return a searchable DropDown over names with current preselected (added when missing)."""
    names = list(names)
    if current and current not in names:
        names.insert(0, current)
    dd = Gtk.DropDown.new_from_strings(names)
    dd.set_enable_search(True)
    dd.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
    dd.set_hexpand(True)
    if current in names:
        dd.set_selected(names.index(current))
    return dd


def _selected(dd):
    item = dd.get_selected_item()
    return item.get_string() if item else ""


def _select(dd, value):
    model = dd.get_model()
    for i in range(model.get_n_items()):
        if model.get_item(i).get_string() == value:
            dd.set_selected(i)
            return


def _open_url(parent, url):
    Gtk.UriLauncher.new(url).launch(parent, None, None)


def _show_support_dialog(window):
    dlg = Gtk.Window(title="Support Kiro", transient_for=window, modal=True)
    dlg.set_default_size(440, -1)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("start", "end", "top", "bottom"):
        getattr(box, f"set_margin_{side}")(18)

    heading = Gtk.Label(xalign=0)
    heading.set_markup("<b>Support Kiro</b>")
    box.append(heading)

    intro = Gtk.Label(xalign=0)
    intro.add_css_class("info-label")
    intro.set_wrap(True)
    intro.set_max_width_chars(52)
    intro.set_label(
        "Kiro and its tools are built by one person, for the community — and kept free. "
        "If Ohmychadwm Appearance saves you time, a little support keeps the work going. "
        "Thank you for being here."
    )
    box.append(intro)

    for name, url, note in _FUNDING:
        btn = Gtk.Button()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        label = Gtk.Label(xalign=0)
        label.set_markup(f"<b>{name}</b>")
        sub = Gtk.Label(label=note, xalign=0)
        sub.add_css_class("info-label")
        content.append(label)
        content.append(sub)
        btn.set_child(content)
        btn.connect("clicked", lambda _w, u=url: _open_url(dlg, u))
        box.append(btn)

    close = Gtk.Button(label="Close")
    close.set_halign(Gtk.Align.END)
    close.connect("clicked", lambda _w: dlg.close())
    box.append(close)

    dlg.set_child(box)
    dlg.present()


def _system_cursor_lines(sel):
    """Return drift lines for the system default and SDDM cursor against sel."""
    sysc = oma_system.read()
    lines = []
    if sysc["default"] != sel.cursor:
        lines.append(f"System default cursor: cursor = {sysc['default'] or 'not set'}")
    if sysc["sddm"] != sel.cursor:
        lines.append(f"Login screen (SDDM): cursor = {sysc['sddm'] or 'not set'}")
    elif sysc["sddm_size"] not in (None, str(sel.cursor_size)):
        lines.append(f"Login screen (SDDM): cursor size = {sysc['sddm_size']}")
    return lines


# ── The page ─────────────────────────────────────────────────────────────────


class AppearancePage:
    """The single page: drift banner, GTK pickers, ohmychadwm bar pickers, Apply."""

    def __init__(self):
        self._gtk_themes = oma_scan.gtk_themes()
        self._preview_theme = Gtk.IconTheme()
        self._preview_theme.set_search_path(oma_scan.icon_theme_search_path())
        self._busy = False

        state = oma_targets.read_all()
        sel = oma_targets.current(state)
        self._forced = state.get(oma_targets.SYSTEM) is not None
        sysc = oma_system.read()
        self._sys_cursor_follows = sysc["default"] == sel.cursor and sysc["sddm"] in (None, sel.cursor)
        config = oma_chadwm.read_config()
        self._has_chadwm = bool(config)

        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.widget.append(self._build_banner())

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("start", "end", "top", "bottom"):
            getattr(body, f"set_margin_{side}")(18)
        body.append(self._build_gtk_section(sel))
        body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        body.append(self._build_bar_section(sel, config))
        if oma_screen.is_virtualbox():
            body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
            body.append(self._build_screen_section())
        scroller.set_child(body)
        self.widget.append(scroller)

        self.widget.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.widget.append(self._build_footer())

        self._update_theme_note()
        self._update_force_note()
        self._update_icon_preview()
        self._update_font_warning()
        self._refresh_drift(state)

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_banner(self):
        self._banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._banner.add_css_class("drift-banner")
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        title = Gtk.Label(label="Your settings are out of sync", xalign=0)
        title.add_css_class("drift-title")
        self._banner_detail = _muted()
        text.append(title)
        text.append(self._banner_detail)
        fix = Gtk.Button(label="Fix all")
        fix.set_valign(Gtk.Align.CENTER)
        fix.set_tooltip_text("Write the choices below to every settings file")
        fix.connect("clicked", self._on_apply)
        self._banner.append(text)
        self._banner.append(fix)
        return self._banner

    def _grid(self):
        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        grid.set_margin_top(6)
        return grid

    def _build_gtk_section(self, sel):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(_section("Applications"))
        box.append(_muted("Used by Thunar and every GTK 2, 3 and 4 application."))
        grid = self._grid()

        self._dd_theme = _dropdown(self._gtk_themes.keys(), sel.theme)
        self._dd_theme.connect("notify::selected", lambda *_: self._update_theme_note())
        self._theme_note = _muted()
        grid.attach(_row_label("Theme"), 0, 0, 1, 1)
        grid.attach(self._dd_theme, 1, 0, 2, 1)
        grid.attach(self._theme_note, 1, 1, 2, 1)
        self._chk_force = Gtk.CheckButton(label="Force this theme on every app (system-wide)")
        self._chk_force.set_tooltip_text(
            "Sets GTK_THEME in /etc/environment, as Kiro ships it. Needs your password; shows after re-login."
        )
        self._chk_force.set_active(self._forced)
        self._chk_force.connect("toggled", lambda *_: self._update_force_note())
        self._force_note = _muted()
        self._force_note.add_css_class("warning-text")
        force_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        force_box.append(self._chk_force)
        force_box.append(self._force_note)
        grid.attach(force_box, 1, 7, 2, 1)

        self._chk_sys_cursor = Gtk.CheckButton(
            label="Also use this cursor on the login screen and as the system default"
        )
        self._chk_sys_cursor.set_tooltip_text(
            "Sets /usr/share/icons/default and the SDDM CursorTheme / CursorSize. Needs your password."
        )
        self._chk_sys_cursor.set_active(self._sys_cursor_follows)
        self._chk_sys_cursor.connect("toggled", lambda *_: self._refresh_drift())
        grid.attach(self._chk_sys_cursor, 1, 8, 2, 1)

        self._dd_icons = _dropdown(oma_scan.icon_themes(), sel.icons)
        self._dd_icons.connect("notify::selected", lambda *_: self._update_icon_preview())
        self._icon_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._icon_strip.add_css_class("icon-strip")
        grid.attach(_row_label("Icons"), 0, 2, 1, 1)
        grid.attach(self._dd_icons, 1, 2, 2, 1)
        grid.attach(self._icon_strip, 1, 3, 2, 1)

        self._dd_cursor = _dropdown(oma_scan.cursor_themes(), sel.cursor)
        sizes = [str(s) for s in sorted(set(_CURSOR_SIZES) | {sel.cursor_size})]
        self._dd_size = Gtk.DropDown.new_from_strings(sizes)
        self._dd_size.set_selected(sizes.index(str(sel.cursor_size)))
        self._dd_size.set_tooltip_text("Cursor size in pixels")
        grid.attach(_row_label("Cursor"), 0, 4, 1, 1)
        grid.attach(self._dd_cursor, 1, 4, 1, 1)
        grid.attach(self._dd_size, 2, 4, 1, 1)

        self._font_btn = Gtk.FontDialogButton(dialog=Gtk.FontDialog(title="Choose a font"))
        self._font_btn.set_font_desc(Pango.FontDescription.from_string(sel.font))
        self._font_btn.set_hexpand(True)
        self._font_btn.connect("notify::font-desc", lambda *_: self._update_font_warning())
        grid.attach(_row_label("Font"), 0, 5, 1, 1)
        grid.attach(self._font_btn, 1, 5, 2, 1)

        self._chk_light = Gtk.CheckButton(label="Light")
        self._chk_dark = Gtk.CheckButton(label="Dark")
        self._chk_dark.set_group(self._chk_light)
        (self._chk_dark if sel.dark else self._chk_light).set_active(True)
        style = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        style.append(self._chk_light)
        style.append(self._chk_dark)
        style.set_tooltip_text("Preferred style for apps that follow it (GTK 4 / libadwaita)")
        grid.attach(_row_label("Style"), 0, 6, 1, 1)
        grid.attach(style, 1, 6, 2, 1)

        box.append(grid)
        return box

    def _build_bar_section(self, sel, config):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(_section("Ohmychadwm bar"))
        if not self._has_chadwm:
            box.append(_muted("~/.config/ohmychadwm is not set up for this user — log into Ohmychadwm once first."))
            self._dd_bar = None
            self._chk_bar_font = None
            self._font_warning = _muted()
            return box
        box.append(_muted(
            "Colours and font of the top bar. Changing these recompiles Ohmychadwm (asks your password once)."
        ))
        grid = self._grid()

        self._bar_theme_now = oma_chadwm.active_theme(config) or ""
        self._dd_bar = _dropdown(oma_chadwm.themes(), self._bar_theme_now)
        grid.attach(_row_label("Bar theme"), 0, 0, 1, 1)
        grid.attach(self._dd_bar, 1, 0, 1, 1)

        self._bar_font_now = oma_chadwm.bar_font(config)
        self._chk_bar_font = Gtk.CheckButton(label="Also use the font above for the bar")
        self._chk_bar_font.set_active(self._bar_font_now is not None)
        self._chk_bar_font.connect("toggled", lambda *_: self._update_font_warning())
        grid.attach(self._chk_bar_font, 1, 1, 1, 1)
        self._font_warning = _muted()
        self._font_warning.add_css_class("warning-text")
        grid.attach(self._font_warning, 1, 2, 1, 1)

        box.append(grid)
        return box

    def _build_screen_section(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(_section("Screen (VirtualBox)"))
        box.append(_muted(
            "Resize the VirtualBox window to the size you want, then save it. Ohmychadwm uses this resolution "
            f"from the next login on ({oma_screen.layout_path().replace(os.path.expanduser('~'), '~', 1)}, "
            "arandr format)."
        ))
        btn = Gtk.Button(label="Save current resolution")
        btn.set_halign(Gtk.Align.START)
        btn.set_margin_top(6)
        btn.connect("clicked", self._on_save_screen)
        box.append(btn)
        return box

    def _build_footer(self):
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for side in ("start", "end", "top", "bottom"):
            getattr(footer, f"set_margin_{side}")(12)
        self._status = Gtk.Label(label="", xalign=0)
        self._status.add_css_class("status-line")
        self._status.set_hexpand(True)
        self._status.set_wrap(True)
        self._btn_restart = Gtk.Button(label="Restart Ohmychadwm now")
        self._btn_restart.set_visible(False)
        self._btn_restart.connect("clicked", self._on_restart)
        reset = Gtk.Button(label="Reset to Kiro default")
        reset.connect("clicked", self._on_reset)
        self._btn_apply = Gtk.Button(label="Apply")
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.connect("clicked", self._on_apply)
        footer.append(self._status)
        footer.append(self._btn_restart)
        footer.append(reset)
        footer.append(self._btn_apply)
        return footer

    # ── Live feedback ────────────────────────────────────────────────────────

    def _update_theme_note(self):
        name = _selected(self._dd_theme)
        if self._gtk_themes.get(name, True):
            self._theme_note.set_label("")
            self._theme_note.set_visible(False)
        else:
            self._theme_note.set_label("This theme has no GTK 4 version — GTK 4 apps will look like Adwaita.")
            self._theme_note.set_visible(True)

    def _update_force_note(self):
        if self._chk_force.get_active():
            self._force_note.set_visible(False)
        else:
            self._force_note.set_label(
                "Without it, apps follow your personal settings — some GTK 4 / libadwaita apps may keep their own look."
            )
            self._force_note.set_visible(True)

    def _update_icon_preview(self):
        while (child := self._icon_strip.get_first_child()) is not None:
            self._icon_strip.remove(child)
        self._preview_theme.set_theme_name(_selected(self._dd_icons))
        for name in _PREVIEW_ICONS:
            paintable = self._preview_theme.lookup_icon(name, None, 32, 1, Gtk.TextDirection.NONE, 0)
            image = Gtk.Image.new_from_paintable(paintable)
            image.set_pixel_size(32)
            image.set_tooltip_text(name)
            self._icon_strip.append(image)

    def _font_desc(self):
        desc = self._font_btn.get_font_desc()
        return desc if desc is not None else Pango.FontDescription.from_string("Sans 11")

    def _update_font_warning(self):
        if self._chk_bar_font is None:
            return
        family = self._font_desc().get_family() or ""
        if self._chk_bar_font.get_active() and not oma_scan.is_nerd_font(family):
            self._font_warning.set_label(
                f"“{family}” is not a Nerd Font — the bar's tag icons may show as empty boxes."
            )
            self._font_warning.set_visible(True)
        else:
            self._font_warning.set_visible(False)

    def _system_cursor_drift(self, sel):
        return _system_cursor_lines(sel) if self._chk_sys_cursor.get_active() else []

    def _refresh_drift(self, state=None):
        sel = self._selection()
        lines = oma_targets.drift(sel, state) + self._system_cursor_drift(sel)
        self._banner_detail.set_label("\n".join(lines))
        self._banner.set_visible(bool(lines))

    def _set_status(self, text, error=False):
        self._status.set_label(text)
        if error:
            self._status.add_css_class("status-error")
        else:
            self._status.remove_css_class("status-error")

    # ── Reading the widgets ──────────────────────────────────────────────────

    def _selection(self):
        desc = self._font_desc()
        return oma_targets.Selection(
            theme=_selected(self._dd_theme),
            icons=_selected(self._dd_icons),
            cursor=_selected(self._dd_cursor),
            cursor_size=int(_selected(self._dd_size)),
            font=oma_targets.norm_font(desc.to_string()),
            dark=self._chk_dark.get_active(),
        )

    def _bar_plan(self):
        """Return (theme, font-or-None) wanted for the bar, or None when ohmychadwm isn't set up."""
        if self._dd_bar is None:
            return None
        font = None
        if self._chk_bar_font.get_active():
            desc = self._font_desc()
            font = (desc.get_family() or "Sans", max(1, round(desc.get_size() / Pango.SCALE)))
        return _selected(self._dd_bar), font

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_reset(self, _widget):
        sel = oma_targets.kiro_default()
        _select(self._dd_theme, sel.theme)
        _select(self._dd_icons, sel.icons)
        _select(self._dd_cursor, sel.cursor)
        _select(self._dd_size, str(sel.cursor_size))
        self._font_btn.set_font_desc(Pango.FontDescription.from_string(sel.font))
        (self._chk_dark if sel.dark else self._chk_light).set_active(True)
        self._chk_force.set_active(True)  # the Kiro ISO ships GTK_THEME forced
        self._chk_sys_cursor.set_active(True)  # ...and the same cursor for SDDM and /usr/share/icons/default
        if self._dd_bar is not None:
            _select(self._dd_bar, oma_chadwm.default_theme())
            self._chk_bar_font.set_active(False)
        self._set_status("Kiro defaults loaded for everything — press Apply to use them.")

    def _on_apply(self, _widget):
        if self._busy:
            return
        self._busy = True
        self._btn_apply.set_sensitive(False)
        self._btn_restart.set_visible(False)
        self._set_status("Applying…")
        sel = self._selection()
        bar = self._bar_plan()
        force = self._chk_force.get_active()
        sys_cursor = self._chk_sys_cursor.get_active()
        threading.Thread(target=self._apply_worker, args=(sel, bar, force, sys_cursor), daemon=True).start()

    def _apply_worker(self, sel, bar, force, sys_cursor):
        log.log_section("Apply")
        results = oma_targets.apply(sel)
        for label, ok, msg in results:
            (log.log_success if ok else log.log_error)(f"{label}: {msg}")

        root_args, notes, bar_result = [], [], None
        env_theme, env_active = oma_env.read()
        if force and (not env_active or env_theme != sel.theme):
            root_args += ["--gtk-theme", sel.theme]
            notes.append("theme")
        elif not force and env_active:
            root_args.append("--release-gtk-theme")
            notes.append("theme")
        if sys_cursor and _system_cursor_lines(sel):
            root_args += ["--system-cursor", sel.cursor, "--cursor-size", str(sel.cursor_size)]

        compiled = False
        if bar is not None:
            theme, font = bar
            try:
                text = oma_chadwm.read_config()
                new = oma_chadwm.set_theme(text, theme)
                new = oma_chadwm.set_bar_font(new, *font) if font else oma_chadwm.clear_bar_font(new)
                if new != text:
                    GLib.idle_add(self._set_status, "Recompiling Ohmychadwm…")
                    oma_chadwm.write_config(new)
                    compiled, msg = oma_chadwm.compile_wm()
                    if compiled:
                        root_args += ["--install", oma_chadwm.BUILT_BINARY]
                    else:
                        bar_result = (False, msg)
            except (OSError, ValueError) as e:
                # must still reach _apply_finished, or Apply stays greyed out until restart
                bar_result = (False, f"Ohmychadwm bar: {e}")

        if root_args:
            # one pkexec for everything that needs root, so at most one password prompt
            GLib.idle_add(self._set_status, "Waiting for your password…")
            proc = subprocess.run(["pkexec", sys.executable, _ROOT_HELPER, *root_args], capture_output=True, text=True)
            if proc.returncode != 0:
                err = (proc.stdout + proc.stderr).strip()
                results.append(("System changes", False, "cancelled or failed" + (f": {err}" if err else "")))
                notes.clear()
            elif compiled:
                bar_result = (True, "Ohmychadwm rebuilt and installed")
        if compiled:
            oma_chadwm.clean()
        if bar_result is not None:
            (log.log_success if bar_result[0] else log.log_error)(bar_result[1])
        GLib.idle_add(self._apply_finished, results, bar_result, notes)

    def _apply_finished(self, results, bar_result, notes):
        self._busy = False
        self._btn_apply.set_sensitive(True)
        failed = [f"{label}: {msg}" for label, ok, msg in results if not ok]
        if bar_result is not None and not bar_result[0]:
            failed.append(bar_result[1])
        if failed:
            self._set_status("Some settings could not be written:\n" + "\n".join(failed), error=True)
        elif bar_result is not None:
            relogin = " Log out and back in for the system-wide theme." if notes else ""
            if oma_chadwm.can_restart():
                self._set_status("Applied. Restart Ohmychadwm to see the new bar." + relogin)
                self._btn_restart.set_visible(True)
            else:
                self._set_status("Applied. Press Super+Shift+R to see the new bar." + relogin)
        elif notes:
            self._set_status("Applied. Log out and back in to see the new theme everywhere.")
        else:
            self._set_status("Applied. Apps you open from now on use the new look.")
        self._refresh_drift()
        return False

    def _on_save_screen(self, _widget):
        def worker():
            ok, msg = oma_screen.save_current()
            (log.log_success if ok else log.log_error)(f"Screen layout: {msg}")
            GLib.idle_add(self._set_status, msg, not ok)

        threading.Thread(target=worker, daemon=True).start()

    def _on_restart(self, _widget):
        self._btn_restart.set_visible(False)
        oma_chadwm.restart()


def build(window):
    """Populate the window with the header row and the appearance page."""
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    header.set_margin_start(12)
    header.set_margin_end(12)
    header.set_margin_top(10)
    header.set_margin_bottom(8)
    title = Gtk.Label(label="Ohmychadwm Appearance", xalign=0)
    title.set_name("title")
    title.set_hexpand(True)
    btn_support = Gtk.Button(label="♥ Support")
    btn_support.set_tooltip_text("Support Kiro's development")
    btn_support.add_css_class("support-button")
    btn_support.connect("clicked", lambda _w: _show_support_dialog(window))
    btn_quit = Gtk.Button(label="Quit")
    btn_quit.connect("clicked", lambda _w: window.close())
    header.append(title)
    header.append(btn_support)
    header.append(btn_quit)
    root.append(header)
    root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    root.append(AppearancePage().widget)
    window.set_child(root)
