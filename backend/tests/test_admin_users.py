"""Admin user-management endpoints."""
from __future__ import annotations

from conftest import register_and_login


async def test_admin_can_list_and_create_users(client):
    await register_and_login(client)  # first user -> admin
    resp = await client.get("/api/v1/auth/users")
    assert resp.status_code == 200
    assert any(u["role"] == "admin" for u in resp.json())

    created = await client.post(
        "/api/v1/auth/users",
        json={"email": "new@example.com", "password": "S3cret!!", "role": "user"},
    )
    assert created.status_code == 201
    assert created.json()["email"] == "new@example.com"

    uid = created.json()["id"]
    upd = await client.put(f"/api/v1/auth/users/{uid}", json={"role": "admin"})
    assert upd.status_code == 200 and upd.json()["role"] == "admin"

    dele = await client.delete(f"/api/v1/auth/users/{uid}")
    assert dele.status_code == 204


async def test_non_admin_cannot_list_users(client):
    await register_and_login(client)  # admin
    # Second account is a regular user.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "S3cret!!"},
    )
    await client.post(
        "/api/v1/auth/login", json={"username": "user@example.com", "password": "S3cret!!"}
    )
    resp = await client.get("/api/v1/auth/users")
    assert resp.status_code == 403


async def test_admin_cannot_delete_self(client):
    await register_and_login(client)  # admin
    me = (await client.get("/api/v1/auth/me")).json()
    resp = await client.delete(f"/api/v1/auth/users/{me['id']}")
    assert resp.status_code == 400
