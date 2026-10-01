"""App preferences for ohmychadwm-appearance (window size) under ~/.config/ohmychadwm-appearance/."""

import json
import os

PREFS_PATH = os.path.expanduser("~/.config/ohmychadwm-appearance/prefs.json")


def load_prefs():
    """Return the saved preferences dict, or an empty dict if none exist."""
    if not os.path.isfile(PREFS_PATH):
        return {}
    try:
        with open(PREFS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def update_prefs(updates):
    """Merge updates into the on-disk prefs and save; return the merged dict."""
    prefs = load_prefs()
    prefs.update(updates)
    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    with open(PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)
    return prefs
