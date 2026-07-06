"""Fact and timeline extraction from plain-language complaints."""

from src.extract.facts import extract_facts
from src.extract.schema import FactsDocument

__all__ = ["extract_facts", "FactsDocument"]
