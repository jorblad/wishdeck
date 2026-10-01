from __future__ import annotations

from datetime import datetime, timezone

from conftest import register_and_login


def _enable(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_GIFT_EXCHANGE", "true")


async def test_gift_exchange_flow(client, monkeypatch):
    _enable(monkeypatch)
    await register_and_login(client)

    me = (await client.get("/api/v1/auth/me")).json()

    # Create group + global people: two siblings (family A) and two cousins (B).
    group = (await client.post("/api/v1/gift-exchange/groups", json={"name": "Family"})).json()
    gid = group["id"]

    alice = (await client.post("/api/v1/people", json={"name": "Alice", "family": "A"})).json()
    bob = (await client.post("/api/v1/people", json={"name": "Bob", "family": "A"})).json()
    c1 = (await client.post("/api/v1/people", json={"name": "Cousin1", "family": "B"})).json()
    c2 = (await client.post("/api/v1/people", json={"name": "Cousin2", "family": "B"})).json()
    names = {p["id"]: p["name"] for p in (alice, bob, c1, c2)}

    for pid in (alice["id"], bob["id"], c1["id"], c2["id"]):
        r = await client.post(
            f"/api/v1/gift-exchange/groups/{gid}/members", json={"person_id": pid}
        )
        assert r.status_code == 201, r.text

    # Same person cannot be added twice.
    dup = await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/members", json={"person_id": alice["id"]}
    )
    assert dup.status_code == 201

    # Owner list + detail surfaces members (regression: model_validate(update=)).
    groups = (await client.get("/api/v1/gift-exchange/groups")).json()
    assert any(g["id"] == gid and len(g["members"]) == 4 for g in groups)
    detail = (await client.get(f"/api/v1/gift-exchange/groups/{gid}")).json()
    assert {m["id"] for m in detail["members"]} == {
        alice["id"], bob["id"], c1["id"], c2["id"]
    }

    # Run the draw.
    draw = (await client.post(f"/api/v1/gift-exchange/groups/{gid}/draw")).json()
    assert draw["unsolvable"] is False
    assert draw["year"] == datetime.now(timezone.utc).year
    assigns = {a["giver_id"]: a["receiver_id"] for a in draw["assignments"]}
    assert set(assigns) == {alice["id"], bob["id"], c1["id"], c2["id"]}

    # No intra-family pairing (siblings A never paired with A, cousins B with B).
    fam = {alice["id"]: "A", bob["id"]: "A", c1["id"]: "B", c2["id"]: "B"}
    for giver, receiver in assigns.items():
        assert fam[giver] != fam[receiver]

    # A second draw for the same year replaces the previous one.
    draw2 = (await client.post(f"/api/v1/gift-exchange/groups/{gid}/draw")).json()
    assert len(draw2["assignments"]) == 4

    # Assignments are persisted and retrievable.
    fetched = (await client.get(f"/api/v1/gift-exchange/groups/{gid}/assignments")).json()
    assert len(fetched) == 4

    # A linked member can read their own assignment (against the current draw).
    await client.put(f"/api/v1/people/{alice['id']}", json={"user_id": me["id"]})
    current = {a["giver_id"]: a["receiver_id"] for a in draw2["assignments"]}
    my = (await client.get(f"/api/v1/gift-exchange/groups/{gid}/assignment/me")).json()
    assert my["receiver_name"] == names[current[alice["id"]]]

    # Removing a member works.
    rm = await client.delete(
        f"/api/v1/gift-exchange/groups/{gid}/members/{bob['id']}"
    )
    assert rm.status_code == 204


async def test_people_families_endpoint(client, monkeypatch):
    _enable(monkeypatch)
    await register_and_login(client)

    await client.post("/api/v1/people", json={"name": "A", "family": "Smith"})
    await client.post("/api/v1/people", json={"name": "B", "family": "Smith"})
    await client.post("/api/v1/people", json={"name": "C", "family": "Jones"})
    await client.post("/api/v1/people", json={"name": "D"})

    families = (await client.get("/api/v1/people/families")).json()
    assert families == ["Jones", "Smith"]


async def test_history_avoids_previous_pairs(client, monkeypatch):
    _enable(monkeypatch)
    await register_and_login(client)

    group = (await client.post("/api/v1/gift-exchange/groups", json={"name": "G"})).json()
    gid = group["id"]
    a = (await client.post("/api/v1/people", json={"name": "A"})).json()
    b = (await client.post("/api/v1/people", json={"name": "B"})).json()
    c = (await client.post("/api/v1/people", json={"name": "C"})).json()
    for pid in (a["id"], b["id"], c["id"]):
        await client.post(
            f"/api/v1/gift-exchange/groups/{gid}/members", json={"person_id": pid}
        )

    prev_year = datetime.now(timezone.utc).year - 1
    hist = await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/assignments",
        json={
            "year": prev_year,
            "assignments": [
                {"giver_id": a["id"], "receiver_id": b["id"]},
                {"giver_id": b["id"], "receiver_id": c["id"]},
                {"giver_id": c["id"], "receiver_id": a["id"]},
            ],
        },
    )
    assert hist.status_code == 201, hist.text
    assert (await client.get(f"/api/v1/gift-exchange/groups/{gid}/history")).json() == [
        prev_year
    ]

    draw = (await client.post(f"/api/v1/gift-exchange/groups/{gid}/draw")).json()
    assert draw["unsolvable"] is False
    pairs = {(x["giver_id"], x["receiver_id"]) for x in draw["assignments"]}
    assert (a["id"], b["id"]) not in pairs
    assert (b["id"], c["id"]) not in pairs
    assert (c["id"], a["id"]) not in pairs

    # Re-posting the same year replaces, not duplicates.
    hist2 = await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/assignments",
        json={
            "year": prev_year,
            "assignments": [
                {"giver_id": a["id"], "receiver_id": b["id"]},
                {"giver_id": b["id"], "receiver_id": c["id"]},
                {"giver_id": c["id"], "receiver_id": a["id"]},
            ],
        },
    )
    assert hist2.status_code == 201
    assert len(hist2.json()) == 3

    # Non-member pairing is rejected.
    bad = await client.post(
        f"/api/v1/gift-exchange/groups/{gid}/assignments",
        json={
            "year": prev_year,
            "assignments": [{"giver_id": a["id"], "receiver_id": "does-not-exist"}],
        },
    )
    assert bad.status_code == 422


async def test_gift_exchange_feature_flag_gate(client, monkeypatch):
    await register_and_login(client)
    r = await client.get("/api/v1/gift-exchange/groups")
    assert r.status_code == 403

    r2 = await client.get("/api/v1/people")
    assert r2.status_code == 403

    _enable(monkeypatch)
    assert (await client.get("/api/v1/gift-exchange/groups")).status_code == 200
    assert (await client.get("/api/v1/people")).status_code == 200
