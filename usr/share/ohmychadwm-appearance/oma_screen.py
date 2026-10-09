"""Login screen layout for VirtualBox: save the current xrandr state as ~/.screenlayout/<user>.sh.

ohmychadwm's run.sh runs that file on session start. The script is written in arandr's format, so arandr can
open and edit it later. Toolkit-free.
"""

import getpass
import os
import re
import shutil
import subprocess

LAYOUT_DIR = os.path.expanduser("~/.screenlayout")

# "Virtual-1 connected primary 1920x1080+0+0 left (normal left inverted right x axis y axis) 0mm x 0mm"
_HEADER = re.compile(
    r"^(?P<name>\S+) (?P<state>connected|disconnected)(?P<primary> primary)?"
    r"(?: (?P<w>\d+)x(?P<h>\d+)\+(?P<x>\d+)\+(?P<y>\d+))?(?: (?P<rot>normal|left|inverted|right))?"
)


def is_virtualbox():
    """Return True when running inside a VirtualBox guest."""
    try:
        out = subprocess.run(["systemd-detect-virt", "--vm"], capture_output=True, text=True).stdout.strip()
        if out:
            return out == "oracle"
    except OSError:
        pass
    try:
        with open("/sys/class/dmi/id/product_name", encoding="utf-8") as f:
            return f.read().strip() == "VirtualBox"
    except OSError:
        return False


def layout_path():
    """Return the layout file run.sh runs on login: ~/.screenlayout/<user>.sh."""
    return os.path.join(LAYOUT_DIR, f"{getpass.getuser()}.sh")


def build_script(xrandr_query):
    """Turn `xrandr --query` output into an arandr-style layout script, or None when no output is active."""
    args, active = [], False
    for line in xrandr_query.splitlines():
        m = _HEADER.match(line)
        if not m:
            continue
        args += ["--output", m["name"]]
        if m["state"] == "connected" and m["w"]:
            active = True
            if m["primary"]:
                args.append("--primary")
            args += ["--mode", f"{m['w']}x{m['h']}", "--pos", f"{m['x']}x{m['y']}", "--rotate", m["rot"] or "normal"]
        else:
            args.append("--off")
    if not active:
        return None
    return "#!/bin/sh\nxrandr " + " ".join(args) + "\n"


def save_current():
    """Write the current resolution to layout_path(); return (ok, message)."""
    try:
        query = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        return False, f"xrandr failed: {e}"
    script = build_script(query)
    if script is None:
        return False, "xrandr reports no active display"
    path = layout_path()
    try:
        os.makedirs(LAYOUT_DIR, exist_ok=True)
        backup = path + ".oma-bak"
        if os.path.isfile(path) and not os.path.exists(backup):
            shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(path, 0o755)
    except OSError as e:
        return False, f"{path}: {e}"
    mode = re.search(r"--mode (\S+)", script)[1]
    return True, f"Saved {mode} to {path.replace(os.path.expanduser('~'), '~', 1)}, used from the next login."
