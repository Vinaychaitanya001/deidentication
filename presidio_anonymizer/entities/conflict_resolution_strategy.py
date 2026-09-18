# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/presidio_anonymizer/entities/conflict_resolution_strategy.py
# Copyright (c) Presidio Contributors.

"""An Enum class designed to manage all types of conflicts among entities or text."""

from enum import Enum


class ConflictResolutionStrategy(Enum):
    """Conflict resolution strategy.

    The strategy to use when there is a conflict between two entities.

    MERGE_SIMILAR_OR_CONTAINED: This default strategy resolves conflicts
    between similar or contained entities.
    REMOVE_INTERSECTIONS: Effectively resolves both intersection conflicts
    among entities and default strategy conflicts.
    NONE: No conflict resolution will be performed.
    """

    MERGE_SIMILAR_OR_CONTAINED = "merge_similar_or_contained"
    REMOVE_INTERSECTIONS = "remove_intersections"
