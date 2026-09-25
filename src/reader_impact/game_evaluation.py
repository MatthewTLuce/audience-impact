"""Multi-work local engineering evaluation. Expected answers are scorer-only."""
from pathlib import Path, PurePosixPath
from collections import Counter
import json
import uuid
from .domain import BoundaryError, canonical, fingerprint, identifier
from .storage import Store
from .ingest import ingest, privacy_review
from .analysis import analyze, validate
from .reports import report_data, render
from .evaluation import score, ratio


def load_manifest(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    if (manifest.get("version") != "narrative-games-v1" or manifest.get("synthetic") is not True
        or manifest.get("domain") != "narrative-game" or not isinstance(manifest.get("works"), list)):
        raise BoundaryError("Only the shipped synthetic narrative-game manifest is supported.")
    seen_works, seen_files = set(), set()
    if not manifest["works"]:
        raise BoundaryError("Fixture manifest has no works.")
    for work in manifest["works"]:
        wid = identifier(work["work_id"])
        if wid in seen_works or work["partition"] not in {"development", "evaluation"}:
            raise BoundaryError("A work must belong to exactly one partition.")
        seen_works.add(wid)
        if not isinstance(work["files"],list) or not work["files"]:
            raise BoundaryError("Each fixture work requires an explicit file list.")
        for name in work["files"]:
            relative = PurePosixPath(name)
            if (relative.is_absolute() or len(relative.parts)!=3 or relative.parts[:2] != ("reviews",wid)
                or relative.suffix != ".txt" or ".." in relative.parts or name in seen_files):
                raise BoundaryError("Manifest paths must select unique ordinary review files under their work.")
            path = root.joinpath(*relative.parts)
            if path.resolve() != path.absolute() or not path.is_file():
                raise BoundaryError("Fixture input missing or symlinked.")
            seen_files.add(name)
    return manifest


def evaluate_games(root, output, partition="development"):
    if partition not in {"development", "evaluation", "all"}:
        raise BoundaryError("Unknown evaluation partition.")
    root, output = Path(root), Path(output)
    manifest = load_manifest(root)
    works = [w for w in manifest["works"] if partition=="all" or w["partition"]==partition]
    if not works:
        raise BoundaryError("No works in selected partition.")
    destination = output / ("game-evaluation-"+uuid.uuid4().hex)
    destination.mkdir(parents=True, mode=0o700)
    store = Store(destination / "private")
    frozen_runs, source_fingerprints = {}, []
    seen_hashes = {}
    # All selected works are analyzed and serialized BEFORE any expected key read.
    for work in works:
        wid = work["work_id"]
        store.init(wid, domain="narrative-game", work_id=wid, partition=work["partition"])
        for name in work["files"]:
            path = root/name
            digest = fingerprint(path.read_bytes())
            if digest in seen_hashes and seen_hashes[digest] != work["partition"]:
                raise BoundaryError("Exact review copy spans development and evaluation partitions.")
            seen_hashes[digest] = work["partition"]
            source_fingerprints.append(dict(file=name,sha256=digest))
            ingest(store,wid,path,authorized=True)
        for r in store.reviews(wid):
            privacy_review(store,wid,r["review_id"],"fixture-operator","Synthetic engineering fixture only")
        analyze(store,wid)
        data = report_data(store,wid)
        payload, page = canonical(data), render(data)
        directory = destination/wid
        directory.mkdir(mode=0o700)
        for name, content in (("analysis.json",payload),("analysis.html",page)):
            (directory/name).write_text(content)
            (directory/name).chmod(0o600)
        frozen_runs[wid] = (data,payload,page)
    keys = {}
    for work in works:
        wid = work["work_id"]
        keys[wid] = json.loads((root/"hidden_keys"/(wid+".json")).read_text())
        if keys[wid].get("version") != manifest["version"]:
            raise BoundaryError("Scorer and fixture versions differ.")
    summaries=[]
    for work in works:
        wid=work["work_id"]
        data,payload,page=frozen_runs[wid]
        expected=keys[wid]
        selected={r["review_id"] for r in store.reviews(wid)}
        if selected != set(expected["cases"]):
            raise BoundaryError("Scorer review IDs do not match the imported corpus.")
        metrics=score(data,dict(cases=expected["cases"],canary=expected["canary"]),store.rows("source",wid))
        observed_context=Counter((e["review_id"],o["impact_category"]) for o in data["context_observations"] for e in o["evidence"])
        expected_context=Counter((rid,c) for rid,case in expected["cases"].items() for c in case["context_categories"])
        matched=sum((observed_context & expected_context).values())
        metrics["provisional_semantic"].update(context_category_precision=ratio(matched,sum(observed_context.values())),
                                               context_category_recall=ratio(matched,sum(expected_context.values())))
        _,failures=validate(dict(observations=data["observations"]+data["context_observations"]),store.reviews(wid),"narrative-game")
        mechanical=metrics["mechanical"]
        mechanical.update(invalid_evidence_count=len(failures)+len(data["validation_failures"]),
            hidden_key_leakage=expected["canary"] in payload or expected["canary"] in page,
            context_in_narrative_count=sum(o["impact_category"]!="narrative" for o in data["observations"]),
            audit_chain_valid=store.verify())
        passed=(all(not mechanical[k] for k in ("invalid_evidence_count","inappropriate_hypotheses","duplicate_inflation_count",
            "unsupported_surface_fact_count","instruction_review_contributions","hidden_key_leakage","context_in_narrative_count"))
            and mechanical["exact_duplicates_detected"]==expected["expected_exact_duplicates"]
            and mechanical["audit_chain_valid"])
        summary=dict(work_id=wid,partition=work["partition"],mechanical_pass=passed,
            analysis_sha256=fingerprint(payload.encode()),review_count=len(selected),
            narrative_observation_count=len(data["observations"]),context_observation_count=len(data["context_observations"]),
            hypothesis_count=len(data["hypotheses"]),metrics=metrics)
        summaries.append(summary)
        store.add("evaluation",wid,dict(**summary,fixture_version=manifest["version"],profile_version="narrative-game-v1",
            configuration=store.corpus(wid)["config"],selected_review_ids=sorted(selected),
            report_sha256=fingerprint(canonical(summary).encode())))
        for name,content in (("evaluation.json",canonical(summary)),("evaluation.html",render(data,summary))):
            (destination/wid/name).write_text(content)
            (destination/wid/name).chmod(0o600)
    result=dict(fixture_version=manifest["version"],profile_version="narrative-game-v1",partition=partition,
        fixture_sha256=fingerprint(canonical(dict(manifest=manifest,sources=source_fingerprints)).encode()),
        mechanical_pass=all(s["mechanical_pass"] for s in summaries),works=summaries,
        limitations=["Synthetic engineering fixtures; not independent real-player validation.",
            "Whole-work evaluation partition tests separation; its author knew the rules.",
            "The analysis provider receives no partition or expected answers.",
            "Semantic metrics and commercial appropriateness are provisional, not acceptance thresholds.",
            "No external source, model, acquisition permission or commercial approval is enabled."])
    (destination/"evaluation.json").write_text(canonical(result))
    (destination/"evaluation.json").chmod(0o600)
    # Standalone aggregate overview contains no per-case answers or private paths.
    import html
    body=html.escape(json.dumps(result,indent=2))
    (destination/"evaluation.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>Audience Impact evaluation</title><style>body{max-width:1000px;margin:40px auto;padding:20px;font:17px/1.6 system-ui;color:#24313a}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f4f3;padding:20px}</style><h1>Audience Impact evaluation</h1><p>Synthetic narrative-game engineering fixtures. These results do not establish real-player accuracy or commercial viability.</p><pre>'+body+'</pre></html>')
    (destination/"evaluation.html").chmod(0o600)
    store.db.close()
    if not result["mechanical_pass"]:
        raise BoundaryError("Game fixture safeguards failed; inspect "+str(destination))
    return dict(mechanical_pass=result["mechanical_pass"],output=str(destination),partition=partition,
                works=[dict(work_id=s["work_id"],reviews=s["review_count"],metrics=s["metrics"]["provisional_semantic"]) for s in summaries])
