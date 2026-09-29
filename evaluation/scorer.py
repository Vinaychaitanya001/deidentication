"""Evaluation v2: the one scorer used for every system and dataset.

Scores the FINAL resolved spans a system would redact (not raw detector output).
Every gold PHI span counts in the denominators; only explicit "don't care" regions
(e.g. honorifics in synth_dataset_v2) are excluded, and they are excluded from both
recall and precision.

Metrics
  entity  strict        exact boundaries + same category
          exact         exact boundaries, any type                (binary)
          partial       any character overlap                     (binary, lenient)
          partial_typed any overlap + same category               (lenient)
  token   binary/typed  alphanumeric tokens touched by a span
  char    leak rate     share of gold PHI alphanumeric characters left uncovered
  doc     zero-leak     share of documents with no uncovered gold PHI character
  hard_negatives        share of annotated look-alikes (BP, doses ...) that got redacted
Types are compared at the category level (NAME, DATE, LOCATION, ...).
"""

import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from deid.ontology import category

TOKEN_RE = re.compile(r"[^\W_]+")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    type: str


@dataclass
class EvalDoc:
    doc_id: str
    text: str
    gold: List[Span]
    ignore: List[Tuple[int, int]] = field(default_factory=list)
    hard_negatives: List[Tuple[int, int, str]] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)


COUNT_KEYS = (
    "strict_tp", "strict_pred", "strict_gold",
    "exact_tp", "exact_pred", "exact_gold",
    "partial_rec_hit", "partial_prec_hit", "partial_pred", "partial_gold",
    "ptyped_rec_hit", "ptyped_prec_hit",
    "tok_tp", "tok_fp", "tok_fn", "tokt_tp", "tokt_fp", "tokt_fn",
    "char_gold", "char_pred", "char_hit",
    "zero_leak", "docs",
)


def _overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
    return a0 < b1 and b0 < a1


def _alnum_positions(text: str, start: int, end: int) -> Iterable[int]:
    return (i for i in range(start, end) if text[i].isalnum())


def _clean_predictions(doc: EvalDoc, preds: Sequence[Span]) -> List[Span]:
    """Deduplicate and drop predictions that only touch don't-care regions."""
    out, seen = [], set()
    for p in preds:
        key = (p.start, p.end, category(p.type))
        if key in seen or p.end <= p.start:
            continue
        seen.add(key)
        touches_gold = any(_overlap(p.start, p.end, g.start, g.end) for g in doc.gold)
        touches_ignore = any(_overlap(p.start, p.end, s, e) for s, e in doc.ignore)
        if touches_ignore and not touches_gold:
            continue
        out.append(p)
    return out


def doc_counts(doc: EvalDoc, preds: Sequence[Span]) -> Dict[str, int]:
    preds = _clean_predictions(doc, preds)
    gold = doc.gold
    c = dict.fromkeys(COUNT_KEYS, 0)

    gs = {(g.start, g.end, category(g.type)) for g in gold}
    ps = {(p.start, p.end, category(p.type)) for p in preds}
    c["strict_tp"], c["strict_pred"], c["strict_gold"] = len(gs & ps), len(ps), len(gs)
    ge, pe = {(s, e) for s, e, _ in gs}, {(s, e) for s, e, _ in ps}
    c["exact_tp"], c["exact_pred"], c["exact_gold"] = len(ge & pe), len(pe), len(ge)

    c["partial_gold"], c["partial_pred"] = len(gold), len(preds)
    for g in gold:
        hits = [p for p in preds if _overlap(g.start, g.end, p.start, p.end)]
        c["partial_rec_hit"] += bool(hits)
        c["ptyped_rec_hit"] += any(category(p.type) == category(g.type) for p in hits)
    for p in preds:
        hits = [g for g in gold if _overlap(g.start, g.end, p.start, p.end)]
        c["partial_prec_hit"] += bool(hits)
        c["ptyped_prec_hit"] += any(category(p.type) == category(g.type) for g in hits)

    for m in TOKEN_RE.finditer(doc.text):
        t0, t1 = m.span()
        gcat = next((category(g.type) for g in gold if _overlap(t0, t1, g.start, g.end)), None)
        if gcat is None and any(_overlap(t0, t1, s, e) for s, e in doc.ignore):
            continue
        pcat = next((category(p.type) for p in preds if _overlap(t0, t1, p.start, p.end)), None)
        if gcat and pcat:
            c["tok_tp"] += 1
        elif pcat:
            c["tok_fp"] += 1
        elif gcat:
            c["tok_fn"] += 1
        if gcat and pcat == gcat:
            c["tokt_tp"] += 1
        else:
            c["tokt_fp"] += bool(pcat)
            c["tokt_fn"] += bool(gcat)

    gold_chars = {i for g in gold for i in _alnum_positions(doc.text, g.start, g.end)}
    pred_chars = {i for p in preds for i in _alnum_positions(doc.text, p.start, p.end)}
    c["char_gold"], c["char_pred"], c["char_hit"] = len(gold_chars), len(pred_chars), len(gold_chars & pred_chars)
    c["zero_leak"] = int(gold_chars <= pred_chars)
    c["docs"] = 1
    return c


