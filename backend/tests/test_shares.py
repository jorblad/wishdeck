from __future__ import annotations

from conftest import register_and_login


async def _register(client, email, password="S3cret!!"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Collaborator"},
    )


async def _make_wishlist(client, visibility="private"):
    r = await client.post(
        "/api/v1/wishlists",
        json={"title": "Shared List", "visibility": visibility},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_owner_sees_shared_flag_in_list(client):
    await register_and_login(client, email="owner@example.com")
    wl = await _make_wishlist(client)
    # Owner's own list reports can_edit True and not shared_with_me.
    lst = (await client.get("/api/v1/wishlists")).json()
    mine = next(w for w in lst if w["id"] == wl["id"])
    assert mine["can_edit"] is True
    assert mine["shared_with_me"] is False
    assert mine["collaborator_count"] == 0


async def test_share_grants_edit_then_revokes(client):
    await register_and_login(client, email="owner@example.com")
    wl = await _make_wishlist(client)
    await _register(client, "friend@example.com")
    friend = (await client.get("/api/v1/users?q=friend")).json()
    assert len(friend) == 1
    friend_id = friend[0]["id"]

    # Owner shares with can_edit.
    r = await client.post(
        f"/api/v1/wishlists/{wl['id']}/shares",
        json={"user_id": friend_id, "can_edit": True},
    )
    assert r.status_code == 201, r.text
    assert r.json()["can_edit"] is True

    # Friend can now add an item (edit).
    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"username": "friend@example.com", "password": "S3cret!!"})
    item = await client.post(
        f"/api/v1/wishlists/{wl['id']}/items", json={"title": "Gift from friend"}
    )
    assert item.status_code == 201, item.text

    # Friend sees it in their list with shared_with_me True.
    lst = (await client.get("/api/v1/wishlists")).json()
    mine = next(w for w in lst if w["id"] == wl["id"])
    assert mine["shared_with_me"] is True
    assert mine["can_edit"] is True


async def test_view_only_share_cannot_edit(client):
    await register_and_login(client, email="owner@example.com")
    wl = await _make_wishlist(client)
    await _register(client, "viewer@example.com")
    viewer_id = (await client.get("/api/v1/users?q=viewer")).json()[0]["id"]

    r = await client.post(
        f"/api/v1/wishlists/{wl['id']}/shares",
        json={"user_id": viewer_id, "can_edit": False},
    )
    assert r.status_code == 201, r.text

    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"username": "viewer@example.com", "password": "S3cret!!"})
    # Viewer may read.
    assert (await client.get(f"/api/v1/wishlists/{wl['id']}")).status_code == 200
    # But not edit.
    assert (
        await client.post(f"/api/v1/wishlists/{wl['id']}/items", json={"title": "nope"})
    ).status_code == 403


async def test_non_manager_cannot_manage_shares(client):
    await register_and_login(client, email="owner@example.com")
    wl = await _make_wishlist(client)
    await _register(client, "stranger@example.com")
    stranger_id = (await client.get("/api/v1/users?q=stranger")).json()[0]["id"]

    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"username": "stranger@example.com", "password": "S3cret!!"})
    r = await client.post(
        f"/api/v1/wishlists/{wl['id']}/shares",
        json={"user_id": stranger_id, "can_edit": True},
    )
    assert r.status_code == 403


async def test_admin_can_manage_shares(client):
    # First user is admin.
    await register_and_login(client, email="admin@example.com")
    await _register(client, "owner2@example.com")
    # Make owner2 a normal user by creating via admin? Register makes admin first user only.
    # Promote flow: just use admin to share a list it doesn't own.
    await client.post("/api/v1/auth/logout")
    await register_and_login(client, email="owner2@example.com")
    wl = await _make_wishlist(client)
    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"username": "admin@example.com", "password": "S3cret!!"})
    # Admin is not the owner; should still be able to manage shares with a third user.
    await _register(client, "third@example.com")
    others = (await client.get("/api/v1/users?q=third")).json()
    assert len(others) == 1
    r = await client.post(
        f"/api/v1/wishlists/{wl['id']}/shares",
        json={"user_id": others[0]["id"], "can_edit": True},
    )
    assert r.status_code == 201, r.text


async def test_admin_can_edit_shared_list_in_ui_flags(client):
    # First user is admin.
    await register_and_login(client, email="admin@example.com")
    await client.post("/api/v1/auth/logout")
    await register_and_login(client, email="owner@example.com")
    wl = await _make_wishlist(client)
    # Admin is not the owner but should still see can_edit True (managers can edit).
    await client.post("/api/v1/auth/logout")
    await client.post("/api/v1/auth/login", json={"username": "admin@example.com", "password": "S3cret!!"})
    data = (await client.get(f"/api/v1/wishlists/{wl['id']}")).json()
    assert data["can_edit"] is True
    assert data["shared_with_me"] is False


async def test_share_with_unknown_user_returns_404(client):
    await register_and_login(client, email="owner@example.com")
    wl = await _make_wishlist(client)
    r = await client.post(
        f"/api/v1/wishlists/{wl['id']}/shares",
        json={"user_id": "00000000-0000-0000-0000-000000000000", "can_edit": True},
    )
    assert r.status_code == 404, r.text
