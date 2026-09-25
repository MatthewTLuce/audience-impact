"""Versioned domain vocabulary; never a source of story facts."""
from dataclasses import dataclass
import re
from .domain import BoundaryError

@dataclass(frozen=True)
class Profile:
    domain: str
    version: str
    engine_version: str
    scope_pattern: str

PROFILES = {
    "book": Profile("book", "book-v1", "deterministic-v1",
        r"wrong (?:book|series)|different (?:book|series)|review bomb|one.star campaign|coordinated campaign"),
    "narrative-game": Profile("narrative-game", "narrative-game-v1", "deterministic-game-v1",
        r"wrong (?:game|book|series|title)|different (?:game|book|series|title)|review bomb|one.star campaign|coordinated campaign"),
}
PARTITIONS = ("unassigned", "development", "evaluation")
# These are literal topic cues, not inferred canon or psychological labels.
TOPICS = {
    "narrative": r"\b(story|narrative|characters?|relationships?|dialogue|ending|farewell|companions?|reunion|betrayal|final gift|that room|funeral|sacred|grief)\b",
    "gameplay": r"\b(gameplay|combat|controls?|puzzles?|difficulty|mechanics?|boss fight|platforming|inventory|crafting)\b",
    "technical": r"\b(crash(?:es|ed|ing)?|bugs?|fps|frame rate|framerate|stutter(?:s|ing)?|performance|load(?:ing)? times?|optimization|resolution)\b",
    "price_value": r"\b(price|pricing|cost|expensive|cheap|discount|value for money|worth the money)\b",
    "service": r"\b(customer support|customer service|refunds?|support team|help desk)\b",
}
CATEGORIES = frozenset((*TOPICS, "mixed", "unresolved"))

def get_profile(domain):
    try:
        return PROFILES[domain]
    except (KeyError, TypeError):
        raise BoundaryError("Unsupported domain; use book or narrative-game.") from None

def classify(quote):
    cues = [dict(topic=topic, quote=m.group(), start=m.start(), end=m.end())
            for topic, pattern in TOPICS.items() for m in re.finditer(pattern, quote, re.I)]
    topics = sorted(set(c["topic"] for c in cues))
    return dict(impact_category=topics[0] if len(topics)==1 else "mixed" if topics else "unresolved",
                topic_cues=cues,
                category_note="Literal sentence-level topic cues; mixed and unresolved reactions require human interpretation.")

def context(corpus):
    profile = get_profile(corpus.get("domain", "book"))
    return dict(domain=profile.domain, profile_version=profile.version,
                work_id=corpus.get("work_id", corpus["corpus_id"]), partition=corpus.get("partition", "unassigned"))


def configuration(domain):
    from .domain import CONFIG
    profile = get_profile(domain)
    return dict(CONFIG) if domain=="book" else dict(CONFIG, version="2", engine=profile.engine_version)
