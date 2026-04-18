#!/usr/bin/env python3
"""
Autoresearch Results Analyzer
Parses results.log files from autoresearch runs and generates structured analysis.

Usage:
    python analyze_results.py results.log
    python analyze_results.py results.log --output analysis.md --learnings learnings.md
"""

import re
import sys
import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CriterionScore:
    name: str
    passes: int
    total: int

    @property
    def percentage(self) -> float:
        return (self.passes / self.total * 100) if self.total > 0 else 0.0


@dataclass
class Round:
    number: int  # 0 = baseline
    score_passes: int = 0
    score_total: int = 0
    percentage: float = 0.0
    outcome: str = ""  # KEPT, REVERTED, or BASELINE
    change_description: str = ""
    criteria: list = field(default_factory=list)

    @property
    def is_baseline(self) -> bool:
        return self.number == 0


def parse_results_log(filepath: str) -> tuple:
    """Parse a results.log file and return (target_name, list of Round objects)."""
    with open(filepath, "r") as f:
        content = f.read()

    lines = content.strip().split("\n")
    target_name = "Unknown"
    rounds = []

    # Extract target name from header
    for line in lines:
        header_match = re.search(r"AUTORESEARCH RESULTS LOG\s*[-—]+\s*(.+)", line)
        if header_match:
            target_name = header_match.group(1).strip()
            break
        # Also try simpler format
        header_match2 = re.search(r"LOG\s*[-—]\s*(.+)", line)
        if header_match2:
            target_name = header_match2.group(1).strip()
            break

    # Parse baseline
    baseline = Round(number=0, outcome="BASELINE")
    baseline_match = re.search(
        r"BASELINE:\s*(\d+)/(\d+)\s*=\s*([\d.]+)%", content
    )
    if baseline_match:
        baseline.score_passes = int(baseline_match.group(1))
        baseline.score_total = int(baseline_match.group(2))
        baseline.percentage = float(baseline_match.group(3))

    # Parse baseline criteria
    baseline_section = content.split("ROUND")[0] if "ROUND" in content else content
    criteria_pattern = r"C(\d+)\s*\(([^)]+)\):\s*(\d+)/(\d+)\s*\(([\d.]+)%\)"
    for match in re.finditer(criteria_pattern, baseline_section):
        baseline.criteria.append(CriterionScore(
            name=match.group(2).strip(),
            passes=int(match.group(3)),
            total=int(match.group(4)),
        ))
    rounds.append(baseline)

    # Parse each round
    round_pattern = (
        r"ROUND\s+(\d+):\s*(\d+)/(\d+)\s*=\s*([\d.]+)%\s*[-—]+\s*(KEPT|REVERTED)"
    )
    round_sections = re.split(r"(?=ROUND\s+\d+:)", content)

    for section in round_sections:
        round_match = re.search(round_pattern, section)
        if not round_match:
            continue

        r = Round(
            number=int(round_match.group(1)),
            score_passes=int(round_match.group(2)),
            score_total=int(round_match.group(3)),
            percentage=float(round_match.group(4)),
            outcome=round_match.group(5),
        )

        # Extract change description
        change_match = re.search(r"Change:\s*(.+?)(?:\n|$)", section)
        if change_match:
            r.change_description = change_match.group(1).strip()

        # Extract criteria scores
        for match in re.finditer(criteria_pattern, section):
            r.criteria.append(CriterionScore(
                name=match.group(2).strip(),
                passes=int(match.group(3)),
                total=int(match.group(4)),
            ))

        rounds.append(r)

    # Sort by round number
    rounds.sort(key=lambda x: x.number)
    return target_name, rounds


