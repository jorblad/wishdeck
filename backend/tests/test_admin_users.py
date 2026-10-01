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


async def test_admin_can_update_user_profile_fields(client):
    """Editing a user's full name / email / username must persist.

    Regression test: the update endpoint previously ignored every profile
    field and only applied role / is_active / password, so name changes were
    silently dropped while the API still reported success.
    """
    await register_and_login(client)  # admin
    created = await client.post(
        "/api/v1/auth/users",
        json={"email": "edit@example.com", "password": "S3cret!!", "role": "user"},
    )
    uid = created.json()["id"]

    upd = await client.put(
        f"/api/v1/auth/users/{uid}",
        json={
            "email": "edit2@example.com",
            "username": "editeduser",
            "full_name": "Edited Name",
            "role": "user",
        },
    )
    assert upd.status_code == 200
    body = upd.json()
    assert body["full_name"] == "Edited Name"
    assert body["email"] == "edit2@example.com"
    assert body["username"] == "editeduser"

    # Verify it actually persisted (not just echoed) by re-fetching the list.
    listing = await client.get("/api/v1/auth/users")
    match = next(u for u in listing.json() if u["id"] == uid)
    assert match["full_name"] == "Edited Name"
    assert match["email"] == "edit2@example.com"

    # Clearing a nullable field (username) should persist as null.
    cleared = await client.put(
        f"/api/v1/auth/users/{uid}", json={"username": "", "full_name": "Renamed"}
    )
    assert cleared.status_code == 200
    assert cleared.json()["username"] is None
    assert cleared.json()["full_name"] == "Renamed"


async def test_admin_cannot_update_user_email_to_duplicate(client):
    await register_and_login(client)  # admin
    a = await client.post(
        "/api/v1/auth/users",
        json={"email": "dup_a@example.com", "password": "S3cret!!", "role": "user"},
    )
    b = await client.post(
        "/api/v1/auth/users",
        json={"email": "dup_b@example.com", "password": "S3cret!!", "role": "user"},
    )
    conflict = await client.put(
        f"/api/v1/auth/users/{b.json()['id']}", json={"email": "dup_a@example.com"}
    )
    assert conflict.status_code == 409
    await client.delete(f"/api/v1/auth/users/{a.json()['id']}")
    await client.delete(f"/api/v1/auth/users/{b.json()['id']}")


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
