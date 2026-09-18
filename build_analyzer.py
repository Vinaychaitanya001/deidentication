"""
Construct a full Presidio AnalyzerEngine + AnonymizerEngine.

OUR OWN code (not from the Presidio repo) — but it only *wires together*
vendored Presidio classes; no detection logic lives here.

Two documented deviations from `presidio_analyzer/conf/default.yaml`:

1. **Model.** The shipped default is `en_core_web_lg` (~560 MB). We default
   to `en_core_web_sm` (~13 MB) because that is what is installed, and
   because model size vs accuracy is one of the things this study measures.
   Override with `model_name=`.

2. **ORGANIZATION.** Presidio's default config lists `ORGANIZATION` under
   `labels_to_ignore` with the comment "Has many false positives", so out of
   the box org detections are thrown away. `synth_dataset_v2.json` contains
   250 ORGANIZATION spans, so this materially changes recall. Both settings
   are measurable via `include_organization=`.
"""

from pathlib import Path
from typing import List, Optional

import yaml

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

DEFAULT_CONF = Path(__file__).parent / "presidio_analyzer" / "conf" / "default.yaml"


def build_nlp_configuration(
    model_name: str = "en_core_web_sm",
    include_organization: bool = False,
    language: str = "en",
) -> dict:
    """Load Presidio's own default.yaml, then apply our two overrides."""
    with open(DEFAULT_CONF, encoding="utf-8") as f:
        conf = yaml.safe_load(f)

    conf["models"] = [{"lang_code": language, "model_name": model_name}]

    if include_organization:
        ner_conf = conf.get("ner_model_configuration", {})
        ignore = [x for x in (ner_conf.get("labels_to_ignore") or []) if x]
        ner_conf["labels_to_ignore"] = [x for x in ignore if x != "ORGANIZATION"]
        conf["ner_model_configuration"] = ner_conf

    return conf


def build_analyzer(
    model_name: str = "en_core_web_sm",
    include_organization: bool = False,
    languages: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
) -> AnalyzerEngine:
    """
    Build a fully wired AnalyzerEngine.

    :param model_name: spaCy model to load
    :param include_organization: un-ignore the ORGANIZATION NER label
    :param languages: languages to load recognizers for (default ["en"])
    :param countries: ISO country codes for country-specific recognizers.
        Default ["us"] — loading all ~18 countries on English text adds
        latency and false positives for no benefit here.
    """
    languages = languages or ["en"]
    countries = countries if countries is not None else ["us"]

    nlp_configuration = build_nlp_configuration(
        model_name=model_name, include_organization=include_organization
    )
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

    registry = RecognizerRegistry(supported_languages=languages)
    registry.load_predefined_recognizers(
        languages=languages, nlp_engine=nlp_engine, countries=countries
    )

    return AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=languages,
    )


def build_anonymizer() -> AnonymizerEngine:
    """Build the full AnonymizerEngine (all 7 operators via OperatorsFactory)."""
    return AnonymizerEngine()


if __name__ == "__main__":
    print("Building full Presidio AnalyzerEngine...")
    analyzer = build_analyzer()
    print(f"  NLP engine        : {analyzer.nlp_engine.engine_name}")
    print(f"  recognizers loaded: {len(analyzer.registry.recognizers)}")
    print(f"  supported entities: {len(analyzer.get_supported_entities('en'))}")
    print()

    text = (
        "Dr. Sarah Johnson from Boston General Hospital called on March 15, 2024. "
        "Her email is sarah.johnson@bgh.org, phone +1 415-555-2671, "
        "SSN 123-45-6789, card 4111 1111 1111 1111."
    )
    print("TEXT:", text)
    print()
    for r in sorted(analyzer.analyze(text=text, language="en"), key=lambda x: x.start):
        print(f"  {r.entity_type:<18} [{r.start:>3}:{r.end:<3}] "
              f"score={r.score:.2f}  {text[r.start:r.end]!r}")
