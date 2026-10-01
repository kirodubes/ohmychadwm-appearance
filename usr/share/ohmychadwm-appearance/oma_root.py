#!/usr/bin/env python3
"""Root helper, run via pkexec: GTK_THEME, the system/SDDM cursor and installing the rebuilt ohmychadwm binary.

Every root action of the app goes through this one script, so one Apply asks
for the password at most once. The install destination is fixed.
"""

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import oma_env  # noqa: E402
import oma_system  # noqa: E402

INSTALL_PATH = "/usr/local/bin/ohmychadwm"


def _write_file(path, transform):
    """Apply transform to a root-owned text file: one-time .oma-bak backup, atomic replace, mode 0644."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    new = transform(text)
    if new == text:
        return
    backup = path + ".oma-bak"
    if os.path.isfile(path) and not os.path.exists(backup):
        shutil.copy2(path, backup)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".oma-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def main():
    """Parse arguments and perform the requested root actions."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gtk-theme", help="force this GTK_THEME system-wide")
    group.add_argument("--release-gtk-theme", action="store_true", help="comment out GTK_THEME")
    parser.add_argument("--system-cursor", help="cursor for /usr/share/icons/default and the SDDM login screen")
    parser.add_argument("--cursor-size", type=int, default=24, help="SDDM cursor size (with --system-cursor)")
    parser.add_argument("--install", help="built ohmychadwm binary to install to " + INSTALL_PATH)
    args = parser.parse_args()

    if args.gtk_theme:
        _write_file(oma_env.ENV_FILE, lambda text: oma_env.force(text, args.gtk_theme))
    elif args.release_gtk_theme:
        _write_file(oma_env.ENV_FILE, oma_env.release)

    if args.system_cursor:
        if not oma_env.valid_name(args.system_cursor):
            parser.error(f"unsafe cursor name: {args.system_cursor!r}")
        cursor = args.system_cursor
        _write_file(oma_system.DEFAULT_INDEX, lambda text: oma_system.set_default_cursor(text, cursor))
        _write_file(oma_system.sddm_conf(), lambda text: oma_system.set_sddm_cursor(text, cursor, args.cursor_size))

    if args.install:
        os.makedirs(os.path.dirname(INSTALL_PATH), exist_ok=True)
        tmp = INSTALL_PATH + ".oma-tmp"
        shutil.copyfile(args.install, tmp)
        os.chmod(tmp, 0o755)
        os.replace(tmp, INSTALL_PATH)  # atomic, safe while the old binary is running


if __name__ == "__main__":
    main()
