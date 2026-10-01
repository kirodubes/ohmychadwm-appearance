"""The ohmychadwm half: bar theme include, managed bar-font block, rebuild and restart.

Every theme header defines its own THEME_FONT, so the #ifndef fallback in
config.def.h never fires. The bar font is therefore overridden by a managed
#undef/#define block placed *after* the theme includes. Text transforms are pure
functions over the file contents so they can be tested without touching disk.
"""

import os
import re
import shutil
import subprocess

CHADWM_DIR = os.path.expanduser("~/.config/ohmychadwm/chadwm")
CONFIG = os.path.join(CHADWM_DIR, "config.def.h")
INSTALL_PATH = "/usr/local/bin/ohmychadwm"

_INCLUDE_RE = re.compile(r'^(\s*)(//\s*)?#include\s+"themes/([^"/]+)\.h"')
BLOCK_BEGIN = "/* >>> ohmychadwm-appearance managed - regenerated, do not hand-edit >>> */"
BLOCK_END = "/* <<< ohmychadwm-appearance managed <<< */"


def themes():
    """Return the sorted bar theme names found in the user's chadwm/themes directory."""
    try:
        names = os.listdir(os.path.join(CHADWM_DIR, "themes"))
    except OSError:
        return []
    return sorted((n[:-2] for n in names if n.endswith(".h")), key=str.lower)


def read_config():
    """Return the user's config.def.h contents, or '' when ohmychadwm isn't set up."""
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def write_config(text):
    """Write config.def.h, keeping a one-time .oma-bak copy of the original."""
    backup = CONFIG + ".oma-bak"
    if not os.path.exists(backup) and os.path.exists(CONFIG):
        shutil.copy2(CONFIG, backup)
    with open(CONFIG, "w", encoding="utf-8") as f:
        f.write(text)


def active_theme(text):
    """Return the name of the uncommented theme include, or None."""
    for line in text.splitlines():
        m = _INCLUDE_RE.match(line)
        if m and not m.group(2):
            return m.group(3)
    return None


def set_theme(text, name):
    """Return text with exactly one theme include active: the one called name."""
    lines = text.splitlines(keepends=True)
    seen = False
    last = -1
    for i, line in enumerate(lines):
        m = _INCLUDE_RE.match(line)
        if not m:
            continue
        last = i
        indent, _comment, stem = m.groups()
        eol = "\n" if line.endswith("\n") else ""
        if stem == name:
            seen = True
            lines[i] = f'{indent}#include "themes/{stem}.h"{eol}'
        else:
            lines[i] = f'{indent}//#include "themes/{stem}.h"{eol}'
    if not seen:
        if last < 0:
            raise ValueError("no theme #include lines found in config.def.h")
        lines.insert(last + 1, f'#include "themes/{name}.h"\n')
    return "".join(lines)


def _strip_block(lines):
    out, inside = [], False
    for line in lines:
        if line.strip() == BLOCK_BEGIN:
            inside = True
        elif line.strip() == BLOCK_END:
            inside = False
        elif not inside:
            out.append(line)
    return out


def bar_font(text):
    """Return (family, size) from the managed block, or None when the theme's own font is used."""
    m = re.search(
        re.escape(BLOCK_BEGIN) + r'.*?#define\s+THEME_FONT\s+"([^"]*)".*?#define\s+THEME_FONTSIZE\s+(\d+)',
        text,
        re.S,
    )
    return (m.group(1), int(m.group(2))) if m else None


def clear_bar_font(text):
    """Return text without the managed bar-font block (the theme's own font applies again)."""
    return "".join(_strip_block(text.splitlines(keepends=True)))


def set_bar_font(text, family, size):
    """Return text with a managed block overriding THEME_FONT/THEME_FONTSIZE after the theme includes."""
    family = family.replace('"', "").replace("\\", "")
    lines = _strip_block(text.splitlines(keepends=True))
    last = max((i for i, line in enumerate(lines) if _INCLUDE_RE.match(line)), default=-1)
    if last < 0:
        raise ValueError("no theme #include lines found in config.def.h")
    block = [
        BLOCK_BEGIN + "\n",
        "#undef  THEME_FONT\n",
        f'#define THEME_FONT     "{family}"\n',
        "#undef  THEME_FONTSIZE\n",
        f"#define THEME_FONTSIZE {int(round(size))}\n",
        BLOCK_END + "\n",
    ]
    lines[last + 1:last + 1] = block
    return "".join(lines)


def _run(cmd):
    proc = subprocess.run(cmd, cwd=CHADWM_DIR, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def rebuild():
    """Compile ohmychadwm as the user and install it with one pkexec prompt; return (ok, message)."""
    # config.h is only regenerated from config.def.h when missing, so clean first.
    _run(["make", "clean"])
    rc, out = _run(["make"])
    if rc != 0:
        _run(["make", "clean"])
        return False, "Compile failed:\n" + out[-1500:]
    rc, out = _run(["pkexec", "install", "-Dm755", os.path.join(CHADWM_DIR, "ohmychadwm"), INSTALL_PATH])
    _run(["make", "clean"])
    if rc != 0:
        return False, "Install was cancelled or failed" + (f":\n{out}" if out else "")
    return True, f"ohmychadwm rebuilt and installed to {INSTALL_PATH}"


def can_restart():
    """Return True when the app can restart ohmychadwm itself (needs xdotool)."""
    return shutil.which("xdotool") is not None


def restart():
    """Send Super+Shift+R; dwm's restart exits 0 and the run.sh session loop relaunches it."""
    subprocess.Popen(["xdotool", "key", "--clearmodifiers", "super+shift+r"])
