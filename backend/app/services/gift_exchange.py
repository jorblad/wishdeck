from __future__ import annotations

import random
from typing import Iterable, Optional, Sequence


def compute_draw(
    participants: Sequence[dict],
    previous_pairs: Optional[Iterable[tuple[str, str]]] = None,
    rng: Optional[random.Random] = None,
) -> Optional[dict[str, str]]:
    """Compute a Secret-Santa assignment (a 1:1 derangement) for ``participants``.

    Constraints:
      * A participant never gives to themselves.
      * Two participants that share a non-null ``family`` are never paired
        (in either direction) — e.g. siblings are excluded, cousins (different
        families) are allowed.
      * Any ``(giver, receiver)`` pair present in ``previous_pairs`` (last year's
        draw) is avoided.

    ``participants`` is a sequence of dicts with at least ``id`` and optionally
    ``family``. Returns a mapping ``{giver_id: receiver_id}`` or ``None`` when no
    valid assignment exists under the constraints.
    """
    rng = rng or random.Random()
    ids = [p["id"] for p in participants]
    family = {p["id"]: p.get("family") for p in participants}
    prev = {(g, r) for g, r in (previous_pairs or [])}

    # Pre-compute allowed receivers per giver and bail out early if anyone has
    # none (e.g. a single family covering everyone).
    allowed: dict[str, list[str]] = {}
    for g in ids:
        allowed[g] = [
            r
            for r in ids
            if r != g
            and not _same_family(family[g], family[r])
            and (g, r) not in prev
        ]
        if not allowed[g]:
            return None

    # Most-constrained-variable ordering keeps the backtracking shallow.
    order = sorted(ids, key=lambda g: len(allowed[g]))
    rng.shuffle(order)

    assign: dict[str, str] = {}
    used: set[str] = set()

    def backtrack(i: int) -> bool:
        if i == len(order):
            return True
        giver = order[i]
        candidates = allowed[giver][:]
        rng.shuffle(candidates)
        for receiver in candidates:
            if receiver in used:
                continue
            assign[giver] = receiver
            used.add(receiver)
            if backtrack(i + 1):
                return True
            used.discard(receiver)
            del assign[giver]
        return False

    if not backtrack(0):
        return None
    return assign


def _same_family(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    return a == b


__all__ = ["compute_draw"]
