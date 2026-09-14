from __future__ import annotations

from conftest import register_and_login


async def _make_wishlist(client, visibility="public", allow_claims=True):
    r = await client.post(
        "/api/v1/wishlists",
        json={"title": "Birthday", "visibility": visibility, "allow_claims": allow_claims},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_crud_wishlist_and_items(client):
    await register_and_login(client)
    wl = await _make_wishlist(client, visibility="private")

    cat = (await client.post(f"/api/v1/wishlists/{wl['id']}/categories",
                             json={"name": "Books", "color": "#ff0000"})).json()
    item = (await client.post(
        f"/api/v1/wishlists/{wl['id']}/items",
        json={"title": "Cool Book", "category_id": cat["id"], "price": 19.9, "currency": "USD"},
    )).json()
    assert item["title"] == "Cool Book" and item["status"] == "open"


async def test_public_view_requires_visibility(client):
    await register_and_login(client)
    wl = await _make_wishlist(client, visibility="private")

    r = await client.get(f"/api/v1/wishlists/public/{wl['slug']}")
    assert r.status_code == 403

    # Make it public and fetch anonymously.
    await client.put(f"/api/v1/wishlists/{wl['id']}", json={"visibility": "public"})
    anon = (await client.get(f"/api/v1/wishlists/public/{wl['slug']}"))
    assert anon.status_code == 200


async def test_claim_respects_flag(client, monkeypatch):
    await register_and_login(client)
    wl = await _make_wishlist(client, visibility="public", allow_claims=True)
    item = (await client.post(f"/api/v1/wishlists/{wl['id']}/items",
                              json={"title": "Gift"})).json()

    # Authenticated owner can claim.
    claim = await client.post(f"/api/v1/wishlists/items/{item['id']}/claim")
    assert claim.status_code == 200
    assert claim.json()["status"] == "claimed"

    # When ALLOW_PUBLIC_CLAIMS is disabled, anonymous claiming is blocked.
    monkeypatch.setenv("ALLOW_PUBLIC_CLAIMS", "false")
    item2 = (await client.post(f"/api/v1/wishlists/{wl['id']}/items",
                               json={"title": "Gift2"})).json()
    await client.post("/api/v1/auth/logout")
    anon = await client.post(f"/api/v1/wishlists/items/{item2['id']}/claim")
    assert anon.status_code == 403

    # An authenticated user may still claim.
    await client.post("/api/v1/auth/login",
                      json={"username": "owner@example.com", "password": "S3cret!!"})
    authed = await client.post(f"/api/v1/wishlists/items/{item2['id']}/claim")
    assert authed.status_code == 200
