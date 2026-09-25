"""Blinded analysis completes before the scorer opens its separate expected key."""
from pathlib import Path
import json
import uuid
from contextlib import nullcontext
from itertools import combinations
from .storage import Store, now
from .ingest import ingest, privacy_review
from .analysis import analyze, validate
from .reports import report_data, render, write_reports
from .domain import canonical, fingerprint, BoundaryError

def ratio(a,b):
    return a/b if b else None

def score(data, key, sources):
    expected = {(rid, emotion) for rid,c in key['cases'].items() for emotion in c['emotions']}
    actual = {(e['review_id'],o['expressed_emotion']) for o in data['observations'] for e in o['evidence']}
    expected_abstain = {rid for rid,c in key['cases'].items() if c['abstention']}
    actual_abstain = {a['review_id'] for a in data['abstentions']}
    expected_pairs = {tuple(sorted((a,b))) for a,b in combinations(key['cases'],2)
                      if key['cases'][a]['group'] and key['cases'][a]['group']==key['cases'][b]['group']}
    actual_pairs = set()
    for c in data['clusters']:
        ids = sorted(set(e['review_id'] for e in c['evidence']))
        actual_pairs.update(combinations(ids,2))
    inappropriate = sum(any(key['cases'][e['review_id']]['sensitive'] for e in h['evidence']) for h in data['hypotheses'])
    injection_ids = {rid for rid,c in key['cases'].items() if c['abstention']=='instruction_like_text'}
    copy_ids = {rid for rid,c in key['cases'].items() if c['abstention']=='possible_copy_or_near_duplicate'}
    contributing = {e['review_id'] for c in data['clusters'] for e in c['evidence']}
    unsupported = sum(o['expressed_emotion'].lower() not in ' '.join(e['quote'].lower() for e in o['evidence'])
                      or (o['referent_phrase']!='unresolved' and o['referent_phrase'] not in ' '.join(e['quote'].lower() for e in o['evidence']))
                      for o in data['observations'])
    all_pairs = set(combinations(sorted(key['cases']),2))
    return dict(
        provisional_semantic=dict(signal_precision=ratio(len(actual&expected),len(actual)), signal_recall=ratio(len(actual&expected),len(expected)),
          clustering_pair_precision=ratio(len(actual_pairs&expected_pairs),len(actual_pairs)),
          clustering_pair_recall=ratio(len(actual_pairs&expected_pairs),len(expected_pairs)),
          clustering_pair_accuracy=ratio(len(all_pairs-(actual_pairs^expected_pairs)),len(all_pairs)),
          abstention_precision=ratio(len(expected_abstain&actual_abstain),len(actual_abstain)),
          abstention_recall=ratio(len(expected_abstain&actual_abstain),len(expected_abstain)),
          commercial_appropriateness=ratio(len(data['hypotheses'])-inappropriate,len(data['hypotheses']))),
        mechanical=dict(evidence_coverage=ratio(sum(bool(o['evidence']) for o in data['observations']),len(data['observations'])),
          invalid_evidence_count=len(data['validation_failures']), inappropriate_hypotheses=inappropriate,
          exact_duplicates_detected=sum(s['status']=='duplicate' for s in sources),
          duplicate_inflation_count=len(copy_ids&contributing), unsupported_surface_fact_count=unsupported,
          instruction_review_contributions=len(injection_ids&contributing),
          hidden_key_leakage=key['canary'] in canonical(data)),
        limitations=['Surface-fact check is not a general factuality metric.',
          'Instruction non-execution is also tested with side-effect sentinels and network denial in the test suite.',
          'The synthetic fixture key is engineered, not independent reader ground truth.',
          'Pair accuracy includes many unrelated pairs; inspect pair recall too.'])

def evaluate(fixture_root, output):
    fixture_root, output = Path(fixture_root), Path(output)
    if not (fixture_root/'reviews').is_dir():
        raise BoundaryError('Fixture suite missing; run from the documented source checkout.')
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    destination = output / ('evaluation-' + uuid.uuid4().hex)
    destination.mkdir(mode=0o700)
    with nullcontext():
        store = Store(destination/'private')
        store.init('synthetic-v1')
        paths = sorted((fixture_root/'reviews').glob('*.txt'))
        for path in paths:
            ingest(store,'synthetic-v1',path,identities=['Avery Tester'],authorized=True)
        for r in store.reviews('synthetic-v1'):
            privacy_review(store,'synthetic-v1',r['review_id'],'fixture-operator','Synthetic fixture privacy approval')
        analyze(store,'synthetic-v1')
        data = report_data(store,'synthetic-v1')
        # Freeze ordinary analysis and HTML BEFORE accessing expected answers.
        frozen = canonical(data)
        analysis_hash = fingerprint(frozen.encode())
        ordinary_html = render(data)
        key = json.loads((fixture_root/'hidden_keys'/'expected.json').read_text())
        metrics = score(data,key,store.rows('source','synthetic-v1'))
        if key['canary'] in frozen or key['canary'] in ordinary_html:
            raise BoundaryError('Hidden evaluation key leaked into analysis.')
        valid, invalid = validate(dict(observations=data['observations']),store.reviews('synthetic-v1'))
        mechanical = metrics['mechanical']
        mechanical['invalid_evidence_count'] = len(invalid)
        mechanical['audit_chain_valid'] = store.verify()
        passed = (not any(mechanical[k] for k in ('invalid_evidence_count','inappropriate_hypotheses','duplicate_inflation_count',
            'unsupported_surface_fact_count','instruction_review_contributions','hidden_key_leakage'))
            and mechanical['exact_duplicates_detected']==1 and mechanical['audit_chain_valid'])
        evaluation = dict(fixture_version=key['version'], fixture_fingerprint=fingerprint(b''.join(p.read_bytes() for p in paths)),
            engine=data['engine'], selected_review_ids=[r['review_id'] for r in store.reviews('synthetic-v1')],
            analysis_sha256=analysis_hash, mechanical_pass=passed, metrics=metrics,
            semantic_thresholds='Provisional; no release accuracy claim.')
        # Summary contains metrics, not per-case answers or expected signals.
        public_eval = evaluation
        run_id = store.add('evaluation','synthetic-v1',dict(**evaluation,report_sha256=fingerprint(canonical(public_eval).encode())))
        (destination/'analysis.json').write_text(frozen)
        (destination/'analysis.html').write_text(ordinary_html)
        (destination/'evaluation.json').write_text(canonical(public_eval))
        (destination/'evaluation.html').write_text(render(data,public_eval))
        for p in destination.iterdir():
            if p.is_file():
                p.chmod(0o600)
        if not passed:
            raise BoundaryError('Mechanical fixture safeguards failed; inspect '+str(destination))
        return dict(mechanical_pass=passed, output=str(destination), analysis_sha256=analysis_hash,
                    semantic_metrics=metrics['provisional_semantic'])
