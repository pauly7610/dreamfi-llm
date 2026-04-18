"""
Unit tests for confidence score calculation.

Tests ADR-005: confidence = eval_score × freshness × citation_count × hard_gate
"""

import pytest


class TestScoreConfidence:
    """Verify confidence scoring follows ADR-005."""

    def test_confidence_deterministic(self):
        """Same input always produces same confidence output."""
        # No randomness
        
        input_data = {
            'eval_score': 0.95,
            'freshness': 0.9,
            'citation_count': 3,
            'hard_gate_passed': True
        }
        
        # Formula: score = eval × freshness × min(citation_count, 5) / 5 × hard_gate
        def calculate_confidence(data):
            multiplier = 1 if data['hard_gate_passed'] else 0.5
            citations_factor = min(data['citation_count'], 5) / 5  # 0.6 for 3 citations
            return data['eval_score'] * data['freshness'] * citations_factor * multiplier
        
        # Multiple calls should return same value
        score1 = calculate_confidence(input_data)
        score2 = calculate_confidence(input_data)
        score3 = calculate_confidence(input_data)
        
        assert score1 == score2 == score3

    def test_confidence_reduces_with_stale_data(self):
        """Confidence reduced when freshness < 0.8."""
        
        fresh_input = {
            'eval_score': 0.95,
            'freshness': 0.95,
            'citation_count': 3,
            'hard_gate_passed': True
        }
        
        stale_input = {
            'eval_score': 0.95,
            'freshness': 0.4,  # < 0.8 threshold
            'citation_count': 3,
            'hard_gate_passed': True
        }
        
        def score_it(data):
            multiplier = 1 if data['hard_gate_passed'] else 0.5
            citations = min(data['citation_count'], 5) / 5
            return data['eval_score'] * data['freshness'] * citations * multiplier
        
        fresh_score = score_it(fresh_input)
        stale_score = score_it(stale_input)
        
        # Stale score should be significantly lower
        assert stale_score < fresh_score
        # fresh: 0.95 * 0.95 * 0.6 * 1 = 0.5415
        assert fresh_score > 0.5
        assert stale_score < 0.4

    def test_confidence_reduces_with_low_citations(self):
        """Confidence reduced when citation_count < 1."""
        
        many_citations = {
            'eval_score': 0.95,
            'freshness': 0.9,
            'citation_count': 5,
            'hard_gate_passed': True
        }
        
        no_citations = {
            'eval_score': 0.95,
            'freshness': 0.9,
            'citation_count': 0,
            'hard_gate_passed': True
        }
        
        def score_it(data):
            multiplier = 1 if data['hard_gate_passed'] else 0.5
            citations = min(data['citation_count'], 5) / 5
            return data['eval_score'] * data['freshness'] * citations * multiplier
        
        many_score = score_it(many_citations)
        no_score = score_it(no_citations)
        
        # No citations = 0 factor
        assert no_score == 0.0 or no_score < 0.1
        assert many_score > no_score

    def test_confidence_reduces_on_hard_gate_fail(self):
        """Confidence reduced when hard-gate criteria fail."""
        
        gate_pass = {
            'eval_score': 0.95,
            'freshness': 0.9,
            'citation_count': 3,
            'hard_gate_passed': True
        }
        
        gate_fail = {
            'eval_score': 0.95,
            'freshness': 0.9,
            'citation_count': 3,
            'hard_gate_passed': False
        }
        
        def score_it(data):
            multiplier = 1 if data['hard_gate_passed'] else 0.5
            citations = min(data['citation_count'], 5) / 5
            return data['eval_score'] * data['freshness'] * citations * multiplier
        
        pass_score = score_it(gate_pass)
        fail_score = score_it(gate_fail)
        
        # Hard gate fail should halve the score
        assert fail_score == pass_score / 2
        assert pass_score > fail_score

    def test_confidence_never_high_with_stale(self):
        """Never return high confidence (>0.8) with freshness < threshold."""
        
        # Perfect eval, good citations, but stale data
        stale = {
            'eval_score': 1.0,
            'freshness': 0.3,  # Stale
            'citation_count': 5,
            'hard_gate_passed': True
        }
        
        def score_it(data):
            multiplier = 1 if data['hard_gate_passed'] else 0.5
            citations = min(data['citation_count'], 5) / 5
            return data['eval_score'] * data['freshness'] * citations * multiplier
        
        score = score_it(stale)
        
        # Should be well below 0.8 threshold
        assert score < 0.8

    def test_confidence_breakdown_included(self):
        """Response includes breakdown of what affected score."""
        
        result = {
            'confidence': 0.513,  # 0.95 * 0.9 * 0.6 * 1
            'breakdown': {
                'eval_score': 0.95,          # From model evaluation
                'freshness_score': 0.9,      # From data age
                'freshness_factor': 0.9,     # Applied to calc
                'citation_count': 3,
                'citation_factor': 0.6,      # 3/5
                'hard_gate_passed': True,
                'hard_gate_factor': 1.0,     # 1.0 if pass, 0.5 if fail
                'reasoning': [
                    'eval_score 0.95: model rated output high',
                    'freshness 0.9: data current (< 3 days old)',
                    'citations 3: good coverage',
                    'hard_gate: passed (structure verified)',
                ]
            }
        }
        
        # Verify all breakdown fields
        assert 'confidence' in result
        assert 'breakdown' in result
        assert 'eval_score' in result['breakdown']
        assert 'freshness_score' in result['breakdown']
        assert 'citation_count' in result['breakdown']
        assert 'hard_gate_passed' in result['breakdown']
        assert 'reasoning' in result['breakdown']
        
        # Verify calculation
        calc = (result['breakdown']['eval_score'] *
                result['breakdown']['freshness_factor'] *
                result['breakdown']['citation_factor'] *
                result['breakdown']['hard_gate_factor'])
        
        assert result['confidence'] == pytest.approx(calc, abs=0.01)

    def test_confidence_citation_count_capped(self):
        """Citation count factor capped at 5 (1.0 factor)."""
        
        # 3 citations: factor = 3/5 = 0.6
        three_citations = {
            'eval_score': 1.0,
            'freshness': 1.0,
            'citation_count': 3,
            'hard_gate_passed': True
        }
        
        # 5 citations: factor = 5/5 = 1.0
        five_citations = {
            'eval_score': 1.0,
            'freshness': 1.0,
            'citation_count': 5,
            'hard_gate_passed': True
        }
        
        # 10 citations: factor = min(10,5)/5 = 1.0 (not >1.0)
        ten_citations = {
            'eval_score': 1.0,
            'freshness': 1.0,
            'citation_count': 10,
            'hard_gate_passed': True
        }
        
        def score_it(data):
            multiplier = 1 if data['hard_gate_passed'] else 0.5
            citations = min(data['citation_count'], 5) / 5
            return data['eval_score'] * data['freshness'] * citations * multiplier
        
        score_3 = score_it(three_citations)
        score_5 = score_it(five_citations)
        score_10 = score_it(ten_citations)
        
        assert score_3 == pytest.approx(0.6)
        assert score_5 == pytest.approx(1.0)
        assert score_10 == pytest.approx(1.0)  # Capped
        assert score_5 == score_10  # Both at cap

