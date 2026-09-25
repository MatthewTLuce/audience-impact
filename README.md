# Audience Impact Local Alpha

Version 0.2 extends the Reader Impact workbench to **narrative-game reviews**, while preserving books and the existing local state format. It identifies provisional evidence of emotionally significant experiences, keeps unrelated review reactions separate, and records human decisions about proposed groupings and commercial-opportunity hypotheses.

**This is a local engineering alpha, not a validated reader/player understanding system.** All shipped reviews are synthetic. Only synthetic fixtures are included. Remote models and live-source connectors are disabled, and no commercial conclusion has been approved. The deterministic engine still misses implicit emotion, sarcasm and equivalent references expressed differently.

## Run the local build

Clone this repository, enter its directory and follow the clean installation commands below.

```sh
.venv/bin/audience-impact --help
.venv/bin/audience-impact evaluate --out outputs/game-development
.venv/bin/audience-impact evaluate --partition evaluation --out outputs/game-evaluation
.venv/bin/reader-impact evaluate --fixture-suite synthetic-v1 --out outputs/book-regression
```

The new `audience-impact` command defaults to narrative games. `reader-impact` retains book defaults for existing scripts. Both operate on the same `reader_impact` Python package and can explicitly initialize either domain. The project directory was not renamed and existing databases were not rewritten.

## Clean installation and checks

