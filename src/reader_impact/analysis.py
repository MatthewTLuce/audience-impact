"""Conservative rule engine. Surface phrases are not canonical story entities."""
import re
from dataclasses import asdict
from difflib import SequenceMatcher
from .domain import EvidenceSpan, BoundaryError, fingerprint, canonical
from .profiles import get_profile, classify, context

VERSION = "deterministic-v1"
# Deliberately literal: synonyms of story referents are never silently merged.
EMOTIONS = r"\b(loved|love|moved|comfort|comforted|hope|hopeful|haunted|hated|hate|disgusted|grief|devastated|unforgettable)\b"
NEGATIVE = {"hated", "hate", "disgusted", "grief", "devastated", "haunted"}
SENSITIVE = r"\b(death|suicide|abuse|trauma|sacred|funeral|grief|devastated|murder)\b"
INJECTION = r"ignore.*instructions|system prompt|api[_ -]?key|exfiltrat|send.*https?://|run (?:this |the )?(?:command|shell)|<script"
REFERENT = r"\b(the final gift|that room|the [\w'-]+(?: [\w'-]+){0,2}?) (?=made|left|felt|was|gave|stayed|brought|meant)"

class DeterministicEngine:
    version = VERSION
    def __init__(self, domain="book"):
        self.profile = get_profile(domain)
        self.version = self.profile.engine_version

    def propose(self, reviews):
        observations, abstentions, duplicates = [], [], []
        prior = []
        for review in reviews:
            text, rid = review["text"], review["review_id"]
            reason = None
            compact = " ".join(re.findall(r"\w+", text.lower()))
            for other, other_compact in prior:
                shared = set(p.strip().lower() for p in text.split("\n") if len(p.strip()) >= 45) & set(p.strip().lower() for p in other["text"].split("\n"))
                if compact == other_compact or SequenceMatcher(None, compact, other_compact).ratio() >= .9 or shared:
                    reason = "possible_copy_or_near_duplicate"
                    duplicates.append(dict(review_id=rid, duplicate_of=other["review_id"], status="needs_review"))
                    break
            prior.append((review, compact))
            if reason is None and re.search(INJECTION, text, re.I):
                reason = "instruction_like_text"
            if reason is None and re.search(self.profile.scope_pattern, text, re.I):
                reason = "scope_or_coordination_concern"
            if reason:
                abstentions.append(dict(review_id=rid, reason=reason))
                continue
            count = 0
            for match in re.finditer(r"[^\n.!?]+[.!?]?", text):
                quote = match.group().strip()
                start = match.start() + len(match.group()) - len(match.group().lstrip())
                emotion = re.search(EMOTIONS, quote, re.I)
                if not emotion:
                    continue
                referent = re.search(REFERENT, quote, re.I)
                if not referent:
                    referent = re.search(r"\b(the final gift|that room)\b", quote, re.I)
                phrase = referent.group(1).lower() if referent else "unresolved"
                ambiguous = phrase in {"unresolved", "the final gift", "that room"}
                evidence = asdict(EvidenceSpan(rid, quote, start, start+len(quote), text[:start].count("\n")+1,
                    review["source_hash"], review["version"]))
                polarity = "negative" if emotion.group().lower() in NEGATIVE else "positive"
                observations.append(dict(observation_id="O-"+fingerprint(canonical(evidence).encode())[:16],
                    evidence=[evidence], expressed_emotion=emotion.group().lower(), referent_phrase=phrase,
                    referent_type="unresolved", polarity_interpretation=polarity, intensity_interpretation="unrated",
                    ambiguity_notes=["Surface phrase only; canonical identity and intensity unknown."] + (["Do not merge unresolved referents."] if ambiguous else []),
                    confidence="low", engine_version=self.version, ambiguous=ambiguous,
                    sensitivity_flags=["sensitive_language"] if re.search(SENSITIVE, quote, re.I) else []))
                if self.profile.domain == "narrative-game":
                    observations[-1].update(classify(quote))
                count += 1
            if not count:
                abstentions.append(dict(review_id=rid, reason="insufficient_rule_evidence"))
        return dict(observations=observations, abstentions=abstentions, duplicate_candidates=duplicates)

def validate(proposal, reviews, domain="book"):
    profile = get_profile(domain)
    lookup = {r["review_id"]:r for r in reviews}
    valid, failures, seen = [], [], set()
    for obs in proposal["observations"]:
        try:
            if not obs.get("evidence"):
                raise BoundaryError("Evidence-free proposal")
            for evidence in obs["evidence"]:
                EvidenceSpan(**evidence).validate(lookup[evidence["review_id"]])
            evidence_text = " ".join(e["quote"].lower() for e in obs["evidence"])
            if (not obs.get("expressed_emotion") or obs["expressed_emotion"].lower() not in evidence_text
                or obs.get("referent_type") != "unresolved"
                or (obs.get("referent_phrase") != "unresolved" and obs.get("referent_phrase", "") not in evidence_text)):
                raise BoundaryError("Unsupported surface interpretation or resolved canon in proposal.")
            if profile.domain == "narrative-game":
                if len(obs["evidence"]) != 1:
                    raise BoundaryError("Game rule proposals require one sentence evidence span.")
                expected_category = classify(obs["evidence"][0]["quote"])
                if any(obs.get(k) != v for k,v in expected_category.items()):
                    raise BoundaryError("Topic classification does not match quoted cues.")
            if obs["observation_id"] in seen:
                raise BoundaryError("Repeated observation identifier.")
            seen.add(obs["observation_id"])
            valid.append(obs)
        except (BoundaryError, KeyError, TypeError) as exc:
            failures.append(dict(observation_id=obs.get("observation_id"), reason=str(exc)))
    return valid, failures

