from pathlib import Path
import json
import socket
import pytest
from reader_impact.evaluation import evaluate

def test_end_to_end_blinding(tmp_path,monkeypatch):
    root=Path(__file__).parent/'fixtures'
    original=Path.read_text
    key_reads=[]
    # Ensure the engine cannot read a hidden key during analysis.
    from reader_impact.analysis import DeterministicEngine
    propose=DeterministicEngine.propose
    active=[False]
    def guarded_read(path,*a,**kw):
        if 'hidden_keys' in path.parts:
            assert not active[0]
            key_reads.append(path)
        return original(path,*a,**kw)
    def guarded_propose(self,reviews):
        active[0]=True
        try:
            assert all(set(r)=={'review_id','text','source_hash','version'} for r in reviews)
            return propose(self,reviews)
        finally: active[0]=False
    def deny(*a,**kw): raise AssertionError('network attempted')
    monkeypatch.setattr(Path,'read_text',guarded_read)
    monkeypatch.setattr(DeterministicEngine,'propose',guarded_propose)
    monkeypatch.setattr(socket,'socket',deny)
    result=evaluate(root,tmp_path/'out')
    assert result['mechanical_pass'] and len(key_reads)==1
    output=Path(result['output'])
    for name in ['analysis.json','analysis.html','evaluation.json','evaluation.html']:
        text=(output/name).read_text()
        assert 'PRIVATE_GROUND_TRUTH' not in text and 'expected.json' not in text and 'Avery Tester' not in text
    metrics=json.loads((output/'evaluation.json').read_text())['metrics']
    assert metrics['provisional_semantic']['signal_recall']<1
    assert metrics['provisional_semantic']['clustering_pair_recall']<1
    assert metrics['mechanical']['duplicate_inflation_count']==0
