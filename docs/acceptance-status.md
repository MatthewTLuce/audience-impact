# Acceptance status

Milestones 0–8 have implemented local workflows and offline checks. The full definition of done is **not claimed**: browser visual inspection was blocked by the local-file URL security policy. JSON/HTML content, escaping, complete evidence and absence of hidden-key canaries are checked programmatically. No browser screenshot was obtained.

| Milestone | Implemented evidence | Qualification |
|---|---|---|
| 0 Foundation | package install, SQLite append-only records, audit chain, init and disabled operations tests | local tamper evidence, not hostile-owner protection |
| 1 Ingestion | TXT/DOCX/PDF success; empty/corrupt/encrypted/active/image-only/oversize/timeout quarantine tests | passive parsers, not a malware sandbox; oversized sources recorded without reading full bytes |
| 2 Privacy | mandatory privacy gate; identifiers/contact redaction; immutable versions; stale-run blocking | manual checking required; unknown names cannot be guaranteed removed |
| 3 Fixtures | 21 synthetic files, 20 unique reviews; separate expected key; all requested adversarial categories represented | overt wrong-scope and coordination cues only |
| 4 Analysis | provider-neutral protocol; deterministic engine; proposals and failures; valid spans and literal interpretation checks | narrow rules; sarcasm and implicit emotion remain failures |
| 5 Clustering | conservative exact phrase grouping, copy screening, disagreement preservation, audited split/merge/correct | synonyms deliberately unmerged; independent reader counts unknown |
| 6 Hypotheses | broad proposed experience category, evidence origin, eight unknowns, sensitive/ambiguous/low-evidence withholding | no real concept selected or approved; suitability remains provisional |
| 7 Evaluation | one-command run; retained state; frozen analysis before scorer key read; aggregate metrics and JSON/HTML | visual browser QA blocked; semantic measures are uncalibrated |
| 8 Pilot readiness | neutral review sheet, separate questionnaire, storage and consent protocol | no human corpus, no pilot execution; dedicated one-at-a-time blinded review UI deferred |

No live connector, remote inference, credentials, manuscript access, outreach, spending, publication or commercial approval occurred. Open-source package dependencies were installed from the package registry for local development.

## September 25 audience-impact shift

Version 0.2 adds an `audience-impact` CLI with narrative-game defaults, immutable per-corpus domain/work/partition metadata, isolated topic categories and three-work synthetic evaluation. The original book command and corpus records remain compatible. See `audience-impact-shift.md` for implementation details and the separate narrative-game pilot/source assessment documents for the next real-data step.

This is a software/testing shift. A real-game corpus and an independent human-labelled evaluation have not been acquired or executed. Visual browser QA remains unverified. These qualifications supersede any interpretation of the milestone table as production or semantic readiness.
