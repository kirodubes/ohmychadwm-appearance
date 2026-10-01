#!/usr/bin/env python3
"""ohmychadwm Appearance — GTK4 theme, icon, cursor and font switcher for ohmychadwm."""

# ── Force Python UTF-8 mode on a non-UTF-8 locale ─────────────────────────
# Never crash on a non-UTF-8 system locale (e.g. latin-1 fr_BE). Re-exec only
# when the locale's encoding is not UTF-8; the re-exec'd process is UTF-8, so
# the guard is loop-safe.
import codecs
import os
import sys

if codecs.lookup(sys.getfilesystemencoding()).name != "utf-8":
    os.environ["PYTHONUTF8"] = "1"
    os.execv(sys.executable, [sys.executable, "-X", "utf8", *sys.argv])

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import log  # noqa: E402
import oma_config  # noqa: E402
import oma_gui  # noqa: E402


class AppearanceApp(Gtk.Application):
    """GTK4 application entry point for ohmychadwm-appearance."""

    def __init__(self):
        super().__init__(application_id="com.kiro.ohmychadwm-appearance")
        self.connect("activate", self.on_activate)

    def on_activate(self, _app):
        """Create and show the main window."""
        window = Main(self)
        window.present()


class Main(Gtk.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app, title="Ohmychadwm Appearance")
        prefs = oma_config.load_prefs()
        self.set_default_size(prefs.get("window_width", 720), prefs.get("window_height", 680))
        self.connect("close-request", self._on_close)
        self._load_css()
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)
        oma_gui.build(self)
        log.log_timing("GUI built")

    def _load_css(self):
        css_path = os.path.join(BASE_DIR, "oma.css")
        if not os.path.isfile(css_path):
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _on_close(self, _window):
        w, h = self.get_default_size()
        oma_config.update_prefs({"window_width": w, "window_height": h})
        return False


def main():
    """Parse flags and run the application."""
    if "--debug" in sys.argv:
        log.DEBUG = True
    log.log_section("Ohmychadwm Appearance")
    AppearanceApp().run(None)


if __name__ == "__main__":
    main()
