from __future__ import annotations

import pytest

from conftest import register_and_login
from app.core.config import resolve_settings


def test_env_overrides_db_and_default(monkeypatch):
    # DB value should be used when env is absent.
    out = resolve_settings({"ALLOW_PUBLIC_CLAIMS": "false"})
    s = next(x for x in out if x["key"] == "ALLOW_PUBLIC_CLAIMS")
    assert s["value"] is False
    assert s["source"] == "database"
    assert s["is_env_overridden"] is False

    # ENV should win and be flagged.
    monkeypatch.setenv("ALLOW_PUBLIC_CLAIMS", "true")
    out = resolve_settings({"ALLOW_PUBLIC_CLAIMS": "false"})
    s = next(x for x in out if x["key"] == "ALLOW_PUBLIC_CLAIMS")
    assert s["value"] is True
    assert s["source"] == "env"
    assert s["is_env_overridden"] is True


def test_int_and_bool_coercion(monkeypatch):
    monkeypatch.setenv("ITEMS_PER_PAGE", "25")
    out = resolve_settings()
    s = next(x for x in out if x["key"] == "ITEMS_PER_PAGE")
    assert s["value"] == 25 and isinstance(s["value"], int)


async def test_settings_api_structure(client):
    await register_and_login(client)
    resp = await client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()["settings"]
    keys = {s["key"] for s in data}
    assert "ALLOW_PUBLIC_CLAIMS" in keys and "OIDC_ENABLED" in keys
    for s in data:
        assert {"key", "value", "is_env_overridden", "source", "editable"} <= s.keys()


async def test_put_ignores_env_overridden(client, monkeypatch):
    await register_and_login(client)  # first user becomes admin
    monkeypatch.setenv("ALLOW_PUBLIC_CLAIMS", "true")

    # Attempt to change the env-locked key + an editable key.
    resp = await client.put(
        "/api/v1/settings",
        json={"values": {"ALLOW_PUBLIC_CLAIMS": False, "DEFAULT_VISIBILITY": "public"}},
    )
    assert resp.status_code == 200
    data = {s["key"]: s for s in resp.json()["settings"]}

    # Env value must NOT have been changed by the UI.
    assert data["ALLOW_PUBLIC_CLAIMS"]["value"] is True
    assert data["ALLOW_PUBLIC_CLAIMS"]["is_env_overridden"] is True
    # Editable, non-env key should reflect the new value.
    assert data["DEFAULT_VISIBILITY"]["value"] == "public"


async def test_public_settings_exposes_default_locale(client, monkeypatch):
    # DEFAULT_LOCALE is public; ENV must win over the DB/UI value.
    monkeypatch.setenv("DEFAULT_LOCALE", "sv")
    resp = await client.get("/api/v1/settings/public")
    assert resp.status_code == 200
    body = resp.json()
    assert body["DEFAULT_LOCALE"] == "sv"
    # Secrets must never leak through the public endpoint.
    assert "OIDC_CLIENT_SECRET" not in body
    assert "SECRET_KEY" not in body

