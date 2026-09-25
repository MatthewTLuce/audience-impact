import sqlite3
import json
from pathlib import Path
import pytest
from reader_impact.storage import Store
from reader_impact.domain import BoundaryError, CONFIG
from reader_impact.cli import main
from reader_impact.ingest import ingest, privacy_review
from reader_impact.analysis import analyze

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path/'private'); s.init('test'); return s

@pytest.fixture
def ready(store,tmp_path):
    path=tmp_path/'review.txt'; path.write_text('The lantern gave hope.'); rid=ingest(store,'test',path,authorized=True)
    privacy_review(store,'test',rid,'operator','Reviewed synthetic input')
    return store

def test_defaults_and_audit(store):
    assert store.corpus('test')['config']==CONFIG
    assert not any(CONFIG[k] for k in ('manuscript_access','remote_model_calls','external_connectors'))
    assert store.verify()
    assert (store.root.stat().st_mode & 0o777)==0o700
    assert ((store.root/'state.sqlite3').stat().st_mode & 0o777)==0o600

@pytest.mark.parametrize('table',['records','audit'])
@pytest.mark.parametrize('operation',['UPDATE {table} SET seq=seq','DELETE FROM {table}'])
def test_append_only(store,table,operation):
    with pytest.raises(sqlite3.IntegrityError,match='append only'):
        store.db.execute(operation.format(table=table))

@pytest.mark.parametrize('identifier',['../escape','','a/b','a'*65])
def test_bad_corpus(store,identifier):
    with pytest.raises(BoundaryError): store.init(identifier)

def test_replacement_fails(store):
    with pytest.raises(BoundaryError): store.init('test')

@pytest.mark.parametrize('command',['scrape','publish','message','remote','product-brief'])
def test_unsupported_cli(command):
    with pytest.raises(SystemExit) as exc: main([command])
    assert exc.value.code==2

def test_no_remote(ready):
    with pytest.raises(BoundaryError,match='offline'): analyze(ready,'test','remote')

def test_authorization_required(store,tmp_path):
    path=tmp_path/'review.txt'; path.write_text('The lantern gave hope.')
    with pytest.raises(BoundaryError,match='authorization'): ingest(store,'test',path)

@pytest.mark.parametrize('name',['manuscript.txt','synopsis.txt','questionnaire.txt','hidden_keys.txt','character-bible.txt'])
def test_prohibited_inputs(store,tmp_path,name):
    path=tmp_path/name; path.write_text('Do not read')
    with pytest.raises(BoundaryError,match='category'): ingest(store,'test',path,authorized=True)
    assert not store.rows('source','test')

def test_directory_cli_blocked(store,tmp_path):
    assert main(['--data',str(store.root),'ingest','--corpus','test','--authorized-local-reviews',str(tmp_path)])==2
