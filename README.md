# OpenForge

A Git for **verifiable artifacts**: knowledge, datasets, mathematical proofs,
and quantitative strategies. Every repository is a manifest + versioned files
+ integrity hashes + automated evaluations + verifiable provenance.

## Products

- **KnowledgeForge** — sourced, versioned, contestable claims.
- **DataForge** — versioned, traceable, reproducible datasets.
- **ProofForge** — formal proofs with dependencies and automatic verification.
- **MOS Hub** — quantitative strategies, reproducible backtests, live tracking.
- **DecisionForge** — decision journal: hypotheses, alternatives, outcomes.

## Principle

Each artifact repository contains:

1. a standard manifest;
2. Git-versioned files;
3. integrity proofs by hash;
4. automated evaluations;
5. verifiable provenance;
6. reproducible results.

## Quick start (Windows / PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./bootstrap.ps1
./run.ps1
```

Local API: `http://127.0.0.1:8000` — see `docs/ARCHITECTURE.md`.

## Recommended MVP

Start with **MOS Hub**: create a strategy repo, validate its manifest, run a
standardized backtest, compute CAGR / Sharpe / Sortino / Calmar / drawdown,
compare two commits, publish a performance sheet, sign results, fork a
strategy.

## Structure

```text
openforge-starter/
├── backend/     # FastAPI validation & hashing API
├── cli/         # openforge CLI
├── docs/        # architecture, product vision, roadmap
├── examples/    # sample manifests per artifact type
├── schemas/     # JSON schema
├── bootstrap.ps1
└── run.ps1
```

## License

MIT — see [LICENSE](LICENSE).
