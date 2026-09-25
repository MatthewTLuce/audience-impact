from pathlib import Path
import copy
import json
import socket
import pytest
from reader_impact.domain import BoundaryError, CONFIG, EvidenceSpan, canonical, fingerprint
from reader_impact.storage import Store
from reader_impact.profiles import classify, context, configuration
from reader_impact.analysis import DeterministicEngine, analyze, validate, cluster, make_cluster
from reader_impact.ingest import ingest, privacy_review
from reader_impact.reports import report_data, render
from reader_impact.review import decide
from reader_impact.cli import audience_main, main
from reader_impact.game_evaluation import evaluate_games, load_manifest

FIXTURES=Path(__file__).parent/'fixtures/narrative-games-v1'

def review(text, rid='R0001'):
    return dict(text=text,review_id=rid,source_hash=fingerprint(text.encode()),version=1)

def game_store(tmp_path, corpus='game'):
    s=Store(tmp_path/'private');s.init(corpus,domain='narrative-game',work_id=corpus,partition='development');return s

def import_review(s,tmp_path,text,corpus='game',name='review.txt'):
    p=tmp_path/name;p.write_text(text)
    rid=ingest(s,corpus,p,authorized=True)
    privacy_review(s,corpus,rid,'operator','Synthetic fixture checked')
    return rid

def test_legacy_corpus_and_audit_unchanged(tmp_path):
    s=Store(tmp_path/'private')
    # Exact old corpus shape, created without a domain or work field.
    s.add('corpus','legacy',dict(corpus_id='legacy',label='legacy',created_at='2026-09-07',config=CONFIG))
    raw=s.rows('corpus','legacy')[0]
    import_review(s,tmp_path,'The lantern gave hope.','legacy')
    analyze(s,'legacy')
    assert s.rows('corpus','legacy')[0]==raw
    assert report_data(s,'legacy')['scope']==dict(domain='book',profile_version='book-v1',work_id='legacy',partition='unassigned')
    assert s.verify()

def test_cli_new_default_and_legacy_default(tmp_path,capsys):
    args=['--data',str(tmp_path/'state'),'init','--corpus']
    assert audience_main(args+['new'])==0
    assert main(args+['old'])==0
    s=Store(tmp_path/'state')
    assert s.corpus('new')['domain']=='narrative-game'
    assert s.corpus('old')['domain']=='book'
    assert s.corpus('new')['config']==configuration('narrative-game')
    assert s.corpus('old')['config']==CONFIG
    assert audience_main(['--data',str(tmp_path/'state'),'inspect','--corpus','new'])==0
    assert 'narrative-game' in capsys.readouterr().out

@pytest.mark.parametrize('bad',['film','remote',None])
def test_unknown_profiles_fail_closed(tmp_path,bad):
    s=Store(tmp_path/'state')
    with pytest.raises(BoundaryError): s.init('x',domain=bad)
    assert not s.rows('corpus','x')

def test_work_partition_collision(tmp_path):
    s=game_store(tmp_path)
    with pytest.raises(BoundaryError,match='partition'):
        s.init('other',domain='narrative-game',work_id='game',partition='evaluation')
    assert not s.rows('corpus','other')

@pytest.mark.parametrize('text,category',[
 ('I loved the story ending.','narrative'),('I hated the controls.','gameplay'),
 ('I hated the crashes.','technical'),('I loved the discount.','price_value'),
 ('I hated the customer support.','service'),('I loved the ending but hated the combat.','mixed'),
 ('I loved it.','unresolved')])
def test_context_categories_with_real_offsets(text,category):
    records=[review(text)]
    raw=DeterministicEngine('narrative-game').propose(records)
    valid,failures=validate(raw,records,'narrative-game')
    assert not failures and len(valid)==1
    obs=valid[0];assert obs['impact_category']==category
    e=obs['evidence'][0];EvidenceSpan(**e).validate(records[0])
    for cue in obs['topic_cues']:
        assert e['quote'][cue['start']:cue['end']]==cue['quote']
    assert bool(cluster(valid))==(category=='narrative')

def test_nonnarrative_does_not_become_hypothesis(tmp_path):
    s=game_store(tmp_path)
    import_review(s,tmp_path,'I loved the controls because they were precise.')
    import_review(s,tmp_path,'The controls gave comfort during combat.','game','review2.txt')
    analyze(s,'game');data=report_data(s,'game')
    assert len(data['context_observations'])==2
    assert not data['observations'] and not data['clusters'] and not data['hypotheses']
    assert 'EXCLUDED FROM NARRATIVE CLUSTERS' in render(data)
    with pytest.raises(BoundaryError):make_cluster(data['context_observations'])

def test_mixed_review_retains_separate_narrative_sentence(tmp_path):
    s=game_store(tmp_path)
    import_review(s,tmp_path,'The farewell gave hope in the story. I hated the price.')
    analyze(s,'game');data=report_data(s,'game')
    assert len(data['observations'])==1 and len(data['context_observations'])==1
    assert data['context_observations'][0]['impact_category']=='price_value'

@pytest.mark.parametrize('phrase',['wrong game','different title','wrong book','coordinated campaign'])
def test_scope_cues(phrase):
    raw=DeterministicEngine('narrative-game').propose([review(f'This is the {phrase}. I loved the story.')])
    assert not raw['observations'] and raw['abstentions'][0]['reason']=='scope_or_coordination_concern'

