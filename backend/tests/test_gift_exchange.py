from __future__ import annotations

import random

from app.services.gift_exchange import compute_draw


def _ids(participants):
    return {p["id"] for p in participants}


def test_basic_derangement_is_a_bijection_with_no_self():
    participants = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    result = compute_draw(participants, rng=random.Random(1))
    assert result is not None
    # bijection
    assert set(result.keys()) == _ids(participants)
    assert set(result.values()) == _ids(participants)
    # no one gives to themselves
    assert all(g != r for g, r in result.items())


def test_family_members_are_never_paired():
    participants = [
        {"id": "a", "family": "X"},
        {"id": "b", "family": "X"},   # sibling of a
        {"id": "c", "family": "Y"},   # cousin
        {"id": "d", "family": "Y"},   # cousin
    ]
    result = compute_draw(participants, rng=random.Random(2))
    assert result is not None
    # no same-family pair in either direction
    fam = {p["id"]: p["family"] for p in participants}
    for giver, receiver in result.items():
        assert fam[giver] != fam[receiver]


def test_single_family_is_unsolvable():
    participants = [
        {"id": "a", "family": "X"},
        {"id": "b", "family": "X"},
        {"id": "c", "family": "X"},
    ]
    assert compute_draw(participants, rng=random.Random(3)) is None


def test_history_pairs_are_avoided():
    participants = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    # last year a -> b; this year that pair must not repeat
    previous = [("a", "b")]
    result = compute_draw(participants, previous_pairs=previous, rng=random.Random(4))
    assert result is not None
    assert result["a"] != "b"
    # still a valid derangement
    assert set(result.keys()) == _ids(participants)
    assert set(result.values()) == _ids(participants)


def test_history_can_make_small_group_unsolvable():
    # Only two participants; if last year already paired them, no new pair exists.
    participants = [{"id": "a"}, {"id": "b"}]
    previous = [("a", "b")]
    assert compute_draw(participants, previous_pairs=previous, rng=random.Random(5)) is None


def test_result_is_stable_for_fixed_seed():
    participants = [{"id": str(i)} for i in range(8)]
    r1 = compute_draw(participants, rng=random.Random(42))
    r2 = compute_draw(participants, rng=random.Random(42))
    assert r1 == r2
