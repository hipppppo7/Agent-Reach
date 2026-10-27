# -*- coding: utf-8 -*-
"""The fork's zh / en / ja localization: language choice, skill files, receipts."""

import re

import pytest

from agent_reach.runtime import manage, onboarding
from agent_reach.utils import lang


@pytest.mark.parametrize("value, expected", [
    ("ja", "ja"), ("ja_JP.UTF-8", "ja"), ("zh_CN.UTF-8", "zh"), ("en_US.UTF-8", "en"),
])
def test_env_variable_picks_the_language(monkeypatch, value, expected):
    monkeypatch.setenv("AGENT_REACH_LANG", value)
    assert lang.current_lang() == expected


def test_os_locale_is_used_when_no_variable_is_set(monkeypatch):
    for var in ("AGENT_REACH_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(lang.locale, "getlocale", lambda: ("Japanese_Japan", "932"))
    assert lang.current_lang() == "ja"
    monkeypatch.setattr(lang.locale, "getlocale", lambda: (None, None))
    assert lang.current_lang() == "en"


def test_every_language_has_the_same_texts():
    for table in (onboarding._TEXT, onboarding._PUBLIC_ACCESS, onboarding._CAPABILITY_LIMITS,
                  onboarding._QUICK_ACCESS, onboarding._DISPLAY_NAMES, onboarding._STATUS_LABELS):
        assert set(table) == set(lang.LANGS)
        keys = set(table["zh"])
        for code in lang.LANGS:
            assert set(table[code]) == keys, code
    for key, value in onboarding._TEXT["zh"].items():
        wanted = set(re.findall(r"{(\w+)}", value))
        for code in ("en", "ja"):
            assert set(re.findall(r"{(\w+)}", onboarding._TEXT[code][key])) == wanted, (code, key)


@pytest.mark.parametrize("code", lang.LANGS)
def test_skill_and_references_exist_for_every_language(code):
    from importlib.resources import files

    skill_name, refs_name = manage._SKILL_FILES[code]
    skill = files("agent_reach").joinpath("skill")
    assert skill.joinpath(skill_name).is_file()
    zh_refs = sorted(p.name for p in skill.joinpath("references").iterdir() if p.name.endswith(".md"))
    assert sorted(p.name for p in skill.joinpath(refs_name).iterdir() if p.name.endswith(".md")) == zh_refs
    text = manage.render_skill(code)
    assert "{{" not in text and text.startswith("---\nname: agent-reach\n")


@pytest.mark.parametrize("code, header", [
    ("en", "| Platform | What works without login | Try after logging in |"),
    ("ja", "| プラットフォーム | ログインなしで調べられること | ログインしてから試すこと |"),
])
def test_installation_report_follows_the_language(monkeypatch, code, header):
    monkeypatch.setenv("AGENT_REACH_LANG", code)
    summary = onboarding.capability_summary([], [])
    report = onboarding.installation_report({
        "version": "1.6.0.1", "capability_summary": summary, "default_channels": [],
    })
    assert header in report
    if code == "en":
        assert not re.search(r"[一-鿿]", report)
