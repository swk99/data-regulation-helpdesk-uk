import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PARSER_VERSION = 2


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, directory):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / 'raw').mkdir(exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, url TEXT, hash TEXT, title TEXT,
              source TEXT, published TEXT, kind TEXT, observed TEXT, checked TEXT, etag TEXT, modified TEXT,
              active INTEGER DEFAULT 0, vector_model TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, version TEXT, body TEXT, metadata TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(id UNINDEXED, body);
            CREATE TABLE IF NOT EXISTS candidates(url TEXT PRIMARY KEY, title TEXT, source TEXT, discovered TEXT);
            CREATE TABLE IF NOT EXISTS source_status(source TEXT PRIMARY KEY, status TEXT, checked TEXT, detail TEXT);
            ''')
            if 'parser_version' not in {row[1] for row in db.execute('PRAGMA table_info(versions)')}:
                db.execute('ALTER TABLE versions ADD COLUMN parser_version INTEGER DEFAULT 0')

    def connect(self):
        db = sqlite3.connect(self.path / 'registry.sqlite3', timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def active(self, url):
        with self.connect() as db:
            row = db.execute('SELECT * FROM versions WHERE url=? AND active=1', (url,)).fetchone()
            return dict(row) if row else None

    def touch(self, url):
        with self.connect() as db:
            db.execute('UPDATE versions SET checked=? WHERE url=? AND active=1', (now(), url))

    def save(self, download, doc, chunks, source):
        digest = hashlib.sha256(download.body).hexdigest()
        version = hashlib.sha256((download.url + digest).encode()).hexdigest()
        snapshot = self.path / 'raw' / digest
        if not snapshot.exists():
            snapshot.write_bytes(download.body)
        stamp = now()
        with self.connect() as db:
            existing = db.execute('SELECT id,parser_version FROM versions WHERE id=?', (version,)).fetchone()
            if not existing:
                db.execute('INSERT INTO versions(id,url,hash,title,source,published,kind,observed,checked,etag,modified) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                           (version, download.url, digest, doc.title, source, doc.published, doc.kind, stamp, stamp, download.etag, download.modified))
            if not existing or existing['parser_version'] != PARSER_VERSION:
                db.execute('DELETE FROM search WHERE id IN (SELECT id FROM chunks WHERE version=?)',(version,))
                db.execute('DELETE FROM chunks WHERE version=?',(version,))
                for i, c in enumerate(chunks):
                    cid = f'{version}:{i}'
                    db.execute('INSERT INTO chunks VALUES(?,?,?,?)', (cid, version, c['text'], json.dumps(c)))
                    db.execute('INSERT INTO search VALUES(?,?)', (cid, doc.title + '\n' + c['section'] + '\n' + c['text']))
                db.execute("UPDATE versions SET parser_version=?,vector_model='' WHERE id=?",(PARSER_VERSION,version))
            db.execute('UPDATE versions SET active=0 WHERE url=?', (download.url,))
            db.execute('UPDATE versions SET active=1,checked=?,etag=?,modified=? WHERE id=?', (stamp, download.etag, download.modified, version))
        return version

    def rows(self, ids=None, version=None):
        sql = 'SELECT c.*,v.url,v.title,v.source,v.published,v.checked,v.observed,v.hash FROM chunks c JOIN versions v ON c.version=v.id WHERE v.active=1'
        args = []
        if ids is not None:
            if not ids:
                return []
            sql += ' AND c.id IN (' + ','.join('?' for _ in ids) + ')'
            args.extend(ids)
        if version:
            sql += ' AND c.version=?'
            args.append(version)
        with self.connect() as db:
            result = []
            for row in db.execute(sql, args):
                d = dict(row)
                d.update(json.loads(d.pop('metadata')))
                result.append(d)
            return result

    def lexical(self, question, limit=40):
        from .query import plan_query
        tokens = plan_query(question).terms
        if not tokens:
            return []
        expression = ' OR '.join('"' + word + '"' for word in tokens)
        with self.connect() as db:
            return [r[0] for r in db.execute('''SELECT search.id FROM search JOIN chunks c ON search.id=c.id
                JOIN versions v ON c.version=v.id WHERE search MATCH ? AND v.active=1 ORDER BY rank LIMIT ?''', (expression, limit))]

    def add_candidates(self, links, source):
        with self.connect() as db:
            db.executemany('INSERT INTO candidates VALUES(?,?,?,?) ON CONFLICT(url) DO UPDATE SET title=excluded.title',
                           [(u, t, source, now()) for u, t in links])

    def candidates(self, question, source, limit):
        with self.connect() as db:
            rows = [dict(r) for r in db.execute("SELECT c.* FROM candidates c LEFT JOIN versions v ON c.url=v.url AND v.active=1 WHERE c.source=? ORDER BY COALESCE(v.checked, '') ASC, c.discovered DESC LIMIT 10000", (source,))]
        from .query import plan_query, candidate_score
        plan = plan_query(question)
        def score(row):
            return candidate_score(row['title'], row['url'], plan)
        rows.sort(key=score, reverse=True)
        return [r for r in rows if not question or score(r) > 0][:limit]

    def mark(self, source, status, detail):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO source_status VALUES(?,?,?,?)', (source, status, now(), detail))

    def status(self):
        with self.connect() as db:
            return {'documents': db.execute('SELECT COUNT(*) FROM versions WHERE active=1').fetchone()[0],
                    'versions': db.execute('SELECT COUNT(*) FROM versions').fetchone()[0],
                    'sources': [dict(r) for r in db.execute('SELECT * FROM source_status')]}

    def history(self, url):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT title,hash,observed,checked,published,active FROM versions WHERE url=? ORDER BY observed DESC', (url,))]
