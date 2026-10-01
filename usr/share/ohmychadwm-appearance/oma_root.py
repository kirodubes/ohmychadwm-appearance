#!/usr/bin/env python3
"""Root helper, run via pkexec: set or release GTK_THEME and/or install the rebuilt ohmychadwm binary.

Every root action of the app goes through this one script, so one Apply asks
for the password at most once. The install destination is fixed.
"""

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import oma_env  # noqa: E402

INSTALL_PATH = "/usr/local/bin/ohmychadwm"


def _write_env(transform):
    try:
        with open(oma_env.ENV_FILE, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    new = transform(text)
    if new == text:
        return
    backup = oma_env.ENV_FILE + ".oma-bak"
    if os.path.isfile(oma_env.ENV_FILE) and not os.path.exists(backup):
        shutil.copy2(oma_env.ENV_FILE, backup)
    tmp = oma_env.ENV_FILE + ".oma-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.chmod(tmp, 0o644)
    os.replace(tmp, oma_env.ENV_FILE)


def main():
    """Parse arguments and perform the requested root actions."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gtk-theme", help="force this GTK_THEME system-wide")
    group.add_argument("--release-gtk-theme", action="store_true", help="comment out GTK_THEME")
    parser.add_argument("--install", help="built ohmychadwm binary to install to " + INSTALL_PATH)
    args = parser.parse_args()

    if args.gtk_theme:
        _write_env(lambda text: oma_env.force(text, args.gtk_theme))
    elif args.release_gtk_theme:
        _write_env(oma_env.release)

    if args.install:
        os.makedirs(os.path.dirname(INSTALL_PATH), exist_ok=True)
        tmp = INSTALL_PATH + ".oma-tmp"
        shutil.copyfile(args.install, tmp)
        os.chmod(tmp, 0o755)
        os.replace(tmp, INSTALL_PATH)  # atomic, safe while the old binary is running


if __name__ == "__main__":
    main()
