# deidentication
microsoft presido replica
https://claude.ai/code/artifact/cc6d11e0-8ff5-423e-97a9-1690bc498685

Clinical PHI de-identification for English notes (Telugu later), built on a pinned
[Presidio](https://github.com/data-privacy-stack/presidio) with our own L0–L7 pipeline in `deid/`.
Current phase: Phase 1 (Foundations). Start with [CLAUDE.md](CLAUDE.md); the architecture,
roadmap, decisions and current state are in [docs/](docs/).

## Run

Python ≥ 3.10 (tested on 3.12).

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest              # test suite
.venv/bin/python demo_clinical.py       # one synthetic note through every stage
.venv/bin/python evaluate_v2.py         # baselines vs Phase-1 system -> results/v2/REPORT.md
```

The clinical NER model (`obi/deid_roberta_i2b2`, ~1.4 GB) downloads on first use.
All data in this repository is synthetic. Set `DEID_HMAC_KEY` before transforming anything real.
