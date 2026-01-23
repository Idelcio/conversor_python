"""
OpenAI Extractor Module
Sistema de extração de certificados usando OpenAI GPT-4 Vision
"""

from .extractor import OpenAIExtractor
from .security import SecurityValidator
from .prompts import SYSTEM_PROMPT, EXTRACTION_SCHEMA

__all__ = ['OpenAIExtractor', 'SecurityValidator', 'SYSTEM_PROMPT', 'EXTRACTION_SCHEMA']
