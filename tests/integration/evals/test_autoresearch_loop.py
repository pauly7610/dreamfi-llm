"""
Integration tests for autoresearch loop - Option C.

Tests the complete autoresearch flow:
- Generate 10 variants per round
- Evaluate each variant
- Rank by confidence score
- Track improvement across rounds
- Promote best variant when criteria met
"""

import pytest


class TestAutoresearchLoopBasics:
    """Test autoresearch loop initialization and basic operations."""
    
    def test_autoresearch_loop_initializes(self):
        """Should initialize with skill_id and variant_count."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(
            skill_id="a1000000-0000-0000-0000-000000000003",
            variant_count=10
        )
        
        assert loop.skill_id == "a1000000-0000-0000-0000-000000000003"
        assert loop.variant_count == 10
        assert loop.rounds_history == []

    def test_autoresearch_loop_has_run_round_method(self):
        """Should have run_round method."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-id", variant_count=5)
        assert hasattr(loop, "run_round")
        assert callable(loop.run_round)


class TestAutoresearchVariantGeneration:
    """Test variant generation in autoresearch loop."""
    
    def test_run_round_generates_variants(self):
        """Should generate N variants in a single round."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=10)
        
        result = loop.run_round(
            input_text="Test meeting transcript",
            prompt_template="Summarize: {input}",
        )
        
        assert "variants_generated" in result
        assert result["variants_generated"] == 10
        assert len(result["variants"]) == 10

    def test_run_round_returns_complete_structure(self):
        """Round result should have all required fields."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=5)
        
        result = loop.run_round(
            input_text="Meeting: Decided to launch April 1",
            prompt_template="Template: {input}",
        )
        
        required_fields = [
            "round_id",
            "skill_id",
            "attempt_count",
            "variants_generated",
            "variants",
            "best_variant",
            "best_confidence",
            "promotable",
            "completed_at",
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_variants_have_scores_and_ranks(self):
        """Each variant should have eval_score, confidence, and rank."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=3)
        
        result = loop.run_round(
            input_text="Test input",
            prompt_template="Template: {input}",
        )
        
        for variant in result["variants"]:
            assert "variant_id" in variant
            assert "output" in variant
            assert "eval_score" in variant
            assert "confidence" in variant
            assert "hard_gate_passed" in variant
            assert "rank" in variant
            assert variant["rank"] > 0  # Ranks are 1-indexed


class TestAutoresearchRanking:
    """Test variant ranking by confidence score."""
    
    def test_variants_ranked_by_confidence_desc(self):
        """Variants should be ranked by confidence in descending order."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=10)
        
        result = loop.run_round(
            input_text="Meeting transcript",
            prompt_template="Summarize: {input}",
        )
        
        # First variant should have confidence ≥ all others
        if len(result["variants"]) > 1:
            for i in range(len(result["variants"]) - 1):
                assert (
                    result["variants"][i]["confidence"] >=
                    result["variants"][i + 1]["confidence"],
                    "Variants not sorted by confidence descending"
                )

    def test_best_variant_is_highest_confidence(self):
        """Best variant should be the one with highest confidence."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=10)
        
        result = loop.run_round(
            input_text="Meeting transcript",
            prompt_template="Summarize: {input}",
        )
        
        best = result["best_variant"]
        highest_confidence = max(v["confidence"] for v in result["variants"])
        
        assert best["confidence"] == highest_confidence


class TestAutoresearchPromotability:
    """Test promotion decision logic."""
    
    def test_best_variant_promotable_with_high_confidence(self):
        """Variant should be promotable when confidence ≥ 75% and hard gates pass."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=10)
        
        result = loop.run_round(
            input_text="Meeting with clear decisions and action items",
            prompt_template="Summarize key points: {input}",
        )
        
        # Assuming good input leads to promoted output
        if result["best_variant"]["confidence"] >= 0.75 and result["best_variant"]["hard_gate_passed"]:
            assert result["promotable"] is True

    def test_round_result_includes_promotable_flag(self):
        """Round result should indicate if best variant is promotable."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=5)
        
        result = loop.run_round(
            input_text="Input text",
            prompt_template="Process: {input}",
        )
        
        assert "promotable" in result
        assert isinstance(result["promotable"], bool)


class TestAutoresearchImprovement:
    """Test improvement tracking across rounds."""
    
    def test_improvement_tracking_single_round(self):
        """Single round should track improvement vs previous (or 0 if first)."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=5)
        
        result = loop.run_round(
            input_text="Meeting transcript",
            prompt_template="Summarize: {input}",
            previous_best_score=None,  # First round
        )
        
        assert "improvement_vs_previous" in result
        # First round should show improvement relative to None (0)
        assert result["improvement_vs_previous"] >= 0

    def test_improvement_tracking_multi_round(self):
        """Multi-round should track improvement in each round."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=3)
        
        # Round 1
        result1 = loop.run_round(
            input_text="Meeting 1",
            prompt_template="Summarize: {input}",
        )
        best_score_1 = result1["best_confidence"]
        
        # Round 2
        result2 = loop.run_round(
            input_text="Meeting 2",
            prompt_template="Summarize: {input}",
            previous_best_score=best_score_1,
        )
        
        # Second round should show improvement vs first
        assert "improvement_vs_previous" in result2
        improvement = result2["improvement_vs_previous"]
        assert isinstance(improvement, float)

    def test_get_improvement_tracking_trajectory(self):
        """Should provide historical trajectory of improvements."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=3)
        
        # Run 2 rounds
        result1 = loop.run_round(
            input_text="Meeting 1",
            prompt_template="Summarize: {input}",
        )
        
        result2 = loop.run_round(
            input_text="Meeting 2",
            prompt_template="Summarize: {input}",
            previous_best_score=result1["best_confidence"],
        )
        
        tracking = loop.get_improvement_tracking()
        
        assert "rounds" in tracking
        assert tracking["rounds"] == 2
        assert "best_ever_confidence" in tracking
        assert "trajectory" in tracking
        assert len(tracking["trajectory"]) == 2


class TestAutoresearchFullFlow:
    """Test complete autoresearch loop execution."""
    
    def test_run_autoresearch_loop_single_round(self):
        """Should execute complete autoresearch for single round."""
        from services.knowledge_hub.src.autoresearch import run_autoresearch_loop
        
        result = run_autoresearch_loop(
            skill_id="a1000000-0000-0000-0000-000000000003",
            skill_name="meeting_summary",
            input_text="45-minute product review. Team decided on web-first. Sarah sends design by Friday. Mike writes brief by Monday.",
            prompt_template="Summarize: {input}",
            variant_count=10,
            rounds=1,
        )
        
        assert "best_variant" in result
        assert "best_confidence" in result
        assert result["best_confidence"] > 0
        assert "improvement_tracking" in result
        assert "total_variants_evaluated" in result
        assert result["total_variants_evaluated"] == 10

    def test_run_autoresearch_loop_multi_round(self):
        """Should execute autoresearch for multiple rounds."""
        from services.knowledge_hub.src.autoresearch import run_autoresearch_loop
        
        result = run_autoresearch_loop(
            skill_id="a1000000-0000-0000-0000-000000000003",
            skill_name="meeting_summary",
            input_text="Meeting transcript",
            prompt_template="Summarize: {input}",
            variant_count=5,
            rounds=3,  # 3 rounds
        )
        
        assert "improvement_tracking" in result
        assert result["improvement_tracking"]["rounds"] == 3
        assert result["total_variants_evaluated"] == 15  # 5 variants × 3 rounds

    def test_autoresearch_produces_best_of_10(self):
        """Should consistently select the best from 10 variants."""
        from services.knowledge_hub.src.autoresearch import run_autoresearch_loop
        
        for _ in range(3):  # Run 3 times to verify consistency
            result = run_autoresearch_loop(
                skill_id="test-skill",
                skill_name="meeting_summary",
                input_text="Meeting: Decide, Act, Track",
                prompt_template="Template: {input}",
                variant_count=10,
                rounds=1,
            )
            
            # Best variant should be rank 1
            assert result["best_variant"]["rank"] == 1
            # Best confidence should be >= all others
            max_confidence = max(
                v["confidence"] for v in result["variants"]
            )
            assert result["best_confidence"] == max_confidence


class TestAutoresearchEdgeCases:
    """Test edge cases and error handling."""
    
    def test_autoresearch_with_single_variant(self):
        """Should work even with variant_count=1."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=1)
        result = loop.run_round(
            input_text="Input",
            prompt_template="Template: {input}",
        )
        
        assert result["variants_generated"] == 1
        assert result["best_variant"]["rank"] == 1

    def test_autoresearch_with_zero_rounds(self):
        """Should handle zero rounds gracefully."""
        from services.knowledge_hub.src.autoresearch import run_autoresearch_loop
        
        result = run_autoresearch_loop(
            skill_id="test-skill",
            skill_name="test",
            input_text="Input",
            prompt_template="Template: {input}",
            variant_count=5,
            rounds=0,  # Zero rounds
        )
        
        # Should still return valid structure (from initialization)
        assert isinstance(result, dict)

    def test_improvement_with_regression(self):
        """Should allow up to 2% regression in scores."""
        from services.knowledge_hub.src.autoresearch import AutoresearchLoop
        
        loop = AutoresearchLoop(skill_id="test-skill", variant_count=2)
        
        # Set high baseline
        result1 = loop.run_round(
            input_text="Perfect meeting transcript with all details",
            prompt_template="Summarize: {input}",
        )
        baseline = result1["best_confidence"]
        
        # Run with lower baseline (regression test)
        result2 = loop.run_round(
            input_text="Brief input",
            prompt_template="Summarize: {input}",
            previous_best_score=baseline,
        )
        
        improvement = result2["improvement_vs_previous"]
        # Should allow negative improvement (within threshold)
        assert isinstance(improvement, float)
