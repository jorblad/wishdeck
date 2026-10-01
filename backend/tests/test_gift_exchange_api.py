from __future__ import annotations

from datetime import datetime, timezone

from conftest import register_and_login


def _enable(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_GIFT_EXCHANGE", "true")


async def test_gift_exchange_flow(client, monkeypatch):
    _enable(monkeypatch)
    await register_and_login(client)

    # Group + participants: two siblings (family A) and two cousins (family B).
    group = await client.post("/api/v1/gift-exchange/groups", json={"name": "Family"})
    assert group.status_code == 201, group.text
    gid = group.json()["id"]

    a = (await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/participants",
        json={"name": "Alice", "family": "A"},
    )).json()
    b = (await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/participants",
        json={"name": "Bob", "family": "A"},
    )).json()
    c = (await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/participants",
        json={"name": "Cousin1", "family": "B"},
    )).json()
    d = (await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/participants",
        json={"name": "Cousin2", "family": "B"},
    )).json()

    draw = await client.post(f"/api/v1/gift-exchange/groups/{gid}/draw")
    assert draw.status_code == 200, draw.text
    data = draw.json()
    assert data["unsolvable"] is False
    assert data["year"] == datetime.now(timezone.utc).year
    assigns = {x["giver_id"]: x["receiver_id"] for x in data["assignments"]}
    assert set(assigns) == {a["id"], b["id"], c["id"], d["id"]}

    fam = {a["id"]: "A", b["id"]: "A", c["id"]: "B", d["id"]: "B"}
    for giver, receiver in assigns.items():
        assert fam[giver] != fam[receiver]

    fetched = (await client.get(f"/api/v1/gift-exchange/groups/{gid}/assignments")).json()
    assert len(fetched) == 4

    # A second draw for the same year replaces the previous one.
    draw2 = (await client.post(f"/api/v1/gift-exchange/groups/{gid}/draw")).json()
    assert len(draw2["assignments"]) == 4


async def test_gift_exchange_feature_flag_gate(client, monkeypatch):
    await register_and_login(client)
    r = await client.get("/api/v1/gift-exchange/groups")
    assert r.status_code == 403

    _enable(monkeypatch)
    r2 = await client.get("/api/v1/gift-exchange/groups")
    assert r2.status_code == 200
