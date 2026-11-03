"""General Schemas

This file contains the types shared across several domains that do not belong to any
single one of them. Domain-specific types live in the sibling modules, and this file
imports none of them, so every module can depend on it without an import cycle.

Holds:
    - 'DifficultyLevel': How hard a question is. Used by questions, exams and profiles.
"""

from __future__ import annotations

from typing import Literal

DifficultyLevel = Literal["easy", "medium", "hard"]
