"""
Gold examples registry - captures perfect outputs for few-shot prompting.

Implements:
- Capture perfect outputs (all hard gates pass)
- Storage + retrieval by skill + scenario
- Few-shot context injection into generation prompts
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json


class GoldExampleRegistry:
    """Manages gold examples for skills."""
    
    def __init__(self):
        # In-memory registry (would be DB table in production)
        self.examples = {}  # key: (skill_id, scenario_type) -> list of examples
    
    def capture_gold_example(
        self,
        skill_id: str,
        scenario_type: str,
        input_context: Dict[str, Any],
        output_text: str,
        eval_result: Dict[str, Any],
        prompt_version_id: str
    ) -> Dict[str, Any]:
        """
        Capture a perfect output as a gold example.
        
        Args:
            skill_id: Skill ID (e.g., 'meeting_summary')
            scenario_type: Scenario classification (e.g., 'product_review', 'engineering_retro')
            input_context: Input context that produced this output
            output_text: Generated output
            eval_result: Eval metrics (must be all pass)
            prompt_version_id: Version ID of prompt used
        
        Returns:
        {
            'gold_example_id': str (UUID),
            'skill_id': str,
            'scenario_type': str,
            'output_text': str,
            'score_percent': float (0-100),
            'passed_all_flag': bool,
            'captured_at': str (ISO datetime)
        }
        """
        
        # Only capture if all criteria passed
        if eval_result.get('pass_fail') != 'pass':
            return {
                'captured': False,
                'reason': 'Output did not pass all criteria'
            }
        
        gold_example_id = str(uuid.uuid4())
        
        # Compute score
        eval_score = eval_result.get('eval_score', 0.0)
        score_percent = eval_score * 100
        
        example = {
            'gold_example_id': gold_example_id,
            'skill_id': skill_id,
            'scenario_type': scenario_type,
            'input_context': input_context,
            'output_text': output_text,
            'score_percent': score_percent,
            'passed_all_flag': True,
            'prompt_version_id': prompt_version_id,
            'captured_at': datetime.utcnow().isoformat()
        }
        
        # Store in registry
        key = (skill_id, scenario_type)
        if key not in self.examples:
            self.examples[key] = []
        self.examples[key].append(example)
        
        return {
            'captured': True,
            'gold_example_id': gold_example_id,
            'skill_id': skill_id,
            'scenario_type': scenario_type
        }
    
    def retrieve_gold_examples(
        self,
        skill_id: str,
        scenario_type: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve gold examples for a skill/scenario.
        
        Returns up to `limit` best examples (sorted by score).
        """
        
        examples = []
        
        if scenario_type:
            # Specific scenario
            key = (skill_id, scenario_type)
            examples = self.examples.get(key, [])
        else:
            # All scenarios for skill
            for (s_id, _), exs in self.examples.items():
                if s_id == skill_id:
                    examples.extend(exs)
        
        # Sort by score descending, take limit
        examples.sort(key=lambda e: e.get('score_percent', 0), reverse=True)
        return examples[:limit]
    
    def build_few_shot_context(
        self,
        skill_id: str,
        scenario_type: Optional[str] = None,
        num_examples: int = 2
    ) -> str:
        """
        Build few-shot examples string for prompt injection.
        
        Returns formatted examples for inclusion in prompt.
        """
        
        examples = self.retrieve_gold_examples(skill_id, scenario_type, num_examples)
        
        if not examples:
            return ""
        
        few_shot = "## Examples of Perfect Outputs\n\n"
        
        for idx, example in enumerate(examples, 1):
            few_shot += f"### Example {idx} ({example.get('scenario_type', 'general')})\n"
            few_shot += f"**Input Context:** {json.dumps(example.get('input_context', {}), indent=2)}\n\n"
            few_shot += f"**Output:**\n{example.get('output_text', '')}\n\n"
            few_shot += f"📊 Score: {example.get('score_percent', 0):.0f}%\n\n"
        
        return few_shot


def capture_gold_example(
    skill_id: str,
    scenario_type: str,
    input_context: Dict[str, Any],
    output_text: str,
    eval_result: Dict[str, Any],
    prompt_version_id: str,
    registry: Optional[GoldExampleRegistry] = None
) -> Dict[str, Any]:
    """Convenience function."""
    if registry is None:
        registry = _get_global_registry()
    return registry.capture_gold_example(
        skill_id,
        scenario_type,
        input_context,
        output_text,
        eval_result,
        prompt_version_id
    )


def retrieve_gold_examples(
    skill_id: str,
    scenario_type: Optional[str] = None,
    limit: int = 3,
    registry: Optional[GoldExampleRegistry] = None
) -> List[Dict[str, Any]]:
    """Convenience function."""
    if registry is None:
        registry = _get_global_registry()
    return registry.retrieve_gold_examples(skill_id, scenario_type, limit)


# Global registry
_global_registry: Optional[GoldExampleRegistry] = None


def _get_global_registry() -> GoldExampleRegistry:
    """Get or create global gold example registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = GoldExampleRegistry()
    return _global_registry
