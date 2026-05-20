# SPDX-FileCopyrightText: 2026 William Jin <AuraMindNest@outlook.com>
#
# SPDX-License-Identifier: BSL-1.0

from __future__ import annotations

import builtins
import importlib.util
import logging
import sys
import types
from pathlib import Path

import pytest
from django.test import RequestFactory

from boost_weblate.endpoint.views import plugin_ping

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_register_plugin_urls_appends_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.ModuleType("weblate.urls")
    fake.real_patterns = []
    fake._cppa_boost_weblate_urls_registered = False
    monkeypatch.setitem(sys.modules, "weblate.urls", fake)

    from boost_weblate.endpoint.apps import register_plugin_urls

    register_plugin_urls()
    register_plugin_urls()

    assert len(fake.real_patterns) == 1


def test_plugin_ping_returns_200() -> None:
    request = RequestFactory().get("/plugin-ping/")
    response = plugin_ping(request)
    assert response.status_code == 200
    assert response.content == b"ok"


def test_register_plugin_urls_skips_on_weblate_urls_import_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals_arg: dict | None = None,
        locals_arg: dict | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ):
        if name == "weblate.urls":
            msg = "No module named 'weblate.urls'"
            raise ModuleNotFoundError(msg)
        return real_import(name, globals_arg, locals_arg, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    caplog.set_level(logging.DEBUG, logger="boost_weblate.endpoint.apps")

    from boost_weblate.endpoint.apps import register_plugin_urls

    register_plugin_urls()
    assert "skipping URL registration" in caplog.text


def test_register_plugin_urls_warns_without_real_patterns(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = types.ModuleType("weblate.urls")
    fake._cppa_boost_weblate_urls_registered = False
    monkeypatch.setitem(sys.modules, "weblate.urls", fake)

    from boost_weblate.endpoint.apps import register_plugin_urls

    with caplog.at_level(logging.WARNING, logger="boost_weblate.endpoint.apps"):
        register_plugin_urls()
    assert "no real_patterns" in caplog.text


def test_boost_endpoint_config_ready_registers_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = types.ModuleType("weblate.urls")
    fake.real_patterns = []
    fake._cppa_boost_weblate_urls_registered = False
    monkeypatch.setitem(sys.modules, "weblate.urls", fake)

    import boost_weblate.endpoint.apps as apps_module
    from boost_weblate.endpoint.apps import BoostEndpointConfig

    cfg = BoostEndpointConfig("boost_weblate.endpoint", apps_module)
    cfg.ready()
    assert len(fake.real_patterns) == 1


@pytest.mark.parametrize(
    "installed_apps",
    [
        pytest.param((), id="tuple"),
        pytest.param([], id="list"),
    ],
)
def test_settings_override_exec_appends_format_and_endpoint_app(
    installed_apps: tuple[str, ...] | list[str],
) -> None:
    """Load ``settings_override.py`` as ``boost_weblate.settings_override``.

    Covers tuple (immutable reassignment) and list (Docker / in-place ``+=``).

    Used so coverage attributes execution to the real file path.
    """
    settings_path = _REPO_ROOT / "src" / "boost_weblate" / "settings_override.py"
    name = "boost_weblate.settings_override"
    saved = sys.modules.pop(name, None)
    try:
        spec = importlib.util.spec_from_file_location(name, settings_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        module.__dict__["WEBLATE_FORMATS"] = ()
        module.__dict__["INSTALLED_APPS"] = installed_apps
        sys.modules[name] = module
        spec.loader.exec_module(module)
        formats = module.WEBLATE_FORMATS
        apps_out = module.INSTALLED_APPS
    finally:
        if saved is not None:
            sys.modules[name] = saved
        else:
            sys.modules.pop(name, None)

    assert isinstance(formats, tuple)
    assert "boost_weblate.formats.quickbook.QuickBookFormat" in formats
    assert "boost_weblate.endpoint.apps.BoostEndpointConfig" in apps_out
    if isinstance(installed_apps, list):
        assert apps_out is installed_apps
    else:
        assert isinstance(apps_out, tuple)
