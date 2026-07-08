"""Rights, applicable-law, and pathways explainers grounded in curated bare acts."""

from src.explain.explain import DISCLAIMER, RightsExplanation, explain_rights
from src.explain.pathways import PathwaysExplanation, explain_pathways

__all__ = [
    "explain_rights",
    "RightsExplanation",
    "explain_pathways",
    "PathwaysExplanation",
    "DISCLAIMER",
]
