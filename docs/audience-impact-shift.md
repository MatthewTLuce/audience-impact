# Audience Impact implementation — September 25, 2026

Version 0.2 adds narrative-game testing to the existing local engine. Books remain supported. The project directory and Python package retain their original names so existing scripts and saved corpora continue to work.

## Working interface

The new `audience-impact` command defaults to the narrative-game profile and the game fixture suite. The original `reader-impact` command defaults to books and the original synthetic suite. Both accept `--domain book` or `--domain narrative-game` when initializing a corpus. Domain, anonymous work ID and study partition are immutable corpus metadata. Old corpora with no domain metadata are read as book corpora; no record is rewritten or migrated automatically.

Each corpus represents exactly one work. Its evidence, clusters and decisions are scoped to that corpus. A work ID cannot be assigned to both development and evaluation within a single state store. The operator still must ensure that imported reviews concern the declared work: filenames and language heuristics cannot establish this automatically. Use a shared study store to enforce the partition rule; separate state stores cannot detect each other's assignments.

## Analysis behavior

Narrative-game analysis retains the narrow deterministic engine and adds versioned topic cues. Sentences with an emotion word and narrative cues become provisional narrative observations. Gameplay, technical, price/value and service comments are preserved separately. A sentence with multiple topic categories is marked mixed; one without topic cues is unresolved. Mixed and unresolved reactions stay in the report and cannot become narrative clusters or hypotheses automatically.

This is deliberately conservative and incomplete. A sentence mentioning story and combat could express a genuine attachment; it is withheld for human interpretation. A word such as character may be used in gameplay discussion and be misclassified. Implicit emotion, negation and sarcasm remain weaknesses. Literal topic separation does not establish psychological interpretation.

Evidence remains exact, versioned normalized text with source hashes and paragraph offsets. Topic cues additionally have offsets relative to their quoted sentence. Validation rejects classification fields that disagree with the configured rules. It does not certify that the rules understand the review.

No canonical character/object/scene identity is supplied from another source. Reports retain literal wording and unresolved referents. Only narrative candidates enter impact clusters; existing human split/merge corrections cannot include context observations. All commercial hypotheses remain proposed with rights, safety, manufacturing, cost, price, demand, fulfillment and margin unknown.

## Evaluation

The `narrative-games-v1` fixture suite contains 44 files: 41 unique synthetic reviews and three exact copies across three anonymous invented works. Two works belong to development; one belongs to evaluation. `--partition development` is the default; `--partition evaluation` selects only the third work; `--partition all` runs separate analyses and metrics for all works.

The provider receives only the same four fields as the book baseline: anonymous review ID, normalized text, source hash and normalization version. It receives neither partition metadata nor expected answers. All selected ordinary JSON/HTML reports are frozen to disk before any scoring key is opened. Keys are separated by work, so a development run reads no evaluation-work text or answers. Exact copies spanning selected development and evaluation partitions fail closed.

The evaluation partition is an engineered isolation test, not an independent holdout: the fixture author knew the rules. Do not tune against a future real evaluation set or claim these synthetic scores predict real-player performance. Scores are reported per work; a good result on one game cannot conceal a poor result on another.

## What is not implemented by this shift

No Steam connector, remote inference, external acquisition, UCI import or real-player pilot is enabled. No actual game corpus has been selected or collected. Existing manuscripts and editor data remain outside the system. The source-access assessment and pilot protocol define the next step; the software shift is complete independently of those later authorizations.

The prior browser-policy block on local HTML preview remains unresolved. Reports are structurally tested, escaped, checked for key leakage and saved locally. Visual browser acceptance is not claimed.
