"""
DreamFi Document Generators — Phase 2
Form-driven document generation using LLM + templates.
Enforces DreamFi voice, structure, and quality standards.
"""

from generators.voice import VOICE_GUIDELINES, FORMAT_RULES, apply_voice_check
from generators.engine import GeneratorEngine

__all__ = [
    "VOICE_GUIDELINES",
    "FORMAT_RULES",
    "apply_voice_check",
    "GeneratorEngine",
]
