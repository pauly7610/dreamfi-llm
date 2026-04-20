from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from dreamfi.db.models import GoldExample


def missing_regression_examples(examples: Iterable[GoldExample], minimum_per_skill: int = 5) -> dict[str, int]:
    """Return per-skill deficit to reach minimum regression examples."""
    counts: dict[str, int] = defaultdict(int)
    for ex in examples:
        if ex.role == "regression":
            counts[ex.skill_id] += 1

    deficits: dict[str, int] = {}
    for skill_id, count in counts.items():
        if count < minimum_per_skill:
            deficits[skill_id] = minimum_per_skill - count

    return deficits
