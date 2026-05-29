from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from dreamfi.db.models import GoldExample


def missing_regression_examples(
    examples: Iterable[GoldExample],
    minimum_per_skill: int = 5,
    *,
    all_skill_ids: Iterable[str] | None = None,
) -> dict[str, int]:
    """Return per-skill deficit to reach minimum regression examples.

    When ``all_skill_ids`` is provided, any skill in that set with zero
    regression examples is reported with the full minimum as its deficit.
    Without ``all_skill_ids`` the function can only see skills that already
    have at least one regression example, which silently hides zero-count
    skills.
    """
    counts: dict[str, int] = defaultdict(int)
    for ex in examples:
        if ex.role == "regression":
            counts[ex.skill_id] += 1

    deficits: dict[str, int] = {}
    skill_ids = set(counts.keys())
    if all_skill_ids is not None:
        skill_ids |= set(all_skill_ids)

    for skill_id in skill_ids:
        count = counts.get(skill_id, 0)
        if count < minimum_per_skill:
            deficits[skill_id] = minimum_per_skill - count

    return deficits
