from io import BytesIO
from pathlib import Path
import zipfile
import json
import pytest
from pypdf import PdfWriter
from reportlab.pdfgen.canvas import Canvas
from reader_impact.ingest import extract, ingest, privacy_review, MAX_BYTES
from reader_impact.storage import Store
from reader_impact.domain import BoundaryError, fingerprint
from reader_impact.analysis import analyze
from reader_impact.reports import report_data
from test_foundation import store, ready

def docx(text='The lantern gave hope.', extra=None):
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p></w:body></w:document>')
        if extra:
            for k,v in extra.items(): z.writestr(k,v)
    return stream.getvalue()

def pdf():
    stream=BytesIO(); c=Canvas(stream); c.drawString(60,750,'The lantern gave hope.'); c.save(); return stream.getvalue()

@pytest.mark.parametrize('ext,data',[('.txt',b'The lantern gave hope.'),('.docx',docx()),('.pdf',pdf())])
def test_formats(store,tmp_path,ext,data):
    p=tmp_path/('review'+ext); p.write_bytes(data)
    rid=ingest(store,'test',p,authorized=True)
    review=store.reviews('test')[0]
    assert 'The lantern gave hope.' in review['text']
    assert review['source_hash']==fingerprint(data)
    source=store.rows('source','test')[0]
    assert Path(source['managed_copy']).read_bytes()==data
    assert review['inclusion']=='pending_privacy_review'

def test_exact_duplicates(store,tmp_path):
    a=tmp_path/'a.txt'; a.write_text('The lantern gave hope.')
    b=tmp_path/'b.txt'; b.write_bytes(a.read_bytes())
    ingest(store,'test',a,authorized=True); ingest(store,'test',b,authorized=True)
    assert len(store.reviews('test'))==1
    assert store.rows('source','test')[1]['status']=='duplicate'

@pytest.mark.parametrize('ext,data,reason',[
    ('.txt',b'', 'empty'),('.txt',b'\xff','corrupt'),('.docx',b'bad','corrupt'),
    ('.pdf',b'bad','corrupt'),('.exe',b'text','unsupported'),('.txt',b'x'*(MAX_BYTES+1),'oversized'),
    ('.docx',docx(extra={'word/vbaProject.bin':b'x'}),'active'),
    ('.docx',docx(extra={'word/embeddings/object.bin':b'x'}),'embedded'),
    ('.docx',docx(extra={'word/_rels/document.xml.rels':'<Relationships><Relationship TargetMode="External" Target="https://invalid.example"/></Relationships>'}),'external'),
    ('.docx',docx('&unknown;'),'corrupt')])
def test_bad_files(ext,data,reason):
    with pytest.raises(BoundaryError,match=reason): extract(data,ext)

def test_pdf_encrypted_and_image_only():
    for encrypted in (True,False):
        writer=PdfWriter(); writer.add_blank_page(width=612,height=792)
        if encrypted: writer.encrypt('secret')
        stream=BytesIO(); writer.write(stream)
        with pytest.raises(BoundaryError,match='password' if encrypted else 'image-only'): extract(stream.getvalue(),'.pdf')

def test_pdf_script():
    writer=PdfWriter(); writer.add_blank_page(width=612,height=792); writer.add_js('app.alert("x")')
    stream=BytesIO(); writer.write(stream)
    with pytest.raises(BoundaryError,match='active'): extract(stream.getvalue(),'.pdf')

def test_quarantine_record(store,tmp_path):
    p=tmp_path/'bad.pdf'; p.write_bytes(b'bad')
    ingest(store,'test',p,authorized=True)
    assert store.rows('source','test')[0]['status']=='quarantined'
    assert not store.reviews('test')

def test_symlink(store,tmp_path):
    p=tmp_path/'a.txt'; p.write_text('hello'); link=tmp_path/'b.txt'; link.symlink_to(p)
    with pytest.raises(BoundaryError,match='symlink'): ingest(store,'test',link,authorized=True)

def test_privacy_versions_and_staleness(store,tmp_path):
    p=tmp_path/'PrivateReviewer.txt'; p.write_text('I am Avery Tester at avery@example.invalid. I loved the final gift.')
    rid=ingest(store,'test',p,authorized=True)
    with pytest.raises(BoundaryError,match='Privacy'): analyze(store,'test')
    privacy_review(store,'test',rid,'operator','Identity corrected',['Avery Tester'])
    analyze(store,'test'); data=json.dumps(report_data(store,'test'))
    assert 'Avery Tester' not in data and 'avery@' not in data and 'PrivateReviewer' not in data
    assert 'the final gift' in data
    assert 'Avery Tester' in store.rows('extracted','test')[0]['text']
    assert len(store.rows('review','test'))==2
    privacy_review(store,'test',rid,'operator','Exclude wrong study',include=False)
    with pytest.raises(BoundaryError,match='stale'): report_data(store,'test')
    assert store.verify()

def test_parser_timeout_quarantines(store,tmp_path,monkeypatch):
    import subprocess
    def timeout(*args,**kwargs): raise subprocess.TimeoutExpired('parser',10)
    monkeypatch.setattr(subprocess,'run',timeout)
    p=tmp_path/'review.txt'; p.write_text('The lantern gave hope.')
    ingest(store,'test',p,authorized=True)
    assert store.rows('source','test')[0]['status']=='quarantined'
    assert 'timeout' in store.rows('source','test')[0]['reason']

def test_zip_expansion_limit():
    data=docx(extra={'large.xml':'x'*(21*1024*1024)})
    # Compress the expanded payload below the input cap.
    source=zipfile.ZipFile(BytesIO(data)); out=BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in source.namelist(): z.writestr(name,source.read(name))
    with pytest.raises(BoundaryError,match='expansion'): extract(out.getvalue(),'.docx')

def test_audit_detects_source_tampering(ready):
    source=ready.rows('source','test')[0]
    p=Path(source['managed_copy']); p.chmod(0o600); p.write_bytes(b'changed')
    with pytest.raises(BoundaryError,match='fingerprint'): ready.verify()
