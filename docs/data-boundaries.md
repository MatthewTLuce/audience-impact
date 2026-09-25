# Data boundaries

Only explicitly supplied, authorized local ordinary reviews are allowed. Never supply a manuscript, synopsis, plot outline, character bible, Plot Designer data, private questionnaire, or answer key to ingestion. No browser, connector, network model, credentials, or external action exists in the production pipeline.

The data root is private to the local OS user (0700); database and reports use 0600. This is not encryption. Use a trusted local account and an encrypted disk for a later pilot. Filesystem copies and backups remain the operator's responsibility. Real data, secrets and outputs are ignored by version control. Keep the data root outside any sync or public folder.

## Storage

- `app-data/originals/<sha256>`: untouched source bytes, read-only to the application workflow (0400).
- `app-data/state.sqlite3`, `source` records: filenames, hashes, extraction state and managed-copy provenance; protected operator data.
- `extracted` records: original extracted text; never a provider input.
- `identity` records: supplied mappings and correction history; protected, append-only.
- `review` records: normalized text, paragraph boundaries, redaction actions, inclusion and version. Pending records never enter analysis.
- `proposal` and `analysis` records: raw rule output, validation failures and accepted-by-validator evidence (not human acceptance).
- `decision` records: human actor, rationale, action and replacement groupings; original proposals survive.
- `report` and `evaluation` records: immutable snapshot fingerprints and run metadata.
- Ordinary JSON/HTML: anonymous review IDs, evidence, hypotheses and privacy-safe decision projections. No filenames, corpus label, actor names or private correction rationale.
- A later human questionnaire key belongs outside the review input directory and outside the ordinary state directory. Do not import it. The current scorer only supports the shipped synthetic suite.

All offsets are Unicode code-point offsets into a specific normalized review version, not byte offsets or PDF page coordinates. The source hash links that record to the untouched original. Redaction changes offsets only by creating a new normalization version. Any review change invalidates the current analysis for report and decision purposes; prior runs remain protected audit history.

## Limits

Passive parsers never invoke macros, document relationships, PDF scripts or metadata actions. DOCX external relationships, macros and embedded objects are quarantined; PDF recognized active content is quarantined. Input size, extracted-text length, DOCX expanded size and PDF page count are bounded. Extraction runs in a fixed child process with a 10-second wall timeout, a 5-second CPU limit, and a 512 MiB address-space limit where the OS supports it. Format libraries remain a dependency trust boundary. This alpha is not a hostile-file malware sandbox.

Privacy approval is an operator attestation after reading the normalized text. The tool cannot guarantee removal of every identifier. Reports can contain story quotations and spoilers; retain them locally. A privacy correction blocks new reports from stale analyses, but does not erase prior snapshots or originals.
