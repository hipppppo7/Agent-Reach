"""Language for the skill and the user-facing receipts: zh | en | ja.

`AGENT_REACH_LANG` wins; then the usual locale variables; then the OS locale
(Windows reports e.g. "Japanese_Japan"). Anything else falls back to English.
"""
import locale
import os

LANGS = ("zh", "en", "ja")


def _match(value: str):
    v = value.strip().lower()
    if v.startswith(("ja", "japanese")):
        return "ja"
    if v.startswith(("zh", "chinese")):
        return "zh"
    if v.startswith(("en", "english")):
        return "en"
    return None


def current_lang() -> str:
    for var in ("AGENT_REACH_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        found = _match(os.environ.get(var, ""))
        if found:
            return found
    try:
        found = _match(locale.getlocale()[0] or "")
    except (TypeError, ValueError):
        found = None
    return found or "en"