def cluster(observations):
    groups = {}
    for observation in observations:
        if observation.get("impact_category", "narrative") != "narrative":
            continue
        key = observation["observation_id"] if observation["ambiguous"] else observation["referent_phrase"]
        groups.setdefault(key, []).append(observation)
    return [make_cluster(members) for members in groups.values()]

def make_cluster(members, rationale=None, cluster_id=None):
    if any(o.get("impact_category", "narrative") != "narrative" for o in members):
        raise BoundaryError("Only narrative observations can form an impact cluster.")
    ids = sorted(o["observation_id"] for o in members)
    evidence = [e for o in members for e in o["evidence"]]
    readers = sorted(set(e["review_id"] for e in evidence))
    polarities = sorted(set(o["polarity_interpretation"] for o in members))
    return dict(cluster_id=cluster_id or "C-"+fingerprint(canonical(ids).encode())[:16], member_observations=ids,
        shared_description="Audience wording: " + " / ".join(sorted(set(o["referent_phrase"] for o in members))),
        evidence=evidence, mention_count=len(members), distinct_review_count=len(readers),
        distinct_reader_count=None, reader_count_note="Independent reader identity is unverified; counts are distinct review records after conservative copy screening.",
        disagreements=polarities if len(polarities)>1 else [],
        outliers=[o["observation_id"] for o in members if o["ambiguous"]],
        merge_rationale=rationale or "Exact surface phrase match only; unresolved phrases stay separate. No canonical equivalence inferred.",
        confidence="low", status="proposed", sensitivity_flags=sorted(set(f for o in members for f in o["sensitivity_flags"])))

def hypotheses(clusters, domain="book"):
    get_profile(domain)
    result = []
    for c in clusters:
        if c["sensitivity_flags"] or c["outliers"] or c["distinct_review_count"] < 2:
            continue
        result.append(dict(hypothesis_id="H-"+c["cluster_id"][2:], type="commercial_opportunity_hypothesis",
            originating_cluster_id=c["cluster_id"], category="Optional reader reflection experience" if domain=="book" else "Optional audience reflection experience",
            rationale="Repeated review wording could justify asking participants about an optional reflection experience. Demand is untested.",
            evidence=c["evidence"], sensitivity_flags=c["sensitivity_flags"], appropriateness="requires_human_review",
            unknowns={k:"unknown" for k in ("rights", "safety", "manufacturing", "cost", "price", "demand", "fulfillment", "margin")},
            status="proposed"))
    return result

def analyze(store, corpus, engine="deterministic"):
    scope = context(store.corpus(corpus))
    if engine != "deterministic":
        raise BoundaryError("Only the offline deterministic engine is enabled.")
    current = store.reviews(corpus)
    if any(r["inclusion"] == "pending_privacy_review" for r in current):
        raise BoundaryError("Privacy review is required for every pending review before analysis.")
    reviews = [r for r in current if r["inclusion"] == "included"]
    # Provider contract excludes filenames, mappings, originals and hidden keys.
    safe = [{k:r[k] for k in ("review_id", "text", "source_hash", "version")} for r in reviews]
    provider = DeterministicEngine(scope["domain"])
    proposal = provider.propose(safe)
    proposal_id = store.add("proposal", corpus, dict(engine=provider.version, scope=scope, proposal=proposal))
    valid, failures = validate(proposal, safe, scope["domain"])
    if scope["domain"] == "narrative-game":
        for obs in valid:
            # Equal text/anonymous R-numbers in different works must not share IDs.
            provider_id = obs["observation_id"]
            obs["provider_observation_id"] = provider_id
            obs["observation_id"] = "O-" + fingerprint(canonical([corpus, scope["work_id"], provider_id]).encode())[:16]
            obs["work_id"] = scope["work_id"]
    narrative = [o for o in valid if o.get("impact_category", "narrative") == "narrative"]
    other = [o for o in valid if o.get("impact_category", "narrative") != "narrative"]
    clusters = cluster(narrative)
    result = dict(engine=provider.version, scope=scope, context_observations=other, proposal_id=proposal_id, selected_reviews=[dict(review_id=r["review_id"],version=r["version"]) for r in safe],
        observations=narrative, clusters=clusters, hypotheses=hypotheses(clusters, scope["domain"]), validation_failures=failures,
        abstentions=proposal["abstentions"], duplicate_candidates=proposal["duplicate_candidates"])
    return store.add("analysis", corpus, result)
