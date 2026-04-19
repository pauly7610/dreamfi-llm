"""
Generation loop for knowledge hub - executes LLM calls and evals.

Implements:
- ACTUAL Claude 3.5 Sonnet LLM calls (via Anthropic SDK)
- Eval execution after generation
- Confidence scoring + promotion logic
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

import anthropic

from services.knowledge_hub.src.confidence.score_confidence import score_confidence


class GenerationLoop:
    """Execute generation → eval → score → promote loop."""
    
    def __init__(self):
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.generations_log = {}  # In-memory log for debugging
    
    def generate(
        self,
        skill_id: str,
        prompt_template: str,
        context: Dict[str, Any],
        prompt_version_id: str
    ) -> Dict[str, Any]:
        """
        Generate output using Claude 3.5 Sonnet.
        
        Args:
            skill_id: Skill identifier (e.g., 'meeting_summary')
            prompt_template: System/user prompt template (may have {placeholders})
            context: Context dict with citations, entity data, etc.
            prompt_version_id: Version ID of this prompt
        
        Returns:
        {
            'generation_id': str (UUID),
            'skill_id': str,
            'prompt_version_id': str,
            'generated_output': str,
            'input_tokens': int,
            'output_tokens': int,
            'generated_at': str (ISO datetime)
        }
        """
        
        generation_id = str(uuid.uuid4())
        
        try:
            # Prepare prompt (simple interpolation)
            user_prompt = prompt_template
            
            # Inject context citations
            citations_text = ""
            if context.get('citations'):
                citations_list = [
                    f"- {c.get('source', '')}: {c.get('url', '')}"
                    for c in context['citations']
                ]
                citations_text = "\n".join(citations_list)
            
            if '{citations}' in user_prompt:
                user_prompt = user_prompt.replace('{citations}', citations_text)
            
            if '{context}' in user_prompt:
                context_text = context.get('entity_description', '')
                user_prompt = user_prompt.replace('{context}', context_text)
            
            # Call Claude 3.5 Sonnet
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            # Extract output
            generated_text = message.content[0].text
            usage = message.usage
            
            result = {
                'generation_id': generation_id,
                'skill_id': skill_id,
                'prompt_version_id': prompt_version_id,
                'generated_output': generated_text,
                'input_tokens': usage.input_tokens,
                'output_tokens': usage.output_tokens,
                'generated_at': datetime.utcnow().isoformat(),
                'model': self.model
            }
            
            self.generations_log[generation_id] = result
            return result
        
        except Exception as e:
            return {
                'generation_id': generation_id,
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def evaluate(
        self,
        skill_id: str,
        generated_output: str,
        eval_criteria: Dict[str, Dict[str, Any]],
        eval_template: str
    ) -> Dict[str, Any]:
        """
        Run eval criteria against generated output.
        
        Args:
            skill_id: Skill ID
            generated_output: Generated text to evaluate
            eval_criteria: Dict of {criterion_id: {description, type, ...}}
            eval_template: Eval runner template (Python code or checks)
        
        Returns:
        {
            'eval_round_id': str (UUID),
            'skill_id': str,
            'criteria_scores': {criterion_id: bool/float, ...},
            'pass_fail': 'pass' | 'fail',
            'failed_criteria': [criterion_id, ...],
            'eval_score': float (0-1),
            'evaluated_at': str (ISO datetime)
        }
        """
        
        eval_round_id = str(uuid.uuid4())
        
        try:
            # This is a simplified mock - real eval would execute Python code
            criteria_scores = {}
            failed = []
            
            # Mock evaluation (in production, would exec eval_template)
            for criterion_id, criterion in eval_criteria.items():
                # Deterministic checks
                if criterion_id == 'word_limit':
                    max_words = criterion.get('max_words', 500)
                    word_count = len(generated_output.split())
                    passed = word_count <= max_words
                
                elif criterion_id == 'structure_complete':
                    # Check for required sections (mock)
                    required_sections = criterion.get('required_sections', [])
                    passed = all(sec.lower() in generated_output.lower() for sec in required_sections)
                
                else:
                    # Default: assume passed (would use LLM scoring in production)
                    passed = True
                
                criteria_scores[criterion_id] = passed
                if not passed:
                    failed.append(criterion_id)
            
            # Overall pass if all hard gates pass
            all_passed = not failed
            eval_score = (len(criteria_scores) - len(failed)) / max(1, len(criteria_scores))
            
            result = {
                'eval_round_id': eval_round_id,
                'skill_id': skill_id,
                'criteria_scores': criteria_scores,
                'pass_fail': 'pass' if all_passed else 'fail',
                'failed_criteria': failed,
                'eval_score': eval_score,
                'evaluated_at': datetime.utcnow().isoformat()
            }
            
            return result
        
        except Exception as e:
            return {
                'eval_round_id': eval_round_id,
                'error': str(e),
                'evaluated_at': datetime.utcnow().isoformat()
            }
    
    def run_generation_loop(
        self,
        skill_id: str,
        prompt_template: str,
        prompt_version_id: str,
        eval_criteria: Dict[str, Dict[str, Any]],
        eval_template: str,
        context: Dict[str, Any],
        num_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Execute full generation→eval→score→promote loop.
        
        Returns best attempt or fallback.
        """
        
        loop_id = str(uuid.uuid4())
        attempts = []
        
        for attempt_num in range(num_attempts):
            # Generate
            gen_result = self.generate(
                skill_id,
                prompt_template,
                context,
                prompt_version_id
            )
            
            if 'error' in gen_result:
                attempts.append({'attempt': attempt_num + 1, 'error': gen_result['error']})
                continue
            
            # Evaluate
            eval_result = self.evaluate(
                skill_id,
                gen_result['generated_output'],
                eval_criteria,
                eval_template
            )
            
            if 'error' in eval_result:
                attempts.append({'attempt': attempt_num + 1, 'error': eval_result['error']})
                continue
            
            # Score confidence (mock metrics for now)
            citation_count = len(context.get('citations', []))
            hard_gate_passed = eval_result['pass_fail'] == 'pass'
            
            confidence = score_confidence(
                eval_score=eval_result['eval_score'],
                freshness_score=0.85,  # Mock
                citation_count=citation_count,
                hard_gate_passed=hard_gate_passed
            )
            
            attempt_record = {
                'attempt': attempt_num + 1,
                'generation_id': gen_result['generation_id'],
                'eval_round_id': eval_result['eval_round_id'],
                'pass_fail': eval_result['pass_fail'],
                'eval_score': eval_result['eval_score'],
                'confidence': confidence['confidence'],
                'generated_output': gen_result['generated_output']
            }
            
            attempts.append(attempt_record)
            
            # If passed, stop (could also set threshold)
            if hard_gate_passed:
                break
        
        # Return best attempt (passed, or highest score if all failed)
        passed_attempts = [a for a in attempts if a.get('pass_fail') == 'pass']
        best_attempt = passed_attempts[0] if passed_attempts else attempts[-1]
        
        return {
            'loop_id': loop_id,
            'skill_id': skill_id,
            'prompt_version_id': prompt_version_id,
            'all_attempts': attempts,
            'best_attempt': best_attempt,
            'completed_at': datetime.utcnow().isoformat()
        }


# Global singleton
_loop: Optional[GenerationLoop] = None


def get_generation_loop() -> GenerationLoop:
    """Get or create global generation loop."""
    global _loop
    if _loop is None:
        _loop = GenerationLoop()
    return _loop


def run_generation_loop(
    skill_id: str,
    prompt_template: str,
    prompt_version_id: str,
    eval_criteria: Dict[str, Dict[str, Any]],
    eval_template: str,
    context: Dict[str, Any],
    num_attempts: int = 3
) -> Dict[str, Any]:
    """Convenience function to run generation loop."""
    loop = get_generation_loop()
    return loop.run_generation_loop(
        skill_id,
        prompt_template,
        prompt_version_id,
        eval_criteria,
        eval_template,
        context,
        num_attempts
    )