def analyze(target_name: str, rounds: list) -> dict:
    """Analyze parsed rounds and return structured analysis data."""
    baseline = rounds[0]
    experiment_rounds = [r for r in rounds if r.number > 0]
    kept = [r for r in experiment_rounds if r.outcome == "KEPT"]
    reverted = [r for r in experiment_rounds if r.outcome == "REVERTED"]

    final_score = baseline.percentage
    for r in experiment_rounds:
        if r.outcome == "KEPT":
            final_score = r.percentage

    # Find biggest single jump
    biggest_jump = 0
    biggest_jump_round = 0
    prev_score = baseline.percentage
    for r in experiment_rounds:
        if r.outcome == "KEPT":
            jump = r.percentage - prev_score
            if jump > biggest_jump:
                biggest_jump = jump
                biggest_jump_round = r.number
            prev_score = r.percentage

    # Criterion tracking
    criterion_names = []
    if baseline.criteria:
        criterion_names = [c.name for c in baseline.criteria]

    criterion_journey = {}
    for name in criterion_names:
        journey = {"baseline": 0, "final": 0, "rounds_targeted": []}
        for c in baseline.criteria:
            if c.name == name:
                journey["baseline"] = c.percentage
                break
        # Find final score for this criterion
        for r in reversed(experiment_rounds):
            if r.outcome == "KEPT" and r.criteria:
                for c in r.criteria:
                    if c.name == name:
                        journey["final"] = c.percentage
                        break
                if journey["final"] > 0:
                    break
        if journey["final"] == 0:
            journey["final"] = journey["baseline"]
        journey["improvement"] = journey["final"] - journey["baseline"]
        criterion_journey[name] = journey

    # Convergence detection
    convergence_round = None
    for r in experiment_rounds:
        if r.outcome == "KEPT" and r.percentage >= 90:
            convergence_round = r.number
            break

    return {
        "target_name": target_name,
        "baseline_score": baseline.percentage,
        "final_score": final_score,
        "improvement": final_score - baseline.percentage,
        "total_rounds": len(experiment_rounds),
        "kept_count": len(kept),
        "reverted_count": len(reverted),
        "acceptance_rate": (len(kept) / len(experiment_rounds) * 100) if experiment_rounds else 0,
        "biggest_jump": biggest_jump,
        "biggest_jump_round": biggest_jump_round,
        "convergence_round": convergence_round,
        "criterion_journey": criterion_journey,
        "kept_rounds": kept,
        "reverted_rounds": reverted,
        "all_rounds": rounds,
    }


