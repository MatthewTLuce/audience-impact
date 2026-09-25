# Narrative-game real-review pilot — prepared, not executed

## Intended study

Select two development titles and one evaluation title after a permitted source is established. Target approximately 50 ordinary reviews per title initially. Choose within the same broad narrative-game domain; record language, version/date coverage and acquisition method. Freeze the evaluation title before tuning. Keep one work per corpus and one shared private state directory for all study corpora.

Use an explicit acquisition and retention record. Do not select only emotional, long, positive, popular or highly helpful reviews. Preserve low-information, negative, gameplay, technical, price and service responses. Record selection filters and exclusions so the sample's limits are visible. Review count is not a verified participant count. Quarantine obvious copies and examine near copies without silently treating them as independent votes.

Provisional work codes are `pilot-game-a`, `pilot-game-b` (development) and `pilot-game-c` (evaluation). They are placeholders, not real selected titles. Do not add plot summaries, walkthroughs, scripts, game databases or known merchandise to analysis context.

## Human annotation before tuning

An annotator first reads each de-identified review independently, without engine output or other annotators' answers. Use one review per handoff. Capture:

- Anonymous work and review ID, source hash and normalization version.
- Exact supporting quote and Unicode start/end offsets.
- Literal emotionally significant subject, or unresolved/none.
- Expressed response and uncertainty, without inferring private intentions.
- Narrative, gameplay, technical, price/value, service, mixed or unresolved topic.
- Sensitivity or inappropriateness, and whether no supported observation is warranted.

After independent review, adjudicate disagreement in a separate record. Cross-review grouping should use the review evidence, not external story knowledge. Keep raw annotations, disagreements and adjudicated answers distinct. Do not let the same annotator see a model answer first and call that an independent key.

A reusable starting form is in `docs/annotation-record-template.json`. It is an operator/scorer artifact; it is not an importer or provider input. Copy it outside the ordinary review folder. The current executable scorer supports the shipped synthetic suites only; a real annotated-corpus scorer needs implementation once the actual input/annotation agreement is selected. The template is not a claim that real annotation import already exists.

## Freeze and evaluation sequence

1. Establish source permission or participant consent, local storage, retention and any requested deletion procedure. Remote inference remains disabled.
2. Import explicit authorized local files. Perform privacy review. Assign work IDs and partitions when initializing corpora; do not reuse an evaluation work in development.
3. Save source fingerprints and the reviewed normalized versions. Annotate independently before tuning. Keep answers outside the analysis state/input directory.
4. Develop on the two development works. Freeze engine/profile version and thresholds before first access to the real evaluation work and key.
5. Analyze the evaluation work, save its report digest, then score against the private answers.
6. Measure evidence validity, precision/recall, grouping precision/recall, topic confusion, abstention, duplicate resistance and inappropriate hypotheses per title. Treat recommendation ratings as sampling metadata, not an answer key for emotional impact.
7. Investigate failures without quietly reclassifying the used evaluation set as untouched. Any further tuning requires a new independent test set.
8. Later repeat a small book-domain evaluation. Neither game scores nor desire for a reminder establishes book accuracy or willingness to buy.

## Consented participant alternative

If a platform source is unsuitable, participants may submit reviews of a game they have played under explicit consent. Request an ordinary review first, without mentioning commercial opportunities. Only after submission ask a separate private questionnaire about what stayed with them, why, whether a reminder would be welcome, and what would be inappropriate to commercialize. Keep this questionnaire outside analysis inputs and reports.

No reviewer recruitment, source terms acceptance, account setup or remote model call has occurred as part of this shift.
