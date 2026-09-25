# Synthetic narrative-game evaluation

44 local files, including three exact copies, cover three anonymous invented works. Development and evaluation are explicit whole-work partitions. These fixtures and expected labels were engineered with knowledge of the rule engine. They test split isolation and mechanics; they are NOT an independent, untouched real-world holdout or a semantic benchmark.

The public manifest lists only anonymous work IDs, partitions and input files. Expected signals, groups, exclusions and context categories reside in separate `hidden_keys/<work-id>.json` files and are opened only after all selected analyses have been frozen. Rule code never imports this key. The ordinary reports omit expected answers. Scores deliberately retain misses on implicit language, sarcasm and synonyms.

No real game descriptions, manuscripts, reviews, walkthroughs, or questionnaires were used to create these fixtures. Real pilot annotations must be independent and prepared before model tuning.

A development run reads neither the evaluation work text nor its key.
