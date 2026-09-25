# Human pilot protocol — prepared, not executed

Before collecting or importing any human review, record consent, a local storage location, retention/deletion expectations, who may read originals, and whether any future remote inference is permitted. The current software performs no remote inference. Agree on how withdrawal will be handled; append-only records mean physical deletion needs a separately designed, authorized retention workflow. Do not promise individual deletion through the alpha CLI.

Assign anonymous reviewer codes and keep the identity mapping privately. Ask each participant to submit one ordinary review file in UTF-8 TXT, DOCX or searchable PDF. They do not need to rename it. An operator supplies the explicit file path and maps its returned R-code to the participant privately. Avoid directory globbing in folders containing anything except authorized ordinary reviews.

## Ordinary review instruction sheet

Please write a review in your own words. Describe your reading experience in whatever way feels natural. There is no required length or list of topics, and there are no right answers. Please avoid including your contact details in the review itself. Submit this review before opening the separate follow-up questionnaire.

## Private follow-up questionnaire

Keep this sheet separate from the ordinary review and analysis inputs. After the ordinary review has been submitted:

1. Did anything remain especially vivid or emotionally important to you? Describe it in your own words, or say none.
2. What response did it evoke, if any? What makes you say that?
3. Was anything meaningful but unwelcome, upsetting, sacred or unsuitable for commercial treatment?
4. Would you personally want any tangible reminder or related experience? No is a useful answer. If yes, describe the connection without assuming a purchase.
5. May the study operator compare these answers to the analysis of your ordinary review under the consent already discussed?

## Blinded sequence

1. Store originals only through the authorized importer; inspect the private normalized text using `inspect --review R0001`.
2. Supply known identifiers for redaction; check names, addresses, contact details and accidental private content manually. Record a privacy approval or exclude the review.
3. Analyze using `--engine deterministic`. Save the JSON/HTML snapshot and its SHA-256 record before opening questionnaire answers.
4. Read each candidate independently and record an initial judgment before seeing any answer key. The ordinary report is an engineering evidence overview, not a blinded one-at-a-time human evaluation instrument.
5. An operator may then compare the frozen snapshot with the separate answers outside this tool. Do not feed the key back into the analysis. A dedicated blinded human-evaluation reader and scoring protocol remain future work.
6. Report disagreements, missing evidence, abstentions and inappropriate concepts; do not frame willingness to have a reminder as demonstrated willingness to pay.

No participants have been contacted and no human files have been imported by this build.