def generate_analysis_md(data: dict) -> str:
    """Generate the full analysis.md content."""
    lines = []
    lines.append(f"# Autoresearch Analysis: {data['target_name']}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Performance Summary
    lines.append("## Performance Summary")
    lines.append("")
    lines.append(
        f"Baseline: {data['baseline_score']:.1f}% → Final: {data['final_score']:.1f}% "
        f"(+{data['improvement']:.1f} percentage points)"
    )
    lines.append(f"Rounds run: {data['total_rounds']}")
    lines.append(
        f"Changes kept: {data['kept_count']}/{data['total_rounds']} "
        f"({data['acceptance_rate']:.0f}% acceptance rate)"
    )
    lines.append(f"Changes reverted: {data['reverted_count']}")

    if data["convergence_round"]:
        lines.append(f"Convergence: Hit 90%+ at round {data['convergence_round']}")
    else:
        lines.append("Convergence: Did not reach 90%")

    if data["biggest_jump"] > 0:
        lines.append(
            f"Biggest single improvement: Round {data['biggest_jump_round']} "
            f"(+{data['biggest_jump']:.1f}pp)"
        )
    lines.append("")

    est_cost_low = data["total_rounds"] * 0.02
    est_cost_high = data["total_rounds"] * 0.05
    lines.append(
        f"Estimated cost: ${est_cost_low:.2f}-${est_cost_high:.2f} "
        f"({data['total_rounds']} rounds)"
    )
    lines.append("")

    # Criterion Analysis
    if data["criterion_journey"]:
        lines.append("## Criterion Analysis")
        lines.append("")

        sorted_criteria = sorted(
            data["criterion_journey"].items(),
            key=lambda x: x[1]["improvement"],
            reverse=True,
        )

        for name, journey in sorted_criteria:
            status = "Strong" if journey["final"] >= 90 else (
                "Moderate" if journey["final"] >= 70 else "Weak"
            )
            lines.append(f"### {name}")
            lines.append(
                f"Baseline: {journey['baseline']:.0f}% → Final: {journey['final']:.0f}% "
                f"(+{journey['improvement']:.0f}pp) — {status}"
            )
            lines.append("")

        # Weakest criterion
        weakest = min(
            data["criterion_journey"].items(), key=lambda x: x[1]["final"]
        )
        lines.append(
            f"Weakest criterion at end: **{weakest[0]}** at {weakest[1]['final']:.0f}%"
        )
        most_improved = max(
            data["criterion_journey"].items(), key=lambda x: x[1]["improvement"]
        )
        lines.append(
            f"Most improved criterion: **{most_improved[0]}** "
            f"(+{most_improved[1]['improvement']:.0f}pp)"
        )
        lines.append("")

    # Changes That Worked
    if data["kept_rounds"]:
        lines.append("## Changes That Worked (sorted by round)")
        lines.append("")
        for r in data["kept_rounds"]:
            desc = r.change_description or "(no description recorded)"
            lines.append(f"- Round {r.number}: {desc} → {r.percentage:.1f}%")
        lines.append("")

    # Changes That Failed
    if data["reverted_rounds"]:
        lines.append("## Changes That Failed")
        lines.append("")
        for r in data["reverted_rounds"]:
            desc = r.change_description or "(no description recorded)"
            lines.append(f"- Round {r.number}: {desc} → dropped to {r.percentage:.1f}% (reverted)")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    if data["final_score"] < 90 and data["criterion_journey"]:
        weakest = min(
            data["criterion_journey"].items(), key=lambda x: x[1]["final"]
        )
        lines.append(
            f"The biggest opportunity is **{weakest[0]}** at {weakest[1]['final']:.0f}%. "
            f"Focus the next loop here."
        )
    elif data["final_score"] >= 90:
        lines.append(
            "Score is above 90%. Remaining improvements will come from edge cases. "
            "Consider whether the eval criteria themselves need updating before running more rounds."
        )

    if data["reverted_count"] > data["kept_count"]:
        lines.append(
            "More changes were reverted than kept. This suggests the skill may be near its "
            "ceiling for these criteria, or the criteria may conflict at the margin."
        )
    lines.append("")

    return "\n".join(lines)


def generate_learnings_md(data: dict) -> str:
    """Generate a portable learnings.md file."""
    lines = []
    lines.append(f"# Learnings from {data['target_name']} Autoresearch Run")
    lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(
        f"# Baseline: {data['baseline_score']:.1f}% → "
        f"Final: {data['final_score']:.1f}% over {data['total_rounds']} rounds"
    )
    lines.append("")

    lines.append("## Rules That Worked")
    if data["kept_rounds"]:
        for r in data["kept_rounds"]:
            desc = r.change_description or "(no description)"
            lines.append(f"- {desc}")
    else:
        lines.append("- (no changes were kept)")
    lines.append("")

    lines.append("## Rules That Hurt")
    if data["reverted_rounds"]:
        for r in data["reverted_rounds"]:
            desc = r.change_description or "(no description)"
            lines.append(f"- {desc} (dropped score to {r.percentage:.1f}%)")
    else:
        lines.append("- (no changes were reverted)")
    lines.append("")

    lines.append("## Patterns for Other Skills")
    lines.append("- (review the kept changes above and identify which patterns")
    lines.append("  would apply to your other skills, prompts, and templates)")
    lines.append("")

    lines.append("## Key Stats")
    lines.append(f"- Improvement: +{data['improvement']:.1f} percentage points")
    lines.append(f"- Acceptance rate: {data['acceptance_rate']:.0f}%")
    if data["biggest_jump"] > 0:
        lines.append(
            f"- Biggest single jump: +{data['biggest_jump']:.1f}pp (Round {data['biggest_jump_round']})"
        )
    lines.append("")

    return "\n".join(lines)


def print_terminal_summary(data: dict):
    """Print a quick summary to terminal."""
    print()
    print(f"  {'='*50}")
    print(f"  AUTORESEARCH ANALYSIS: {data['target_name']}")
    print(f"  {'='*50}")
    print()
    print(f"  {data['baseline_score']:.1f}% → {data['final_score']:.1f}%  (+{data['improvement']:.1f}pp)")
    print(f"  {data['total_rounds']} rounds | {data['kept_count']} kept | {data['reverted_count']} reverted")
    if data["convergence_round"]:
        print(f"  Converged at round {data['convergence_round']}")
    print()

    if data["criterion_journey"]:
        print("  Criterion breakdown:")
        for name, journey in sorted(
            data["criterion_journey"].items(),
            key=lambda x: x[1]["final"],
        ):
            arrow = "↑" if journey["improvement"] > 0 else ("↓" if journey["improvement"] < 0 else "→")
            print(
                f"    {name}: {journey['baseline']:.0f}% → {journey['final']:.0f}% {arrow}"
            )
    print()


def main():
    parser = argparse.ArgumentParser(description="Analyze autoresearch results.log files")
    parser.add_argument("logfile", help="Path to results.log")
    parser.add_argument("--output", "-o", default="analysis.md", help="Output analysis file")
    parser.add_argument("--learnings", "-l", default="learnings.md", help="Output learnings file")
    parser.add_argument("--quiet", "-q", action="store_true", help="Skip terminal output")
    args = parser.parse_args()

    if not Path(args.logfile).exists():
        print(f"Error: {args.logfile} not found")
        sys.exit(1)

    target_name, rounds = parse_results_log(args.logfile)

    if len(rounds) < 1:
        print("Error: Could not parse any rounds from the log file")
        sys.exit(1)

    data = analyze(target_name, rounds)

    if not args.quiet:
        print_terminal_summary(data)

    analysis = generate_analysis_md(data)
    with open(args.output, "w") as f:
        f.write(analysis)
    print(f"  Analysis written to: {args.output}")

    learnings = generate_learnings_md(data)
    with open(args.learnings, "w") as f:
        f.write(learnings)
    print(f"  Learnings written to: {args.learnings}")
    print()


if __name__ == "__main__":
    main()
