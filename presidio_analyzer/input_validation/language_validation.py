# Vendored, unmodified, from microsoft/presidio (MIT License).
# Source: https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/input_validation/language_validation.py
# Copyright (c) Presidio Contributors.

from typing import List

import regex as re


def validate_language_codes(languages: List[str]) -> None:
    """Validate language codes format.

    :param languages: List of languages to validate.
    """
    language_code_regex = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")

    for lang in languages:
        if not re.match(language_code_regex, lang):
            raise ValueError(
                f"Invalid language code format: {lang}. "
                f"Expected format: 'en' or 'en-US'"
            )
