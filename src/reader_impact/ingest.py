"""Passive extraction. No relationship resolution, macros, scripts or OCR."""
from pathlib import Path
from io import BytesIO
import zipfile
import re
from defusedxml import ElementTree
from pypdf import PdfReader
from .domain import BoundaryError, fingerprint
from .storage import now

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 200_000

def extract(data, extension):
    if len(data) > MAX_BYTES:
        raise BoundaryError("oversized: limit is 10 MiB")
    try:
        if extension == ".txt":
            text = data.decode("utf-8-sig")
        elif extension == ".docx":
            with zipfile.ZipFile(BytesIO(data)) as archive:
                if sum(i.file_size for i in archive.infolist()) > 20 * 1024 * 1024:
                    raise BoundaryError("oversized DOCX expansion")
                if any("vbaproject" in n.lower() or "/embeddings/" in n.lower() for n in archive.namelist()):
                    raise BoundaryError("active or embedded DOCX content quarantined")
                for n in archive.namelist():
                    if n.endswith(".rels"):
                        rels = ElementTree.fromstring(archive.read(n))
                        if any(e.attrib.get("TargetMode") == "External" for e in rels):
                            raise BoundaryError("external DOCX relationship quarantined")
                root = ElementTree.fromstring(archive.read("word/document.xml"))
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                text = "\n".join("".join(e.text or "" for e in p.iter(ns + "t")) for p in root.iter(ns + "p"))
        elif extension == ".pdf":
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise BoundaryError("password-protected PDF")
            if len(reader.pages) > 100:
                raise BoundaryError("oversized PDF: maximum 100 pages")
            if any(token in data for token in (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile")):
                raise BoundaryError("active PDF content quarantined")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            raise BoundaryError("unsupported format: use UTF-8 TXT, DOCX or searchable PDF")
    except BoundaryError:
        raise
    except Exception as exc:
        raise BoundaryError("corrupt or unreadable document (" + type(exc).__name__ + ")") from None
    text = "\n".join(line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    if not text.strip():
        raise BoundaryError("empty or image-only document; OCR is disabled")
    if len(text) > MAX_TEXT:
        raise BoundaryError("oversized extracted text")
    return text

def extract_bounded(data, extension):
    import subprocess
    import sys
    import json
    if extension not in {".txt", ".pdf", ".docx"}:
        raise BoundaryError("unsupported format: use UTF-8 TXT, DOCX or searchable PDF")
    try:
        result = subprocess.run([sys.executable, "-m", "reader_impact.parse_worker", extension],
            input=data, capture_output=True, timeout=10, check=False)
    except subprocess.TimeoutExpired:
        raise BoundaryError("parser timeout: document quarantined") from None
    try:
        payload = json.loads(result.stdout)
    except (ValueError, UnicodeDecodeError):
        raise BoundaryError("parser failed or exceeded resource limit") from None
    if result.returncode or "error" in payload:
        raise BoundaryError(payload.get("error", "parser failed"))
    return payload["text"]


def deidentify(text, identities=()):
    actions = []
    for name in sorted(set(identities), key=len, reverse=True):
        if not name.strip():
            continue
        text, count = re.subn(r"(?<!\w)" + re.escape(name) + r"(?!\w)", "[IDENTITY]", text, flags=re.I)
        if count:
            actions.append(dict(kind="operator_identity", count=count))
    for pattern, replacement, kind in [
        (r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", "email"),
        (r"https?://\S+", "[URL]", "url"),
        (r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)", "[PHONE]", "phone")]:
        text, count = re.subn(pattern, replacement, text)
        if count:
            actions.append(dict(kind=kind, count=count))
    return text, actions

def ingest(store, corpus, path, identities=(), authorized=False, input_kind="review"):
    store.corpus(corpus)
    if not authorized or input_kind != "review":
        raise BoundaryError("Import requires explicit authorization of local review files only.")
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise BoundaryError("Input must be a regular local file, not a symlink.")
    if any(re.search(r"manuscript|synopsis|plot[-_ ]?outline|character[-_ ]?bible|hidden[-_ ]?keys?|questionnaire|answer[-_ ]?key", part, re.I) for part in path.parts):
        raise BoundaryError("Excluded input category; only ordinary review files are permitted.")
    if path.stat().st_size > MAX_BYTES:
        return store.add("source", corpus, dict(status="quarantined", reason="oversized: limit is 10 MiB", filename=path.name, imported_at=now()))
    data = path.read_bytes()
    sha = fingerprint(data)
    existing = next((s for s in store.rows("source", corpus) if s.get("sha256") == sha), None)
    source = dict(filename=path.name, extension=path.suffix.lower(), sha256=sha, size=len(data), imported_at=now(), warnings=[])
    if existing:
        source.update(status="duplicate", duplicate_of=existing["json_id"])
        return store.add("source", corpus, source)
    directory = store.root / "originals"
    directory.mkdir(exist_ok=True, mode=0o700)
    destination = directory / sha
    if not destination.exists():
        with destination.open("xb") as handle:
            handle.write(data)
        destination.chmod(0o400)
    elif fingerprint(destination.read_bytes()) != sha:
        raise BoundaryError("Managed original fingerprint mismatch.")
    source["managed_copy"] = str(destination)
    try:
        extracted = extract_bounded(data, path.suffix.lower())
    except BoundaryError as exc:
        source.update(status="quarantined", reason=str(exc))
        return store.add("source", corpus, source)
    source.update(status="extracted", warnings=["Passive extraction; metadata omitted. Privacy review required."])
    sid = store.add("source", corpus, source)
    store.add("extracted", corpus, dict(source_document_id=sid, text=extracted))
    rid = f"R{len(store.reviews(corpus)) + 1:04d}"
    text, actions = deidentify(extracted, identities)
    store.add("review", corpus, dict(review_id=rid, source_document_id=sid, source_hash=sha, text=text,
        paragraphs=paragraphs(text), actions=actions, version=1, inclusion="pending_privacy_review", exclusion_reason=None))
    if identities:
        store.add("identity", corpus, dict(review_id=rid, identities=list(identities), reason="import mapping"))
    return rid

def paragraphs(text):
    result, start = [], 0
    for i, line in enumerate(text.split("\n"), 1):
        result.append(dict(paragraph=i, start=start, end=start+len(line)))
        start += len(line) + 1
    return result

def privacy_review(store, corpus, rid, actor, reason, identities=(), include=True):
    store.corpus(corpus)
    if not actor.strip() or not reason.strip():
        raise BoundaryError("Human actor and reason are required.")
    prior = next((r for r in store.reviews(corpus) if r["review_id"] == rid), None)
    if not prior:
        raise BoundaryError("Unknown review.")
    row = {k:v for k,v in prior.items() if k != "json_id"}
    row["text"], actions = deidentify(row["text"], identities)
    row.update(version=prior["version"]+1, paragraphs=paragraphs(row["text"]), actions=prior["actions"]+actions,
        inclusion="included" if include else "excluded", exclusion_reason=None if include else reason)
    store.add("identity", corpus, dict(review_id=rid, identities=list(identities), actor=actor, reason=reason))
    store.add("review", corpus, row)
    return rid
