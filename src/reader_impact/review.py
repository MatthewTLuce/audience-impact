"""Human decisions and structural corrections retain original proposals."""
from .domain import BoundaryError, identifier
from .analysis import make_cluster

def latest(store, corpus):
    store.corpus(corpus)
    rows = store.rows("analysis", corpus)
    if not rows:
        raise BoundaryError("No analysis available.")
    run = rows[-1]
    versions = [dict(review_id=r["review_id"],version=r["version"]) for r in store.reviews(corpus) if r["inclusion"] == "included"]
    if versions != run["selected_reviews"] or any(r["inclusion"] == "pending_privacy_review" for r in store.reviews(corpus)):
        raise BoundaryError("Analysis is stale after a review change; analyze again.")
    return run

def decide(store, corpus, target, status, actor, reason, groups=None):
    identifier(actor)
    if not reason.strip():
        raise BoundaryError("A human decision reason is required.")
    run = latest(store, corpus)
    originals = {c["cluster_id"]:c for c in run["clusters"]}
    targets = set(originals) | {h["hypothesis_id"] for h in run["hypotheses"]}
    if target not in targets:
        raise BoundaryError("Unknown target in current analysis.")
    if status not in {"accepted", "rejected", "needs_review", "corrected", "split", "merge"}:
        raise BoundaryError("Unsupported human decision.")
    replacements = []
    if status in {"corrected", "split", "merge"}:
        if target not in originals or not groups or not all(isinstance(g,list) and g for g in groups):
            raise BoundaryError("Structural corrections require non-empty observation groups for a cluster.")
        ids = [oid for g in groups for oid in g]
        observations = {o["observation_id"]:o for o in run["observations"]}
        if len(ids) != len(set(ids)) or not set(ids) <= set(observations):
            raise BoundaryError("Unknown or repeated observation in correction.")
        affected = [c for c in run["clusters"] if set(c["member_observations"]) & set(ids)]
        expected = set(oid for c in affected for oid in c["member_observations"])
        if set(ids) != expected or not set(originals[target]["member_observations"]) <= set(ids):
            raise BoundaryError("Correction must preserve every member of every affected cluster.")
        if status == "split" and (len(groups)<2 or len(affected)!=1):
            raise BoundaryError("Split requires one original and at least two groups.")
        if status == "merge" and (len(groups)!=1 or len(affected)<2):
            raise BoundaryError("Merge requires at least two originals and one group.")
        replacements = [make_cluster([observations[oid] for oid in group], "Human correction: " + reason) for group in groups]
    return store.add("decision", corpus, dict(analysis_id=run["json_id"], target=target, status=status,
        actor=actor, reason=reason, replacements=replacements,
        affected_clusters=[c["cluster_id"] for c in affected] if replacements else []))
