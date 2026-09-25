"""Append-only JSON records and chained audit events in a private SQLite store."""
from pathlib import Path
import sqlite3
import os
import uuid
from datetime import datetime, timezone
from .domain import CONFIG, BoundaryError, canonical, fingerprint, identifier
from .profiles import get_profile, PARTITIONS, configuration

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.db = sqlite3.connect(self.root / "state.sqlite3")
        os.chmod(self.root / "state.sqlite3", 0o600)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS records(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL,
          corpus TEXT NOT NULL, id TEXT UNIQUE NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY, time TEXT NOT NULL,
          action TEXT NOT NULL, record_id TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS records_no_update BEFORE UPDATE ON records BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS records_no_delete BEFORE DELETE ON records BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'append only'); END;
        ''')

    def add(self, kind, corpus, data, record_id=None):
        rid = record_id or kind + "-" + uuid.uuid4().hex
        raw, time = canonical(data), now()
        with self.db:
            self.db.execute("INSERT INTO records(kind,corpus,id,data) VALUES(?,?,?,?)", (kind, corpus, rid, raw))
            last = self.db.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
            previous = last[0] if last else "0" * 64
            digest = fingerprint(canonical([previous, time, kind, rid, raw]).encode())
            self.db.execute("INSERT INTO audit(time,action,record_id,previous,hash) VALUES(?,?,?,?,?)",
                            (time, kind, rid, previous, digest))
        return rid

    def rows(self, kind, corpus):
        return [dict(json_id=rid, **__import__('json').loads(raw)) for rid, raw in
                self.db.execute("SELECT id,data FROM records WHERE kind=? AND corpus=? ORDER BY seq", (kind, corpus))]

    def corpus(self, corpus):
        identifier(corpus)
        rows = self.rows("corpus", corpus)
        if not rows:
            raise BoundaryError("Unknown corpus; run init first.")
        if rows[0]["config"] != configuration(rows[0].get("domain", "book")):
            raise BoundaryError("Unsupported configuration; all external capabilities must remain disabled.")
        profile = get_profile(rows[0].get("domain", "book"))
        if rows[0].get("profile_version", profile.version) != profile.version:
            raise BoundaryError("Unsupported domain profile version.")
        return rows[0]

    def init(self, corpus, label="Local study", domain="book", work_id=None, partition="unassigned"):
        identifier(corpus)
        if self.rows("corpus", corpus):
            raise BoundaryError("Corpus already exists; replacement is not supported.")
        profile = get_profile(domain)
        work_id = identifier(work_id or corpus)
        if partition not in PARTITIONS:
            raise BoundaryError("Unknown study partition.")
        # One work cannot quietly occur in both development and evaluation in this store.
        import json
        for (raw,) in self.db.execute("SELECT data FROM records WHERE kind='corpus'"):
            existing = json.loads(raw)
            if (existing.get("domain", "book") == domain and existing.get("work_id", existing["corpus_id"]) == work_id
                and {existing.get("partition", "unassigned"), partition} == {"development", "evaluation"}):
                raise BoundaryError("Work already assigned to the other study partition.")
        rid = self.add("corpus", corpus, dict(corpus_id=corpus, label=label, created_at=now(), config=configuration(domain),
            domain=profile.domain, profile_version=profile.version, work_id=work_id, partition=partition))
        self.add("source_access_rule", corpus, dict(source="external_sources", allowed_acquisition_method="none",
            allowed_actions=[], prohibited_actions=["scrape","connect","post","contact","remote_inference"],
            retention_constraints="no acquisition", authorization_owner="unassigned", terms_review_date=None, status="disabled"))
        return rid

    def reviews(self, corpus):
        versions = {}
        for row in self.rows("review", corpus):
            versions[row["review_id"]] = row
        return list(versions.values())

    def verify(self):
        previous = "0" * 64
        for time, action, rid, prev, digest, raw in self.db.execute('''SELECT a.time,a.action,a.record_id,a.previous,a.hash,r.data
            FROM audit a JOIN records r ON a.record_id=r.id ORDER BY a.seq'''):
            expected = fingerprint(canonical([previous, time, action, rid, raw]).encode())
            if prev != previous or digest != expected:
                raise BoundaryError("Audit chain mismatch.")
            previous = digest
        if self.db.execute("SELECT count(*) FROM records").fetchone() != self.db.execute("SELECT count(*) FROM audit").fetchone():
            raise BoundaryError("Audit record count mismatch.")
        for (raw,) in self.db.execute("SELECT data FROM records WHERE kind='source'"):
            source = __import__('json').loads(raw)
            if source.get("managed_copy"):
                path = Path(source["managed_copy"])
                if not path.is_file() or fingerprint(path.read_bytes()) != source["sha256"]:
                    raise BoundaryError("Original source fingerprint mismatch or missing source.")
        return True