Requires Python 3.11+ on macOS or Linux. Tested with Python 3.12.14. The macOS system Python used during the original build was 3.9; use a compatible installed Python instead.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps .
.venv/bin/python -m pytest -q
.venv/bin/audience-impact evaluate --fixture-suite narrative-games-v1 --partition all
.venv/bin/reader-impact evaluate --fixture-suite synthetic-v1
```

Dependency installation may use the package registry; runtime analysis needs no network or API credentials. Use a normal installation rather than editable mode: the bundled Python runtime did not reliably honor editable `.pth` files. After source changes, reinstall with `pip install --no-deps --force-reinstall .`, or run source tests with `PYTHONPATH=src .venv/bin/python -m pytest -q`. Run fixture evaluation from this source checkout; fixtures are deliberately outside the provider package.

## One work per corpus

The following illustrates a later authorized real-review workflow; no human reviews have been imported by this build.

```sh
.venv/bin/audience-impact init --corpus game-a-dev --work pilot-game-a --partition development
.venv/bin/audience-impact ingest --corpus game-a-dev --authorized-local-reviews /absolute/path/to/ordinary-review.txt
.venv/bin/audience-impact inspect --corpus game-a-dev --review R0001
.venv/bin/audience-impact privacy-review --corpus game-a-dev --review R0001 --actor operator-01 --reason 'Checked normalized text for personal information'
.venv/bin/audience-impact analyze --corpus game-a-dev
.venv/bin/audience-impact report --corpus game-a-dev --out outputs/game-a
.venv/bin/audience-impact audit --corpus game-a-dev
```

For books use `audience-impact init --domain book --corpus book-a --work book-a`, or the original `reader-impact init` command. Old corpora without domain fields are interpreted as books without altering their records.

Each corpus is scoped to one anonymous work ID. Set `--partition development`, `evaluation` or the default `unassigned`. The same work cannot be assigned to development and evaluation within the same data store. Use a shared private `--data /path/to/study-state` directory for a study. Review files still need to match the operator-declared work; the software cannot establish title identity from arbitrary prose.

`inspect --review` is a protected operator view and may display identifiers before approval. Add `--identity 'known identity'` to ingest or privacy-review to record redaction; use the Python API for private identity mappings if shell history is a concern. Automatic redaction does not reliably recognize all names. Use `--exclude` with a reason for excluded inputs. Corrections append a new normalization version and invalidate current analysis reports until analysis runs again.

Supply explicit local UTF-8 TXT, DOCX or searchable-PDF files. No manual filename changes are required. Directories, symlinks, obvious prohibited input categories, unauthorized imports and unsupported formats fail closed. Recognized active, corrupt, encrypted, oversized or image-only files are quarantined. Source hashing and passive extraction are bounded; this is not a hostile-file malware sandbox.

## Narrative versus other reactions

The game profile records sentence-level literal topic cues. Narrative candidates are eligible for impact clustering. Gameplay, technical, price/value, service, mixed and unresolved reactions are kept in `context_observations` and displayed separately with their exact evidence. They cannot automatically support a narrative opportunity hypothesis. Book behavior remains the legacy baseline.

This distinction is provisional: mixed-topic sentences can contain real emotional significance, and cues can be misleading. No canonical identities or facts are inferred from game scripts, plots, walkthroughs or outside knowledge. Referents remain literal/unresolved. Exact-phrase clustering deliberately leaves many synonymous references apart.

## Human decisions and audit

Originals, normalized versions, raw proposals, validation failures and human decisions remain separately inspectable in private SQLite records. Each source retains a SHA-256 fingerprint. Append-only SQL triggers and a hash chain provide local tamper evidence; they do not protect against an adversarial machine owner.

```sh
.venv/bin/audience-impact decide --corpus game-a-dev --target C-REPLACE --status rejected --actor operator-01 --reason 'Evidence does not support this grouping'
```

Supported statuses: accepted, rejected, needs_review, corrected, split and merge. Structural changes require `--groups '[["O-first"],["O-second"]]'` for a split or one complete group for a merge. Unknown, repeated or omitted affected observations fail validation. Decisions target the current run of that corpus; cross-work decisions and context-to-narrative merges are rejected. Corrections preserve the original proposal and do not automatically create approved products.

Every hypothesis remains a proposal, with rights, safety, manufacturing, cost, price, demand, fulfillment and margin unknown. No product-brief export, outreach, publishing, purchase or auto-approval operation exists.

## Evaluation and limitations

`narrative-games-v1` contains 44 files and 41 unique reviews across three anonymous invented works. Two are development works and one is an evaluation work. Default evaluation reads only development reviews and their scorer keys. All selected analysis reports are saved before any key is opened. The provider never receives keys, partition labels, filenames or identity mappings. An all-partition run rejects exact review copies spanning development/evaluation.

The fixture author knew the rules. The evaluation partition is a test of isolation, **not an independent real-player holdout**. Do not use these scores to claim emotional accuracy, independent-reader counts or commercial viability. Scores are separate by work and include weak clustering/implicit-language cases; the original book suite remains available as a regression baseline.

Each run retains originals and audit state in `private/`. Game runs contain per-work `analysis.json/html` and `evaluation.json/html`, plus an aggregate evaluation overview. Reports omit hidden answers. The source package includes separate synthetic scorer keys so the test suite can be reproduced.

Reports are escaped and programmatically checked for evidence and key leakage. Visual browser inspection remains unverified after a browser-policy block on local HTML files. The complete original alpha definition of done is not claimed.

## Next real-data step

Establish a permitted complete-review corpus and an independent annotation process before tuning. Steam has a documented endpoint, but applicability of source terms and permission for our study remain unresolved; no connector is enabled. A consented participant corpus is an alternative. No actual game titles have been selected. A real annotation/scoring workflow remains to be implemented after the corpus agreement is defined.

See:

- `docs/audience-impact-shift.md` — compatibility, profile behavior and limitations.
- `docs/narrative-game-pilot.md` — study design and independent annotation protocol.
- `docs/annotation-record-template.json` — blank private annotation form, not an analysis input.
- `docs/game-source-access-assessment.md` — source investigation and unresolved permission scope.
- `docs/data-boundaries.md` — storage, privacy and prohibited inputs.

The no-manuscript boundary remains in force. Live sources and remote models remain disabled. Books remain a future transfer test, not a domain whose accuracy follows from game results.
