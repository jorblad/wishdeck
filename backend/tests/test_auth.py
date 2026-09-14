from __future__ import annotations


async def test_register_first_user_becomes_admin(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "S3cret!!", "full_name": "Admin"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "admin"


async def test_register_then_login_sets_cookie(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "u@example.com", "password": "S3cret!!"},
    )
    r = await client.post("/api/v1/auth/login", json={"username": "u@example.com", "password": "S3cret!!"})
    assert r.status_code == 200
    assert "access_token" in r.cookies

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "u@example.com"


async def test_login_wrong_password_rejected(client):
    await client.post("/api/v1/auth/register", json={"email": "u2@example.com", "password": "S3cret!!"})
    r = await client.post("/api/v1/auth/login", json={"username": "u2@example.com", "password": "wrong"})
    assert r.status_code == 401


async def test_registration_disabled_via_env(client, monkeypatch):
    monkeypatch.setenv("ENABLE_REGISTRATION", "false")
    r = await client.post(
        "/api/v1/auth/register", json={"email": "x@example.com", "password": "S3cret!!"}
    )
    assert r.status_code == 403
