"""L0 ingest. Phase 1 is a pass-through: English only, spans refer to the original text.

Unicode/whitespace normalization with an OffsetMap and per-segment language ID are P2.9.
"""

from deid.contracts import Document


def ingest(text: str, doc_id: str = "doc", language: str = "en") -> Document:
    return Document(doc_id=doc_id, text=text, language=language)
