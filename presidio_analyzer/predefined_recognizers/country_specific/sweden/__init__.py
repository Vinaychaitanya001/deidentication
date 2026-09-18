# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/sweden/__init__.py
# Copyright (c) Presidio Contributors.

"""Sweden-specific recognizers."""

from .se_organisationsnummer_recognizer import SeOrganisationsnummerRecognizer
from .se_personnummer_recognizer import SePersonnummerRecognizer

__all__ = [
    "SeOrganisationsnummerRecognizer",
    "SePersonnummerRecognizer",
]
