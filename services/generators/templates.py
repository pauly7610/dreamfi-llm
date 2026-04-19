import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

log = logging.getLogger(__name__)


class TemplateEngine:
    def __init__(self, templates_path: Optional[Path] = None):
        if templates_path is None:
            templates_path = Path(__file__).parent.parent.parent / "config" / "generator_templates.yaml"
        self.templates_path = templates_path
        self._templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        try:
            with open(self.templates_path, "r") as f:
                data = yaml.safe_load(f) or {}
                return data.get("templates", data)
        except FileNotFoundError:
            log.warning(f"Templates file not found: {self.templates_path}")
            return {}

    def get_template(self, template_id: str) -> Dict[str, Any]:
        if template_id not in self._templates:
            raise ValueError(f"Template not found: {template_id}")
        return self._templates[template_id]

    def get_sections(self, template_id: str) -> List[str]:
        template = self.get_template(template_id)
        return template.get("section_order", [])

    def render(self, template_id: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        template = self.get_template(template_id)
        sections = {}

        section_order = template.get("section_order", [])
        section_templates = template.get("sections", {})

        for section_name in section_order:
            if section_name not in section_templates:
                continue
            section_template = section_templates[section_name]
            sections[section_name] = {
                "template": section_template.get("template", ""),
                "prompt_hint": section_template.get("prompt_hint", ""),
                "required": section_template.get("required", False),
                "word_count_target": section_template.get("word_count_target", 0),
            }

        return {
            "template_id": template_id,
            "name": template.get("name", ""),
            "sections": sections,
            "voice_guide": template.get("voice_guide", ""),
            "required_fields": template.get("required_fields", []),
        }

    def apply_voice(self, content: str, voice_guide: str) -> str:
        banned_phrases = [
            "leverage", "synergy", "synergize", "circle back",
            "move the needle", "low-hanging fruit", "boil the ocean",
            "paradigm shift", "best-in-class", "world-class",
            "holistic approach", "going forward", "at the end of the day",
            "deep dive", "touch base", "take offline", "bandwidth",
            "thought leader", "disruptive", "scalable solution",
            "innovative", "robust", "seamless", "cutting-edge",
            "game-changer", "mission-critical", "value-add",
            "stakeholder alignment"
        ]

        for phrase in banned_phrases:
            pattern = f"\\b{phrase}\\b"
            import re
            if re.search(pattern, content, re.IGNORECASE):
                log.warning(f"Banned phrase detected: {phrase}")

        return content

    def validate_output(self, output_dict: Dict[str, Any], template_id: str) -> tuple[bool, List[str]]:
        template = self.get_template(template_id)
        required_sections = template.get("required_sections", [])
        errors = []

        for section in required_sections:
            if section not in output_dict or not output_dict[section]:
                errors.append(f"Missing required section: {section}")

        content = "\n".join(str(v) for v in output_dict.values())
        if len(content) < 500:
            errors.append("Output too short (minimum 500 characters)")

        return len(errors) == 0, errors

    def list_templates(self) -> List[str]:
        return list(self._templates.keys())

    def get_template_metadata(self, template_id: str) -> Dict[str, Any]:
        template = self.get_template(template_id)
        return {
            "name": template.get("name", ""),
            "description": template.get("description", ""),
            "required_fields": template.get("required_fields", []),
            "required_sections": template.get("required_sections", []),
            "voice_guide": template.get("voice_guide", ""),
        }
