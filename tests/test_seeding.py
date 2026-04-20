from dreamfi.db.models import GoldExample
from dreamfi.trust.seeding import missing_regression_examples


def test_reports_deficit_when_skill_has_fewer_than_five_regression_examples() -> None:
    examples = [
        GoldExample(gold_id="g1", workspace_id="w1", skill_id="planning_weekly_brief", role="regression"),
        GoldExample(gold_id="g2", workspace_id="w1", skill_id="planning_weekly_brief", role="regression"),
    ]

    deficits = missing_regression_examples(examples, minimum_per_skill=5)

    assert deficits == {"planning_weekly_brief": 3}