def _prf(tp: float, n_pred: float, n_gold: float, rec_hit: Optional[float] = None) -> Dict[str, float]:
    p = tp / n_pred if n_pred else 0.0
    r = (rec_hit if rec_hit is not None else tp) / n_gold if n_gold else 0.0

    def fbeta(b: float) -> float:
        return (1 + b * b) * p * r / (b * b * p + r) if (p + r) else 0.0

    return {"precision": p, "recall": r, "f1": fbeta(1), "f2": fbeta(2)}


def summarize(c: Dict[str, float]) -> Dict:
    tok_pred, tok_gold = c["tok_tp"] + c["tok_fp"], c["tok_tp"] + c["tok_fn"]
    tokt_pred, tokt_gold = c["tokt_tp"] + c["tokt_fp"], c["tokt_tp"] + c["tokt_fn"]
    char_rec = c["char_hit"] / c["char_gold"] if c["char_gold"] else 1.0
    return {
        "entity_strict": _prf(c["strict_tp"], c["strict_pred"], c["strict_gold"]),
        "entity_exact": _prf(c["exact_tp"], c["exact_pred"], c["exact_gold"]),
        "entity_partial": _prf(c["partial_prec_hit"], c["partial_pred"], c["partial_gold"], c["partial_rec_hit"]),
        "entity_partial_typed": _prf(c["ptyped_prec_hit"], c["partial_pred"], c["partial_gold"], c["ptyped_rec_hit"]),
        "token_binary": _prf(c["tok_tp"], tok_pred, tok_gold),
        "token_typed": _prf(c["tokt_tp"], tokt_pred, tokt_gold),
        "char": {
            "recall": char_rec,
            "leak_rate": 1.0 - char_rec,
            "precision": c["char_hit"] / c["char_pred"] if c["char_pred"] else 0.0,
        },
        "doc_zero_leak_rate": c["zero_leak"] / c["docs"] if c["docs"] else 0.0,
        "counts": {k: int(c[k]) for k in ("docs", "partial_gold", "partial_pred", "char_gold", "zero_leak")},
    }


# Headline numbers that get bootstrap confidence intervals.
HEADLINE = {
    "strict_f1": lambda s: s["entity_strict"]["f1"],
    "strict_f2": lambda s: s["entity_strict"]["f2"],
    "exact_f2": lambda s: s["entity_exact"]["f2"],
    "partial_recall": lambda s: s["entity_partial"]["recall"],
    "partial_precision": lambda s: s["entity_partial"]["precision"],
    "partial_f2": lambda s: s["entity_partial"]["f2"],
    "token_f2": lambda s: s["token_binary"]["f2"],
    "token_typed_f2": lambda s: s["token_typed"]["f2"],
    "char_leak_rate": lambda s: s["char"]["leak_rate"],
    "doc_zero_leak_rate": lambda s: s["doc_zero_leak_rate"],
}


def _sum(rows: Sequence[Dict[str, int]]) -> Dict[str, float]:
    tot = dict.fromkeys(COUNT_KEYS, 0)
    for r in rows:
        for k in COUNT_KEYS:
            tot[k] += r[k]
    return tot


def bootstrap_ci(rows: Sequence[Dict[str, int]], n: int = 1000, seed: int = 13, alpha: float = 0.05) -> Dict[str, List[float]]:
    rng = random.Random(seed)
    draws = defaultdict(list)
    for _ in range(n):
        s = summarize(_sum([rows[rng.randrange(len(rows))] for _ in rows]))
        for name, f in HEADLINE.items():
            draws[name].append(f(s))
    return {name: _percentiles(v, alpha) for name, v in draws.items()}


def paired_difference_ci(rows_a, rows_b, n: int = 1000, seed: int = 13, alpha: float = 0.05) -> Dict[str, Dict]:
    """CI of metric(A) - metric(B), resampling the same documents for both systems."""
    assert len(rows_a) == len(rows_b)
    rng = random.Random(seed)
    base_a, base_b = summarize(_sum(rows_a)), summarize(_sum(rows_b))
    draws = defaultdict(list)
    for _ in range(n):
        idx = [rng.randrange(len(rows_a)) for _ in rows_a]
        sa, sb = summarize(_sum([rows_a[i] for i in idx])), summarize(_sum([rows_b[i] for i in idx]))
        for name, f in HEADLINE.items():
            draws[name].append(f(sa) - f(sb))
    return {name: {"diff": HEADLINE[name](base_a) - HEADLINE[name](base_b), "ci": _percentiles(v, alpha)}
            for name, v in draws.items()}


