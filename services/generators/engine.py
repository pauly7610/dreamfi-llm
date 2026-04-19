import logging
import httpx
from typing import Dict, Any, Optional
import anthropic
from config import config as _cfg
from services.generators.templates import TemplateEngine
from services.generators.jira_helper import JiraHelper

log = logging.getLogger(__name__)


class GeneratorEngine:
    def __init__(self, templates_path: Optional[str] = None):
        self.template_engine = TemplateEngine(templates_path)
        self.anthropic_client = anthropic.Anthropic(api_key=_cfg.anthropic.api_key)
        self.model = _cfg.anthropic.model
        self.knowledge_hub_url = "http://localhost:3000/api/v1"
        self.jira_helper = JiraHelper()

    def _retrieve_knowledge_context(self, query: str) -> Optional[Dict[str, Any]]:
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"{self.knowledge_hub_url}/retrieve",
                    params={"query": query, "limit": 5}
                )
                if response.status_code == 200:
                    return response.json()
                log.warning(f"Knowledge Hub returned {response.status_code}")
                return None
        except Exception as e:
            log.error(f"Failed to retrieve knowledge context: {e}")
            return None

    def _build_system_prompt(self, template_id: str) -> str:
        template = self.template_engine.get_template(template_id)
        voice_guide = template.get("voice_guide", "")
        instructions = template.get("system_instructions", "")
        return f"{voice_guide}\n\n{instructions}"

    def _build_user_prompt(self, form_data: Dict[str, Any], template_id: str) -> str:
        template = self.template_engine.get_template(template_id)
        prompt_template = template.get("user_prompt_template", "")

        prompt = prompt_template
        for key, value in form_data.items():
            placeholder = f"{{{{{key}}}}}"
            if isinstance(value, list):
                prompt = prompt.replace(placeholder, "\n".join(f"- {v}" for v in value))
            else:
                prompt = prompt.replace(placeholder, str(value))

        return prompt

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        response = self.anthropic_client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text

    def _parse_sections_from_response(self, response_text: str, template_id: str) -> Dict[str, str]:
        template = self.template_engine.get_template(template_id)
        section_order = template.get("section_order", [])

        sections = {}
        lines = response_text.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            for section in section_order:
                if section.lower() in line.lower() and any(c in line for c in ["##", "###", "**", "--"]):
                    if current_section:
                        sections[current_section] = "\n".join(current_content).strip()
                    current_section = section
                    current_content = []
                    continue

            if current_section:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def generate_doc(self, generator_type: str, form_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        log.info(f"Generating {generator_type} with data: {list(form_data.keys())}")

        try:
            template = self.template_engine.get_template(generator_type)
        except ValueError:
            raise ValueError(f"Unknown generator type: {generator_type}")

        knowledge_context = None
        if context is None:
            query = form_data.get("title") or form_data.get("problem_area", "")
            knowledge_context = self._retrieve_knowledge_context(query)

        system_prompt = self._build_system_prompt(generator_type)
        user_prompt = self._build_user_prompt(form_data, generator_type)

        if knowledge_context:
            evidence = knowledge_context.get("documents", [])
            if evidence:
                sources_text = "\n".join([f"- {doc.get('title', 'Unknown')}: {doc.get('summary', '')}" for doc in evidence[:3]])
                user_prompt += f"\n\n## Relevant Context from Knowledge Hub:\n{sources_text}"

        llm_response = self._call_llm(system_prompt, user_prompt)

        sections = self._parse_sections_from_response(llm_response, generator_type)

        is_valid, errors = self.template_engine.validate_output(sections, generator_type)
        if not is_valid:
            log.warning(f"Validation errors: {errors}")

        return {
            "generator_type": generator_type,
            "title": form_data.get("title", form_data.get("epic_summary", "Untitled")),
            "sections": sections,
            "raw_response": llm_response,
            "valid": is_valid,
            "errors": errors,
            "form_data": form_data,
        }

    def generate_with_epic_context(self, generator_type: str, form_data: Dict[str, Any], epic_key: str) -> Dict[str, Any]:
        epic_data = self.jira_helper.fetch_epic_data(epic_key)
        form_data["epic_context"] = epic_data
        return self.generate_doc(generator_type, form_data, context={"epic": epic_data})

    def generate_multiple(self, generator_configs: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        results = []
        for config in generator_configs:
            generator_type = config.get("type")
            form_data = config.get("form_data")
            try:
                result = self.generate_doc(generator_type, form_data)
                results.append(result)
            except Exception as e:
                log.error(f"Failed to generate {generator_type}: {e}")
                results.append({
                    "generator_type": generator_type,
                    "error": str(e),
                    "valid": False,
                })
        return results
