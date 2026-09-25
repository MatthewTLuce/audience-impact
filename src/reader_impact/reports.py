"""Anonymous analysis reports. Ground truth is never accepted by this module."""
from pathlib import Path
import html
from .domain import canonical, fingerprint, BoundaryError
from .review import latest
from .profiles import context

NOTICE = "Synthetic/offline engineering results are not evidence of audience-impact accuracy or commercial viability. All hypotheses require human review."

def report_data(store, corpus):
    run = latest(store, corpus)
    decisions = [d for d in store.rows("decision", corpus) if d["analysis_id"] == run["json_id"]]
    # Actors and free-text decision notes are protected operator data; ordinary reports
    # use statuses only. Structural rationales are private for the same reason.
    public_decisions = []
    for d in decisions:
        replacements = []
        for c in d["replacements"]:
            c = dict(c, merge_rationale="Human regrouping; private audit holds the rationale.")
            replacements.append(c)
        public_decisions.append(dict(target=d["target"], status=d["status"], replacements=replacements,
                                     affected_clusters=d["affected_clusters"]))
    return dict(schema_version="2", scope=run.get("scope", context(store.corpus(corpus))), context_observations=run.get("context_observations", []), notice=NOTICE, analysis_id=run["json_id"], engine=run["engine"],
        observations=run["observations"], clusters=run["clusters"], hypotheses=run["hypotheses"],
        abstentions=run["abstentions"], duplicate_candidates=run["duplicate_candidates"],
        validation_failures=run["validation_failures"], human_decision_history=public_decisions,
        review_manifest=[dict(review_id=r["review_id"], normalization_version=r["version"],
                            inclusion=r["inclusion"]) for r in store.reviews(corpus)])

def render(data, evaluation=None):
    import json
    esc = lambda v: html.escape(str(v), quote=True)

    def evidence_html(items):
        return "".join(
            f'<blockquote>{esc(e["quote"])}<footer>{esc(e["review_id"])} · paragraph {e["paragraph"]} · '
            f'offsets {e["start"]}–{e["end"]} · normalization v{e["normalization_version"]}'
            f'<br>SHA-256 {esc(e["source_hash"])}</footer></blockquote>' for e in items)

    scope = data.get("scope", {})
    scope_html = " · ".join(esc(scope.get(k,"unspecified")) for k in ("domain","work_id","partition"))
    cards = []
    for c in data["clusters"]:
        cards.append(f'<article><p class="tag">{esc(c["cluster_id"])} · ORIGINAL PROPOSAL</p>'
            f'<h2>{esc(c["shared_description"])}</h2><p>{c["mention_count"]} mentions · '
            f'{c["distinct_review_count"]} distinct review records · participant identity unverified</p>'
            f'<p>{esc(c["merge_rationale"])}</p>'
            f'<p>Disagreement: {esc(", ".join(c["disagreements"]) or "None detected by rules")} · '
            f'Sensitivity: {esc(", ".join(c["sensitivity_flags"]) or "Unassessed beyond narrow rules")}</p>'
            + evidence_html(c["evidence"]) + '</article>')
    context_cards = []
    for o in data.get("context_observations", []):
        context_cards.append('<article><p class="tag">'+esc(o["impact_category"].replace("_"," ").upper())+
            ' · EXCLUDED FROM NARRATIVE CLUSTERS</p><p>'+esc(o["category_note"])+
            '</p>'+evidence_html(o["evidence"])+'</article>')
    hyps = "".join(f'<article><p class="tag">COMMERCIAL OPPORTUNITY HYPOTHESIS · ORIGINAL PROPOSAL</p>'
        f'<h3>{esc(h["category"])}</h3><p>{esc(h["rationale"])}</p>'
        f'<p>Evidence cluster: {esc(h["originating_cluster_id"])}</p>'
        f'<p>{esc(" · ".join(k+": "+v for k,v in h["unknowns"].items()))}</p></article>' for h in data["hypotheses"])
    abstentions = "".join(f'<li>{esc(a["review_id"])}: {esc(a["reason"])}</li>' for a in data["abstentions"])
    metrics = ""
    if evaluation:
        metrics = '<h2>Engineering evaluation</h2><p>Semantic scores are provisional fixture measurements. '
        metrics += 'They do not establish usefulness on real reviews.</p><pre>'+esc(json.dumps(evaluation,indent=2))+'</pre>'
    style = """body{font:17px/1.6 system-ui,sans-serif;color:#24313a;background:#f2f4f3;max-width:980px;margin:40px auto;padding:0 24px}
    h1{font-size:40px;line-height:1.15}h2{line-height:1.3}article{background:white;padding:24px;margin:24px 0;border:1px solid #ccd6d2;border-radius:12px}
    .notice{background:#fff1d5;padding:20px;border-left:4px solid #b37a18}.tag{font-size:12px;letter-spacing:.06em;color:#48635d;overflow-wrap:anywhere}
    blockquote{border-left:3px solid #86a39a;margin:16px 0;padding:8px 16px;overflow-wrap:anywhere}footer{font-size:12px;color:#52616b;overflow-wrap:anywhere}
    pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}li{margin:8px 0}"""
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>Audience Impact — Local Alpha</title><style>'+style+'</style><main>'
        '<p class="tag">LOCAL REVIEW WORKBENCH · ENGINEERING ALPHA</p><h1>Audience impact evidence</h1>'
        '<p class="notice">'+esc(data["notice"])+'</p><p>'+scope_html+'</p><p>Engine: '+esc(data["engine"])+
        ' · '+str(len(data["observations"]))+' narrative candidates · '+str(len(data["clusters"]))+' proposed clusters</p>'+
        metrics+'<h2>Narrative evidence clusters</h2>'+(''.join(cards) or '<p>No narrative clusters proposed.</p>')+
        '<h2>Gameplay, technical, value, service and uncertain reactions</h2>'+
        '<p>These quoted reactions remain inspectable but do not support narrative opportunity hypotheses. '
        'Mixed topics and absent cues require human interpretation. Categorization is a narrow rule baseline.</p>'+
        (''.join(context_cards) or '<p>No separate context observations in this run.</p>')+
        '<h2>Hypotheses for human consideration</h2>'+(hyps or '<p>Withheld: insufficient, ambiguous, or sensitive evidence.</p>')+
        '<h2>Abstentions and copy screening</h2><ul>'+abstentions+'</ul><h2>Human decision history</h2><pre>'+
        esc(json.dumps(data["human_decision_history"],indent=2))+'</pre><p>Original proposals are preserved above. '
        'Decisions are scoped to this analysis; corrected groupings do not automatically approve hypotheses.</p></main></html>')

def write_reports(store, corpus, directory):
    data = report_data(store, corpus)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    base = data["analysis_id"]
    # A decision changes the digest, producing a new snapshot rather than overwriting.
    digest = fingerprint(canonical(data).encode())
    base += "-" + digest[:12]
    for ext, content in (("json", canonical(data)), ("html", render(data))):
        path = directory / (base + "." + ext)
        if path.exists() and path.read_text() != content:
            raise BoundaryError("Report snapshot conflict.")
        if not path.exists():
            with path.open("x", encoding="utf-8") as handle:
                handle.write(content)
            path.chmod(0o600)
    store.add("report", corpus, dict(analysis_id=data["analysis_id"], sha256=digest))
    return dict(json=str(directory/(base+".json")), html=str(directory/(base+".html")))
