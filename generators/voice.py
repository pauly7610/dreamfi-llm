"""
DreamFi Voice and Style Rules
Defines tone, formatting, banned phrases, and required elements
for all generated documents.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Voice guidelines — shared across every document type
# ---------------------------------------------------------------------------

VOICE_GUIDELINES: dict[str, Any] = {
    "tone": {
        "primary": "clear, direct, and concise",
        "register": "professional but approachable — no corporate fluff",
        "audience": "internal teams (product, engineering, compliance, ops)",
        "rules": [
            "Lead with the insight, not the setup.",
            "Use active voice. Say who does what.",
            "Write at an 8th-grade reading level — no jargon unless domain-specific and defined.",
            "Every sentence must earn its place. Cut filler.",
            "Quantify where possible — replace vague words with numbers.",
        ],
    },
    "formatting": {
        "rules": [
            "Use tables instead of long paragraphs when comparing options or listing attributes.",
            "Lead every document with the hypothesis or core question.",
            "Use bullet lists for 3+ related items.",
            "Bold key terms on first use, then use them without emphasis.",
            "Keep paragraphs to 3 sentences max.",
            "Use headers (H2/H3) to create scannable structure.",
            "Include a TL;DR section at the top for documents over 500 words.",
        ],
    },
    "banned_phrases": [
        "leverage",
        "synergy",
        "synergize",
        "circle back",
        "move the needle",
        "low-hanging fruit",
        "boil the ocean",
        "paradigm shift",
        "best-in-class",
        "world-class",
        "holistic approach",
        "going forward",
        "at the end of the day",
        "deep dive",  # use "analysis" or "investigation"
        "touch base",
        "take offline",
        "bandwidth",  # when referring to people, not networks
        "thought leader",
        "disruptive",
        "scalable solution",  # say what scales and how
        "innovative",  # show, don't tell
        "robust",  # be specific about what makes it strong
        "seamless",  # describe the actual integration
        "cutting-edge",
        "game-changer",
        "mission-critical",  # say why it matters instead
        "value-add",
        "stakeholder alignment",  # say who needs to agree on what
    ],
    "required_elements": [
        "hypothesis",
        "success_metrics",
        "risks",
    ],
}

# ---------------------------------------------------------------------------
# Per-document-type section requirements
# ---------------------------------------------------------------------------

FORMAT_RULES: dict[str, dict[str, Any]] = {
    "technical_prd": {
        "required_sections": [
            "Hypothesis",
            "Problem Statement",
            "Proposed Approach",
            "System Components",
            "API Changes",
            "Data Model Changes",
            "Edge Cases",
            "Success Metrics",
            "Dependencies",
            "Risks",
        ],
        "notes": "Must include system component table and API change details.",
    },
    "business_prd": {
        "required_sections": [
            "Hypothesis",
            "Business Context",
            "Market Opportunity",
            "Target Users",
            "Revenue Impact",
            "Proposed Solution",
            "Success Metrics",
            "Stakeholders",
            "Timeline",
            "Risks",
        ],
        "notes": "Must include revenue projection table and stakeholder RACI.",
    },
    "risk_brd": {
        "required_sections": [
            "Vendor Overview",
            "Service Type & Data Categories",
            "Regulatory Frameworks",
            "Security Controls",
            "Risk Assessment",
            "Monitoring Approach",
            "Data Retention",
            "Exit Strategy",
        ],
        "notes": "Must include risk matrix table and compliance checklist.",
    },
    "sponsor_bank": {
        "required_sections": [
            "Bank Overview",
            "Integration Scope",
            "Regulatory Requirements",
            "Transaction Types",
            "Settlement Approach",
            "Compliance Controls",
            "SLA Requirements",
            "Reporting Requirements",
            "Incident Response",
        ],
        "notes": "Must include SLA table and incident severity matrix.",
    },
    "discovery": {
        "required_sections": [
            "Problem Area",
            "Research Questions",
            "User Segments",
            "Data Sources",
            "Hypotheses",
            "Evidence Summary",
            "Opportunity Size",
            "Recommendation",
        ],
        "notes": "Must include evidence-strength table and recommendation matrix.",
    },
    "epic_builder": {
        "required_sections": [
            "Epic Summary",
            "Objective",
            "User Stories",
            "Acceptance Criteria",
            "Technical Considerations",
            "Dependencies",
            "Estimation",
        ],
        "notes": "User stories must follow 'As a [user], I want [action] so that [outcome]' format.",
    },
}


# ---------------------------------------------------------------------------
# Voice-check function
# ---------------------------------------------------------------------------

def apply_voice_check(content: str) -> dict[str, Any]:
    """
    Check whether *content* follows DreamFi voice rules.

    Returns a dict with:
        passed: bool — True if all checks pass
        results: list of dicts with rule, passed, details
    """
    results: list[dict[str, Any]] = []
    content_lower = content.lower()

    # 1. Banned-phrase check
    found_banned: list[str] = []
    for phrase in VOICE_GUIDELINES["banned_phrases"]:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, content_lower):
            found_banned.append(phrase)
    results.append({
        "rule": "no_banned_phrases",
        "passed": len(found_banned) == 0,
        "details": f"Found banned phrases: {', '.join(found_banned)}" if found_banned else "No banned phrases detected.",
    })

    # 2. Hypothesis-first check (should appear in first 500 chars)
    has_hypothesis_early = (
        "hypothesis" in content_lower[:500]
        or "## hypothesis" in content_lower[:500]
        or "# hypothesis" in content_lower[:500]
    )
    results.append({
        "rule": "hypothesis_first",
        "passed": has_hypothesis_early,
        "details": "Hypothesis appears near the top." if has_hypothesis_early else "Hypothesis not found in the first 500 characters.",
    })

    # 3. Active-voice heuristic — flag excessive passive constructions
    passive_patterns = [
        r"\bis been\b",
        r"\bwas \w+ed\b",
        r"\bwere \w+ed\b",
        r"\bbeing \w+ed\b",
        r"\bhas been \w+ed\b",
        r"\bhave been \w+ed\b",
        r"\bwill be \w+ed\b",
    ]
    passive_count = sum(len(re.findall(p, content_lower)) for p in passive_patterns)
    word_count = len(content.split())
    passive_ratio = passive_count / max(word_count, 1)
    passive_ok = passive_ratio < 0.03  # fewer than 3% passive constructions
    results.append({
        "rule": "active_voice",
        "passed": passive_ok,
        "details": f"Passive constructions: {passive_count} ({passive_ratio:.1%} of words)."
                   + ("" if passive_ok else " Consider rewriting passive sentences."),
    })

    # 4. Paragraph-length check — no paragraph over 4 sentences
    paragraphs = re.split(r"\n\s*\n", content)
    long_paragraphs = 0
    for para in paragraphs:
        stripped = para.strip()
        if stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("-"):
            continue  # skip headers, tables, lists
        sentences = re.split(r"[.!?]+\s", stripped)
        if len(sentences) > 4:
            long_paragraphs += 1
    results.append({
        "rule": "short_paragraphs",
        "passed": long_paragraphs == 0,
        "details": f"{long_paragraphs} paragraph(s) exceed 4 sentences." if long_paragraphs else "All paragraphs are concise.",
    })

    # 5. Tables-over-paragraphs heuristic — document should include at least one table
    has_table = "|" in content and "---" in content
    results.append({
        "rule": "uses_tables",
        "passed": has_table,
        "details": "Document includes table(s)." if has_table else "No tables detected. Consider using tables for structured data.",
    })

    # 6. Success-metrics check
    has_metrics = "success metric" in content_lower or "success criteria" in content_lower or "## success" in content_lower
    results.append({
        "rule": "has_success_metrics",
        "passed": has_metrics,
        "details": "Success metrics section found." if has_metrics else "No success metrics section detected.",
    })

    # 7. Risks section check
    has_risks = "## risk" in content_lower or "### risk" in content_lower or "# risk" in content_lower
    results.append({
        "rule": "has_risks_section",
        "passed": has_risks,
        "details": "Risks section found." if has_risks else "No risks section detected.",
    })

    overall = all(r["passed"] for r in results)

    return {
        "passed": overall,
        "results": results,
    }