def _percentiles(values: List[float], alpha: float) -> List[float]:
    v = sorted(values)
    lo, hi = v[int(alpha / 2 * (len(v) - 1))], v[int((1 - alpha / 2) * (len(v) - 1))]
    return [lo, hi]


def per_category(docs: Sequence[EvalDoc], preds: Dict[str, List[Span]]) -> Dict[str, Dict]:
    """Recall per gold category (lenient + strict + char) and precision per predicted category."""
    rec = defaultdict(lambda: defaultdict(int))
    prec = defaultdict(lambda: defaultdict(int))
    for d in docs:
        ps = _clean_predictions(d, preds.get(d.doc_id, []))
        pchars = {i for p in ps for i in _alnum_positions(d.text, p.start, p.end)}
        for g in d.gold:
            r = rec[category(g.type)]
            r["support"] += 1
            r["partial_hit"] += any(_overlap(g.start, g.end, p.start, p.end) for p in ps)
            r["strict_hit"] += any((p.start, p.end, category(p.type)) == (g.start, g.end, category(g.type)) for p in ps)
            chars = set(_alnum_positions(d.text, g.start, g.end))
            r["chars"] += len(chars)
            r["chars_hit"] += len(chars & pchars)
        for p in ps:
            q = prec[category(p.type)]
            q["predicted"] += 1
            q["overlaps_any_phi"] += any(_overlap(g.start, g.end, p.start, p.end) for g in d.gold)
    out = {"recall_by_gold_category": {}, "precision_by_pred_category": {}}
    for cat, r in sorted(rec.items(), key=lambda kv: -kv[1]["support"]):
        out["recall_by_gold_category"][cat] = {
            "support": r["support"],
            "partial_recall": r["partial_hit"] / r["support"],
            "strict_recall": r["strict_hit"] / r["support"],
            "char_recall": r["chars_hit"] / r["chars"] if r["chars"] else 1.0,
        }
    for cat, q in sorted(prec.items(), key=lambda kv: -kv[1]["predicted"]):
        out["precision_by_pred_category"][cat] = {
            "predicted": q["predicted"],
            "partial_precision": q["overlaps_any_phi"] / q["predicted"],
        }
    return out


def name_subtypes(docs: Sequence[EvalDoc], preds: Dict[str, List[Span]]) -> Dict:
    """Patient vs clinician: of gold names overlapped by a subtyped name prediction, how many match."""
    matched = total = 0
    for d in docs:
        ps = [p for p in preds.get(d.doc_id, []) if p.type in ("NAME.PATIENT", "NAME.CLINICIAN")]
        for g in d.gold:
            if g.type not in ("NAME.PATIENT", "NAME.CLINICIAN"):
                continue
            hits = [p for p in ps if _overlap(g.start, g.end, p.start, p.end)]
            if hits:
                total += 1
                matched += hits[0].type == g.type
    return {"compared": total, "subtype_correct": matched, "accuracy": matched / total if total else None}


def hard_negative_rate(docs: Sequence[EvalDoc], preds: Dict[str, List[Span]]) -> Dict:
    by_kind = defaultdict(lambda: [0, 0])
    for d in docs:
        ps = preds.get(d.doc_id, [])
        for s, e, kind in d.hard_negatives:
            flagged = any(_overlap(s, e, p.start, p.end) for p in ps)
            by_kind[kind][0] += 1
            by_kind[kind][1] += flagged
    n = sum(v[0] for v in by_kind.values())
    f = sum(v[1] for v in by_kind.values())
    return {
        "total": n, "redacted": f, "rate": f / n if n else None,
        "by_kind": {k: {"total": v[0], "redacted": v[1], "rate": v[0] and v[1] / v[0]}
                    for k, v in sorted(by_kind.items())},
    }


def evaluate(docs: Sequence[EvalDoc], preds: Dict[str, List[Span]], bootstrap: int = 1000) -> Dict:
    rows = [doc_counts(d, preds.get(d.doc_id, [])) for d in docs]
    result = summarize(_sum(rows))
    result["ci95"] = bootstrap_ci(rows, n=bootstrap) if bootstrap else {}
    result.update(per_category(docs, preds))
    result["name_subtypes"] = name_subtypes(docs, preds)
    if any(d.hard_negatives for d in docs):
        result["hard_negatives"] = hard_negative_rate(docs, preds)
    result["_rows"] = rows
    return result
