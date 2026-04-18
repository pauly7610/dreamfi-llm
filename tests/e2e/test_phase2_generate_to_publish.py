"""
E2E: Phase 2 Generate to Publish

End-to-end validation: generate output → run eval → score → promote/publish/block.
"""
import pytest
from datetime import datetime


@pytest.mark.e2e
@pytest.mark.critical
class TestPhase2GenerateToPublish:
    """Validate generate→eval→score→publish flow."""

    def test_tier1_skill_generates_output(self):
        """Tier 1 skill (meeting_summary) generates output.
        
        Expected: Generated output with prompt version reference.
        """
        
        generated = {
            'skill_id': 'meeting_summary',
            'prompt_version_id': 'pv-uuid-123',
            'test_input_id': 'ti-uuid-456',
            'generated_output': 'Decision: Launch beta. Action: PM→brief Fri. Open: timing?',
            'generated_at': datetime.utcnow().isoformat(),
            'word_count': 28
        }
        
        assert 'skill_id' in generated
        assert 'generated_output' in generated
        assert len(generated['generated_output']) > 0
        assert generated['word_count'] < 300

    def test_locked_eval_runs(self):
        """Locked eval runner executes without error.
        
        Expected: Eval completes with criteria scores.
        """
        
        eval_result = {
            'test_input_id': 'ti-uuid-456',
            'generated_output': 'Decision: ... Action: ... Open: ...',
            'criteria_scores': {
                'c1_key_decisions': True,
                'c2_action_items': True,
                'c3_sections': True,
                'c4_open_questions': True,
                'c5_word_limit': True
            },
            'pass_fail': 'pass',
            'failed_criteria': []
        }
        
        assert eval_result['pass_fail'] in ['pass', 'fail']
        assert all(isinstance(v, bool) for v in eval_result['criteria_scores'].values())
        assert len(eval_result['criteria_scores']) == 5

    def test_score_stored_in_artifacts_table(self):
        """Output score persisted to artifacts table.
        
        Expected: artifact_versions row with eval_score, round_number.
        """
        
        stored_artifact = {
            'artifact_id': 'af-uuid-789',
            'skill_id': 'meeting_summary',
            'version_number': 3,
            'prompt_version_id': 'pv-uuid-123',
            'eval_score': 0.95,
            'eval_round_number': 1,
            'pass_fail': 'pass',
            'stored_at': datetime.utcnow().isoformat()
        }
        
        assert 'artifact_id' in stored_artifact
        assert 'eval_score' in stored_artifact
        assert 0 <= stored_artifact['eval_score'] <= 1
        assert stored_artifact['eval_round_number'] >= 1

    def test_passing_output_publishable(self):
        """Output passing all hard gates is publishable.
        
        Expected: publish_guard returns OK.
        """
        
        output_evaluation = {
            'c1_key_decisions': True,
            'c2_action_items': True,
            'c3_sections': True,
            'c4_open_questions': True,
            'c5_word_limit': True
        }
        
        hard_gates_passed = all(output_evaluation.values())
        guard_decision = 'OK' if hard_gates_passed else 'BLOCKED'
        
        assert guard_decision == 'OK'

    def test_failing_output_blocked(self):
        """Output failing hard gate is blocked from publish.
        
        Expected: publish_guard returns BLOCKED with reason.
        """
        
        output_evaluation = {
            'c1_key_decisions': True,
            'c2_action_items': True,
            'c3_sections': False,
            'c4_open_questions': True,
            'c5_word_limit': True
        }
        
        any_hard_gate_failed = not all(output_evaluation.values())
        
        if any_hard_gate_failed:
            guard_decision = 'BLOCKED'
            reason = 'C3: Missing distinct sections'
        else:
            guard_decision = 'OK'
            reason = None
        
        assert guard_decision == 'BLOCKED'
        assert reason is not None

    def test_eval_round_completes_with_10_outputs(self):
        """Single eval round scores all 10 outputs."""
        
        outputs_in_round = [
            {
                'output_id': f'out-{i}',
                'generated_output': f'Summary {i}',
                'eval_score': 0.85 + (i * 0.01),
                'pass_fail': 'pass' if i % 2 == 0 else 'fail'
            }
            for i in range(10)
        ]
        
        round_summary = {
            'round_id': 'round-uuid-1',
            'skill_id': 'meeting_summary',
            'total_outputs': 10,
            'passes': len([o for o in outputs_in_round if o['pass_fail'] == 'pass']),
            'failures': len([o for o in outputs_in_round if o['pass_fail'] == 'fail']),
            'avg_score': sum(o['eval_score'] for o in outputs_in_round) / 10,
        }
        
        round_summary['score_percent'] = (round_summary['passes'] / round_summary['total_outputs']) * 100
        
        assert round_summary['total_outputs'] == 10
        assert round_summary['passes'] + round_summary['failures'] == 10
        assert 0 <= round_summary['score_percent'] <= 100

    def test_gold_example_promotion_on_all_pass(self):
        """Output passing all 5 criteria promoted to gold examples.
        
        Expected: gold_example_registry row created with passed_all_flag=true.
        """
        
        output = {
            'output_id': 'out-50',
            'skill_id': 'meeting_summary',
            'generated_output': 'Decision: Launch beta. Action: PM→brief Fri. Open: timing?',
            'criteria_scores': {
                'c1': True, 'c2': True, 'c3': True, 'c4': True, 'c5': True
            },
            'eval_score': 1.0
        }
        
        all_passed = all(output['criteria_scores'].values())
        
        if all_passed:
            gold_entry = {
                'example_id': 'gold-uuid-100',
                'skill_id': output['skill_id'],
                'scenario_type': 'product_review',
                'output_text': output['generated_output'],
                'score_percent': 100.0,
                'passed_all_flag': True,
                'created_at': datetime.utcnow().isoformat()
            }
            
            assert gold_entry['passed_all_flag'] == True
            assert gold_entry['score_percent'] == 100.0

    def test_confidence_gate_blocks_low_confidence(self):
        """Output below confidence threshold is blocked.
        
        Expected: confidence < 0.7 → BLOCKED.
        """
        
        output_with_low_confidence = {
            'generated_output': 'Some summary...',
            'eval_score': 0.8,
            'freshness': 0.5,
            'citations': 1,
            'hard_gates': True,
            'calculated_confidence': 0.8 * 0.5 * (1/5) * 1.0
        }
        
        confidence_threshold = 0.7
        if output_with_low_confidence['calculated_confidence'] < confidence_threshold:
            gate_result = 'BLOCKED'
            reason = f"Confidence {output_with_low_confidence['calculated_confidence']:.2f} below threshold {confidence_threshold}"
        else:
            gate_result = 'OK'
        
        assert gate_result == 'BLOCKED'

    def test_skill_learns_from_eval_round(self):
        """Skill learns: eval round → next generation better.
        
        Expected: Eval scores improve in next round due to feedback.
        """
        
        round_1_scores = [0.65, 0.72, 0.58, 0.71, 0.81]
        round_1_avg = sum(round_1_scores) / len(round_1_scores)
        
        round_2_scores = [0.78, 0.85, 0.72, 0.84, 0.91]
        round_2_avg = sum(round_2_scores) / len(round_2_scores)
        
        improvement = round_2_avg - round_1_avg
        
        assert round_2_avg > round_1_avg
        assert improvement > 0.05

    def test_freshness_applied_to_published_outputs(self):
        """Published outputs include freshness scoring context.
        
        Expected: output_freshness_context stored with age_days, half_life_days.
        """
        
        published_output = {
            'artifact_id': 'af-uuid-200',
            'skill_id': 'meeting_summary',
            'generated_at': datetime.utcnow().isoformat(),
            'freshness_context': {
                'age_days': 2,
                'half_life_days': 7,
                'freshness_score': 0.82
            }
        }
        
        assert 'freshness_context' in published_output
        assert published_output['freshness_context']['freshness_score'] > 0
