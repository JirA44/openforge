# Contributing to OpenForge

Thanks for your interest in improving OpenForge!

## Development setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # API on http://127.0.0.1:8000
```

## Submitting changes

1. Open an issue first for anything non-trivial (bug or feature).
2. Keep PRs focused: one feature or fix per PR.
3. Add or update tests when behavior changes.
4. Run the API locally and validate at least one manifest from `examples/` before submitting.

## Manifest schema

All artifacts (strategy, dataset, knowledge, proof, decision) must carry:
`schema_version`, `artifact_type`, `name`, `version`, `license`.
See `schemas/openforge.schema.json` and the files under `examples/`.

## Code of conduct

Be constructive. Rejected contributions get a reason — negative results are
valuable here too.
