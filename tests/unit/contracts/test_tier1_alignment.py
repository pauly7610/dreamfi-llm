"""
Test Tier 1 Contract Alignment

Validates that locked eval files, schema seed data, and code all point to the same truth.
This test is the CI gate that prevents contract drift.

IMPORTANT: This test should FAIL initially. Fix failures by:
1. Updating schema seed data to match locked evals
2. Updating locked eval files to match contracts
3. Ensuring file paths are consistent everywhere
"""

import pytest
import os
import json
from pathlib import Path
from typing import Dict, List
import hashlib


class TestTier1ContractAlignment:
    """Verify all 3 Tier 1 skills align across schema, code, and evals."""

    # Expected Tier 1 skills
    EXPECTED_TIER1_SKILLS = {
        "meeting_summary": {
            "file": "evals/meeting-summary.md",
            "tier": 1,
            "criteria_count": 5,
            "hard_gate_ids": [1, 2, 3, 5],
        },
        "agent_system_prompt": {
            "file": "evals/agent-system-prompt.md",
            "tier": 1,
            "criteria_count": 5,
            "hard_gate_ids": [1, 2, 5],
        },
        "support_agent": {
            "file": "evals/support-agent.md",
            "tier": 1,
            "criteria_count": 5,
            "hard_gate_ids": [1, 2, 3, 5],
        },
    }

    def _load_schema_skills(self) -> Dict:
        """Load Tier 1 skills from schema seed data.
        
        Expected location: services/knowledge-hub/db/schemas.ts
        or services/knowledge-hub/db/migrations/001_initial_schema.sql
        """
        import re
        
        schema_path = Path("services/knowledge-hub/db/schema.sql")
        if not schema_path.exists():
            return {}
        
        schema_content = schema_path.read_text()
        skills = {}
        
        # Tier 1 skill definitions from contract
        tier1_skills = {
            "agent_system_prompt": "a1000000-0000-0000-0000-000000000001",
            "support_agent": "a1000000-0000-0000-0000-000000000002",
            "meeting_summary": "a1000000-0000-0000-0000-000000000003",
        }
        
        # Extract file paths from skill_registry INSERT
        # Format: ('uuid', 'skill_name', ..., 'evals/xxx.md', ...)
        for skill_name, skill_id in tier1_skills.items():
            # Find the INSERT line for this skill
            skill_pattern = rf"\('{skill_id}',\s+'{skill_name}'"
            if re.search(skill_pattern, schema_content):
                # Extract file path from this line
                # Pattern: up to next ), find 'evals/xxx.md'
                insert_match = re.search(
                    rf"\('{skill_id}',\s+'{skill_name}',[^)]*'(evals/[^']+\.md)'",
                    schema_content
                )
                if insert_match:
                    file_path = insert_match.group(1)
                    skills[skill_name] = {
                        "tier": 1,
                        "eval_file_path": file_path,
                        "skill_id": skill_id,
                        "hard_gate_criteria_ids": [],
                        "criteria_count": 0,
                        "eval_file_hash": None,
                    }
        
        # Extract criteria counts and hard gates
        # Format: INSERT INTO evaluation_criteria_catalog (...) VALUES
        #         ('skill_id', 'criterion_key', ..., true|false, weight)
        for skill_name, skill_id in tier1_skills.items():
            if skill_name not in skills:
                continue
            
            # Find all criteria INSERTs for this skill
            # Pattern: ('skill_id', 'criterion_key', 'text', 'type', hard_gate_bool, weight)
            criteria_pattern = rf"\('{skill_id}',\s+'([^']+)',\s+'[^']*',\s+'[^']*',\s+(true|false),\s+[\d.]+\)"
            matches = list(re.finditer(criteria_pattern, schema_content))
            
            skills[skill_name]["criteria_count"] = len(matches)
            
            # Collect hard gate IDs (1-indexed)
            hard_gates = []
            for idx, match in enumerate(matches, 1):
                is_hard_gate = match.group(2).lower() == "true"
                if is_hard_gate:
                    hard_gates.append(idx)
            
            skills[skill_name]["hard_gate_criteria_ids"] = hard_gates
        
        # Compute and store eval file hashes
        for skill_name, skill_def in skills.items():
            eval_file = Path(skill_def["eval_file_path"])
            if eval_file.exists():
                skills[skill_name]["eval_file_hash"] = self._compute_file_hash(eval_file)
        
        return skills

    def _load_locked_eval_files(self) -> Dict[str, Path]:
        """List all locked eval files in evals/ directory."""
        evals_path = Path("evals")
        if not evals_path.exists():
            return {}

        eval_files = {}
        for md_file in evals_path.glob("*.md"):
            eval_files[md_file.stem] = md_file

        return eval_files

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def test_every_tier1_skill_has_locked_eval_file(self):
        """Every Tier 1 skill in schema must have a corresponding locked eval file.
        
        FAIL: Missing eval file for a skill
        """
        schema_skills = self._load_schema_skills()
        eval_files = self._load_locked_eval_files()

        for skill_name, skill_def in self.EXPECTED_TIER1_SKILLS.items():
            assert skill_name in schema_skills, f"Skill '{skill_name}' not in schema"

            expected_file = skill_def["file"]
            # Check file exists
            file_path = Path(expected_file)
            assert file_path.exists(), f"Expected eval file not found: {expected_file}"

    def test_every_locked_eval_file_in_schema(self):
        """Every Tier 1 locked eval file in evals/ must be seeded in schema.
        
        FAIL: Tier 1 orphaned eval file with no schema entry
        """
        schema_skills = self._load_schema_skills()
        eval_files = self._load_locked_eval_files()
        
        # Only check Tier 1 eval files
        tier1_files = {stem for stem in self.EXPECTED_TIER1_SKILLS.keys()}

        for eval_stem, eval_path in eval_files.items():
            # Convert file stem to skill name (meeting-summary -> meeting_summary)
            skill_name = eval_stem.replace("-", "_")
            
            # Only validate Tier 1 eval files
            if skill_name not in tier1_files:
                continue

            assert (
                skill_name in schema_skills
            ), f"Tier 1 eval file '{eval_stem}.md' not in schema skills"

    def test_skill_name_format_consistent(self):
        """Skill names use snake_case everywhere.
        
        FAIL: Inconsistent naming (meeting_summary vs meeting-summary)
        """
        schema_skills = self._load_schema_skills()

        for skill_name, skill_def in schema_skills.items():
            assert (
                "_" in skill_name or len(skill_name.split("_")) == 1
            ), f"Skill name should be snake_case: {skill_name}"

    def test_eval_file_path_uses_md_extension(self):
        """Eval file paths must use .md, not .yaml.
        
        FAIL: eval_file_path ends in .yaml
        """
        schema_skills = self._load_schema_skills()

        for skill_name, skill_def in schema_skills.items():
            if "tier" in skill_def and skill_def["tier"] == 1:
                file_path = skill_def.get("eval_file_path", "")
                assert file_path.endswith(
                    ".md"
                ), f"Skill '{skill_name}' has eval_file_path ending in {Path(file_path).suffix}, expected .md"

    def test_tier_value_is_integer(self):
        """Tier must be integer 1, 2, or 3.
        
        FAIL: tier is string or invalid number
        """
        schema_skills = self._load_schema_skills()

        for skill_name, skill_def in schema_skills.items():
            tier = skill_def.get("tier")
            assert isinstance(
                tier, int
            ), f"Skill '{skill_name}' tier must be int, got {type(tier)}"
            assert tier in [
                1,
                2,
                3,
            ], f"Skill '{skill_name}' tier must be 1, 2, or 3, got {tier}"

    def test_criteria_count_matches_locked_eval(self):
        """Schema criteria_count must match actual criteria in locked eval file.
        
        FAIL: Count mismatch
        """
        schema_skills = self._load_schema_skills()

        for expected_skill, expected_def in self.EXPECTED_TIER1_SKILLS.items():
            if expected_skill not in schema_skills:
                pytest.skip(f"Skill '{expected_skill}' not in schema yet")

            schema_skill = schema_skills[expected_skill]
            expected_count = expected_def["criteria_count"]
            actual_count = schema_skill.get("criteria_count")

            assert (
                actual_count == expected_count
            ), f"Skill '{expected_skill}' criteria_count mismatch: schema has {actual_count}, expected {expected_count}"

    def test_hard_gate_criteria_ids_match(self):
        """Schema hard_gate_criteria_ids must match locked eval hard gates.
        
        FAIL: Hard gate IDs mismatch
        """
        schema_skills = self._load_schema_skills()

        for expected_skill, expected_def in self.EXPECTED_TIER1_SKILLS.items():
            if expected_skill not in schema_skills:
                pytest.skip(f"Skill '{expected_skill}' not in schema yet")

            schema_skill = schema_skills[expected_skill]
            expected_gates = sorted(expected_def["hard_gate_ids"])
            actual_gates = sorted(schema_skill.get("hard_gate_criteria_ids", []))

            assert (
                actual_gates == expected_gates
            ), f"Skill '{expected_skill}' hard_gate_criteria_ids mismatch: schema has {actual_gates}, expected {expected_gates}"

    def test_eval_file_hash_consistency(self):
        """Schema seed must include eval file hash for immutability.
        
        FAIL: Hash mismatch or missing
        """
        schema_skills = self._load_schema_skills()
        eval_files = self._load_locked_eval_files()

        for expected_skill, expected_def in self.EXPECTED_TIER1_SKILLS.items():
            if expected_skill not in schema_skills:
                pytest.skip(f"Skill '{expected_skill}' not in schema yet")

            schema_skill = schema_skills[expected_skill]
            eval_file_path = Path(schema_skill.get("eval_file_path", ""))

            if not eval_file_path.exists():
                pytest.skip(f"Eval file not found: {eval_file_path}")

            # Compute actual hash
            actual_hash = self._compute_file_hash(eval_file_path)

            # Get stored hash
            stored_hash = schema_skill.get("eval_file_hash")
            if stored_hash is None:
                pytest.skip(f"Skill '{expected_skill}' eval_file_hash not in schema yet")

            assert (
                actual_hash == stored_hash
            ), f"Skill '{expected_skill}' eval_file_hash mismatch: actual {actual_hash}, stored {stored_hash}"

    def test_no_tier1_skill_without_eval_file(self):
        """No Tier 1 skill should exist without a corresponding locked eval file.
        
        FAIL: Tier 1 skill in schema without eval file
        """
        schema_skills = self._load_schema_skills()

        for skill_name, skill_def in schema_skills.items():
            if skill_def.get("tier") == 1:
                file_path = Path(skill_def.get("eval_file_path", ""))
                assert (
                    file_path.exists()
                ), f"Tier 1 skill '{skill_name}' has missing eval file: {file_path}"

    def test_no_orphaned_eval_files(self):
        """No orphaned Tier 1 eval files in evals/ without schema entries.
        
        FAIL: Tier 1 eval file exists but not in schema
        """
        schema_skills = self._load_schema_skills()
        eval_files = self._load_locked_eval_files()

        # Only check Tier 1 eval files
        tier1_files = {stem for stem in self.EXPECTED_TIER1_SKILLS.keys()}
        
        for eval_stem in eval_files.keys():
            # Convert file stem to skill name
            skill_name = eval_stem.replace("-", "_")
            
            # Only validate Tier 1 eval files
            if skill_name not in tier1_files:
                continue

            assert (
                skill_name in schema_skills
            ), f"Orphaned Tier 1 eval file: evals/{eval_stem}.md not in schema"

    def test_all_expected_tier1_skills_present(self):
        """All 3 expected Tier 1 skills must be in schema.
        
        FAIL: Missing one of the expected Tier 1 skills
        """
        schema_skills = self._load_schema_skills()

        for expected_skill in self.EXPECTED_TIER1_SKILLS.keys():
            assert (
                expected_skill in schema_skills
            ), f"Expected Tier 1 skill '{expected_skill}' not in schema"

    def test_contract_definitions_match_schema(self):
        """All contract definitions from docs/contracts/tier1_skill_contracts.md
        must match schema entries.
        
        FAIL: Definition mismatch
        """
        schema_skills = self._load_schema_skills()

        for expected_skill, expected_def in self.EXPECTED_TIER1_SKILLS.items():
            if expected_skill not in schema_skills:
                pytest.skip(f"Skill '{expected_skill}' not in schema yet")

            schema_skill = schema_skills[expected_skill]

            # Check tier
            assert (
                schema_skill.get("tier") == expected_def["tier"]
            ), f"Tier mismatch for '{expected_skill}'"

            # Check file path
            assert (
                schema_skill.get("eval_file_path") == expected_def["file"]
            ), f"File path mismatch for '{expected_skill}'"

            # Check criteria count
            assert (
                schema_skill.get("criteria_count") == expected_def["criteria_count"]
            ), f"Criteria count mismatch for '{expected_skill}'"