def test_category_tampering_rejected():
    r=[review('I loved the controls.')];raw=DeterministicEngine('narrative-game').propose(r)
    raw['observations'][0]['impact_category']='narrative'
    valid,failed=validate(raw,r,'narrative-game')
    assert not valid and failed

def test_no_cross_work_grouping_or_decisions(tmp_path):
    s=game_store(tmp_path,'game-a')
    s.init('game-b',domain='narrative-game',work_id='game-b')
    import_review(s,tmp_path,'The farewell gave hope in the story.','game-a','a.txt')
    import_review(s,tmp_path,'I loved how the farewell was quiet in the dialogue.','game-b','b.txt')
    analyze(s,'game-a');analyze(s,'game-b')
    a,b=report_data(s,'game-a'),report_data(s,'game-b')
    assert a['scope']['work_id']!=b['scope']['work_id']
    assert not a['hypotheses'] and not b['hypotheses']
    with pytest.raises(BoundaryError):
        decide(s,'game-a',b['clusters'][0]['cluster_id'],'accepted','operator','Wrong work')

def test_privacy_and_unknowns_remain(tmp_path):
    s=game_store(tmp_path)
    import_review(s,tmp_path,'The farewell gave hope in the story. Email reviewer@example.invalid.')
    import_review(s,tmp_path,'I loved how the farewell was quiet in the dialogue.','game','b.txt')
    analyze(s,'game');data=report_data(s,'game')
    assert 'reviewer@example' not in canonical(data)
    assert data['hypotheses'][0]['status']=='proposed'
    assert set(data['hypotheses'][0]['unknowns'].values())=={'unknown'}
    assert data['clusters'][0]['distinct_reader_count'] is None

def test_evaluate_games_blinding_partition_and_network(tmp_path,monkeypatch):
    original_read=Path.read_text
    original_bytes=Path.read_bytes
    original_propose=DeterministicEngine.propose
    active=[False];key_reads=[]
    def read(path,*a,**kw):
        if 'hidden_keys' in path.parts:
            assert not active[0]
            assert path.name!='game-c.json'
            assert len(list((tmp_path/'out').glob('*/game-*/analysis.json')))==2
            key_reads.append(path)
        return original_read(path,*a,**kw)
    def read_bytes(path,*a,**kw):
        assert '/reviews/game-c/' not in str(path), 'Evaluation partition read during development run'
        return original_bytes(path,*a,**kw)
    def propose(self,records):
        active[0]=True
        try:
            assert all(set(r)=={'review_id','text','source_hash','version'} for r in records)
            return original_propose(self,records)
        finally: active[0]=False
    def deny(*a,**kw):raise AssertionError('Network attempted')
    monkeypatch.setattr(Path,'read_text',read)
    monkeypatch.setattr(Path,'read_bytes',read_bytes)
    monkeypatch.setattr(DeterministicEngine,'propose',propose)
    monkeypatch.setattr(socket,'socket',deny)
    result=evaluate_games(FIXTURES,tmp_path/'out','development')
    assert result['mechanical_pass'] and len(key_reads)==2
    assert {w['work_id'] for w in result['works']}=={'game-a','game-b'}
    for path in Path(result['output']).rglob('*'):
        if path.suffix in {'.json','.html'}:
            text=original_read(path)
            assert 'PRIVATE_GAME_KEY' not in text and 'hidden_keys' not in text
            assert 'context_categories' not in text # expected label field is scorer-only

@pytest.mark.parametrize('mutation',[
 lambda m:m['works'][0]['files'].__setitem__(0,'hidden_keys/expected.json'),
 lambda m:m['works'][0]['files'].__setitem__(0,'reviews/game-a/../../secret.txt'),
 lambda m:m['works'].append(copy.deepcopy(m['works'][0])),
 lambda m:m['works'][0].update(partition='invalid')])
def test_manifest_rejects_bad_scope(tmp_path,mutation):
    import shutil
    root=tmp_path/'fixtures';shutil.copytree(FIXTURES,root)
    m=json.loads((root/'manifest.json').read_text());mutation(m)
    (root/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(BoundaryError):load_manifest(root)

def test_exact_copy_across_partitions_rejected(tmp_path):
    import shutil
    root=tmp_path/'fixtures';shutil.copytree(FIXTURES,root)
    (root/'reviews/game-c/01.txt').write_bytes((root/'reviews/game-a/01.txt').read_bytes())
    with pytest.raises(BoundaryError,match='spans'):
        evaluate_games(root,tmp_path/'out','all')

def test_equal_text_in_different_works_has_distinct_ids(tmp_path):
    s=game_store(tmp_path,'a');s.init('b',domain='narrative-game',work_id='b')
    for corpus in ['a','b']:
        import_review(s,tmp_path,'The farewell gave hope in the story.',corpus,corpus+'.txt')
        analyze(s,corpus)
    a,b=report_data(s,'a'),report_data(s,'b')
    assert a['observations'][0]['observation_id']!=b['observations'][0]['observation_id']
    assert a['clusters'][0]['cluster_id']!=b['clusters'][0]['cluster_id']
    with pytest.raises(BoundaryError):
        decide(s,'a',b['clusters'][0]['cluster_id'],'accepted','operator','Other work')

def test_unsupported_profile_version_fails(tmp_path):
    s=Store(tmp_path/'state')
    s.add('corpus','invalid',dict(corpus_id='invalid',domain='narrative-game',
        config=configuration('narrative-game'),profile_version='unknown'))
    with pytest.raises(BoundaryError,match='profile version'):s.corpus('invalid')
