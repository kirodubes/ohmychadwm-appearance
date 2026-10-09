"""Screen resolution for VirtualBox: apply a mode now and save it as ~/.screenlayout/<user>.sh.

ohmychadwm's run.sh runs that file on session start. The script is written in arandr's format, so arandr can
open and edit it later. Toolkit-free.
"""

import getpass
import os
import re
import shutil
import subprocess

LAYOUT_DIR = os.path.expanduser("~/.screenlayout")

PREFERRED_MODE = "1920x1080"

_MODE = re.compile(r"^\s+(\d+x\d+)\s")
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


def _query():
    return subprocess.run(["xrandr", "--query"], capture_output=True, text=True, check=True).stdout


def _main_output(xrandr_query):
    """Return (name, modes) of the primary output, else the first connected one; (None, []) when none."""
    found, current = [], None
    for line in xrandr_query.splitlines():
        m = _HEADER.match(line)
        if m:
            current = None
            if m["state"] == "connected":
                current = (m["name"], bool(m["primary"]), [])
                found.append(current)
        elif current is not None and (mode := _MODE.match(line)) and mode[1] not in current[2]:
            current[2].append(mode[1])
    if not found:
        return None, []
    name, _primary, modes = next((o for o in found if o[1]), found[0])
    return name, modes


def modes():
    """Return (modes, default) for the main output: xrandr's list and the mode to preselect."""
    try:
        _name, found = _main_output(_query())
    except (OSError, subprocess.CalledProcessError):
        return [], None
    if not found:
        return [], None
    return found, PREFERRED_MODE if PREFERRED_MODE in found else found[0]


def build_script(xrandr_query, mode=None):
    """Turn `xrandr --query` into an arandr-style layout script (main output set to mode), or None if nothing is on."""
    main, _modes = _main_output(xrandr_query)
    args, active = [], False
    for line in xrandr_query.splitlines():
        m = _HEADER.match(line)
        if not m:
            continue
        args += ["--output", m["name"]]
        if m["state"] == "connected" and (m["w"] or (mode and m["name"] == main)):
            active = True
            if m["primary"] or m["name"] == main:
                args.append("--primary")
            size = mode if mode and m["name"] == main else f"{m['w']}x{m['h']}"
            pos = f"{m['x']}x{m['y']}" if m["w"] else "0x0"
            args += ["--mode", size, "--pos", pos, "--rotate", m["rot"] or "normal"]
        else:
            args.append("--off")
    if not active:
        return None
    return "#!/bin/sh\nxrandr " + " ".join(args) + "\n"


def apply_and_save(mode):
    """Switch the main output to mode now and save it to layout_path(); return (ok, message)."""
    try:
        script = build_script(_query(), mode)
    except (OSError, subprocess.CalledProcessError) as e:
        return False, f"xrandr failed: {e}"
    if script is None:
        return False, "xrandr reports no connected display"
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
    short = path.replace(os.path.expanduser("~"), "~", 1)
    proc = subprocess.run(["sh", path], capture_output=True, text=True)
    if proc.returncode != 0:
        return False, f"Saved to {short}, but xrandr could not switch to {mode}: {proc.stderr.strip()}"
    return True, f"Screen set to {mode} and saved to {short}, so every login uses it."
