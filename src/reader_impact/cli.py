"""Explicit local actions only; no API key or connector options."""
import argparse
import json
import sys
from pathlib import Path
from .storage import Store
from .domain import BoundaryError
from .ingest import ingest, privacy_review
from .analysis import analyze
from .reports import write_reports
from .review import decide
from .profiles import PROFILES, PARTITIONS, context

def main(argv=None, *, default_domain="book"):
    p = argparse.ArgumentParser(description="Audience Impact Local Alpha — offline book and narrative-game review evidence")
    p.add_argument("--data", default="app-data", help="Private local state directory")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("init", "ingest", "inspect", "privacy-review", "analyze", "report", "decide", "audit"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--corpus", required=True, help="Anonymous corpus identifier")
        if name == "inspect":
            cmd.add_argument("--review", help="Show protected normalized text for local privacy review")
        if name == "init":
            cmd.add_argument("--label", default="Local study")
            cmd.add_argument("--domain", choices=list(PROFILES), default=default_domain)
            cmd.add_argument("--work", help="Anonymous ID for exactly one work; defaults to corpus ID")
            cmd.add_argument("--partition", choices=PARTITIONS, default="unassigned")
        if name == "ingest":
            cmd.add_argument("paths", nargs="+")
            cmd.add_argument("--authorized-local-reviews", action="store_true", help="Attest these are authorized ordinary reviews, never manuscripts or answer keys")
            cmd.add_argument("--identity", action="append", default=[], help="Identity to redact; visible in shell history, prefer private API mapping for real names")
        if name == "privacy-review":
            cmd.add_argument("--review", required=True)
            cmd.add_argument("--actor", required=True, help="Anonymous operator ID")
            cmd.add_argument("--reason", required=True)
            cmd.add_argument("--identity", action="append", default=[])
            cmd.add_argument("--exclude", action="store_true")
        if name == "analyze":
            cmd.add_argument("--engine", default="deterministic")
        if name == "report":
            cmd.add_argument("--out", default="outputs")
        if name == "decide":
            cmd.add_argument("--target", required=True)
            cmd.add_argument("--status", required=True, choices=["accepted","rejected","corrected","needs_review","split","merge"])
            cmd.add_argument("--actor", required=True)
            cmd.add_argument("--reason", required=True)
            cmd.add_argument("--groups", help='JSON list of lists of observation IDs for split/merge/correct')
    ev = sub.add_parser("evaluate")
    ev.add_argument("--fixture-suite", default="narrative-games-v1" if default_domain=="narrative-game" else "synthetic-v1",
                    choices=["synthetic-v1", "narrative-games-v1"])
    ev.add_argument("--partition", choices=["development", "evaluation", "all"], default="development")
    ev.add_argument("--out", default="outputs/evaluation")
    args = p.parse_args(argv)
    try:
        if args.command == "evaluate":
            from .evaluation import evaluate
            if args.fixture_suite == "synthetic-v1":
                if args.partition != "development":
                    raise BoundaryError("The legacy book suite has no evaluation partition.")
                result = evaluate(Path.cwd()/"tests"/"fixtures", Path(args.out))
            else:
                from .game_evaluation import evaluate_games
                result = evaluate_games(Path.cwd()/"tests"/"fixtures"/"narrative-games-v1", Path(args.out), args.partition)
        else:
            store = Store(args.data)
            if args.command == "init":
                result = store.init(args.corpus, args.label, args.domain, args.work, args.partition)
            elif args.command == "ingest":
                paths = []
                for name in args.paths:
                    path = Path(name)
                    # Never recurse into neighbouring manuscripts, questionnaires or keys.
                    if path.is_dir():
                        raise BoundaryError("Supply explicit review files; directory scanning is disabled.")
                    paths.append(path)
                result = [ingest(store,args.corpus,path,args.identity,args.authorized_local_reviews) for path in paths]
            elif args.command == "privacy-review":
                result = privacy_review(store,args.corpus,args.review,args.actor,args.reason,args.identity,not args.exclude)
            elif args.command == "analyze":
                result = analyze(store,args.corpus,args.engine)
            elif args.command == "report":
                result = write_reports(store,args.corpus,args.out)
            elif args.command == "decide":
                result = decide(store,args.corpus,args.target,args.status,args.actor,args.reason,json.loads(args.groups) if args.groups else None)
            elif args.command == "audit":
                store.corpus(args.corpus)
                result = dict(audit_valid=store.verify())
            else:
                store.corpus(args.corpus)
                if args.review:
                    review = next((r for r in store.reviews(args.corpus) if r["review_id"]==args.review),None)
                    if not review:
                        raise BoundaryError("Unknown review.")
                    print(json.dumps({k:review[k] for k in ("review_id","text","version","inclusion")},indent=2))
                    return 0
                result = dict(scope=context(store.corpus(args.corpus)), review_count=len(store.reviews(args.corpus)), analysis_status="available" if store.rows("analysis",args.corpus) else "not_run", config=store.corpus(args.corpus)["config"],
                    reviews=[{k:r[k] for k in ("review_id","version","inclusion")} for r in store.reviews(args.corpus)],
                    sources=[dict(source_document_id=s["json_id"],status=s["status"],reason=s.get("reason")) for s in store.rows("source",args.corpus)])
        print(json.dumps(result, indent=2))
        return 0
    except (BoundaryError, OSError, json.JSONDecodeError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 2

def audience_main(argv=None):
    return main(argv, default_domain="narrative-game")

if __name__ == "__main__":
    raise SystemExit(main())
