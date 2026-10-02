"""Private SQLite storage with separate append-only answer-origin tables."""
import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

KINDS = ('source_question', 'official_answer', 'third_party_explanation', 'ai_derived_answer', 'teacher_result', 'learner_answer')


class PrivateExamPersistence:
    def __init__(self, root: Path, tenant_id: str):
        self.directory = root / tenant_id
        self.path = self.directory / 'bank.sqlite3'
        if self.directory.is_symlink() or self.path.is_symlink():
            raise ValueError('private bank cannot follow a symlink')

    def load(self):
        if not self.path.exists():
            return {}, {}, {}
        if self.path.stat().st_size > 100_000_000:
            raise ValueError('bank exceeds bounded pilot storage size')
        with closing(sqlite3.connect(f'file:{self.path}?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('unknown bank schema; migration review required')
            papers = {key: json.loads(value) for key, value in db.execute('SELECT id, payload FROM papers')}
            sessions = {key: json.loads(value) for key, value in db.execute('SELECT id, payload FROM sessions')}
            layers = {}
            for kind in KINDS:
                for question_id, value in db.execute(f'SELECT question_id, payload FROM layer_{kind} ORDER BY ordinal'):
                    row = json.loads(value)
                    if row['kind'] != kind or row['question_id'] != question_id:
                        raise ValueError('answer-origin storage integrity failure')
                    layers.setdefault(question_id, {}).setdefault(kind, []).append(row)
        return papers, layers, sessions

    def save(self, papers, layers, sessions):
        if self.directory.is_symlink() or self.path.is_symlink():
            raise ValueError('private bank cannot follow a symlink')
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        descriptor = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(descriptor)
        os.chmod(self.path, 0o600)
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                version = db.execute('PRAGMA user_version').fetchone()[0]
                if version not in (0, 1):
                    raise ValueError('bank schema requires explicit migration')
                db.execute('CREATE TABLE IF NOT EXISTS papers (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
                for kind in KINDS:
                    db.execute(f'CREATE TABLE IF NOT EXISTS layer_{kind} (id TEXT PRIMARY KEY, question_id TEXT NOT NULL, ordinal INTEGER NOT NULL, payload TEXT NOT NULL)')
                for table, records in (('papers', papers), ('sessions', sessions)):
                    for key, value in records.items():
                        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
                        db.execute(f'INSERT INTO {table} VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (key, payload))
                for question_id, by_kind in layers.items():
                    for kind, records in by_kind.items():
                        if kind not in KINDS:
                            raise ValueError('invalid answer layer')
                        for ordinal, record in enumerate(records):
                            row_id = hashlib.sha256(f'{question_id}:{kind}:{ordinal}'.encode()).hexdigest()
                            payload = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False)
                            existing = db.execute(f'SELECT payload FROM layer_{kind} WHERE id=?', (row_id,)).fetchone()
                            if existing and existing[0] != payload:
                                raise ValueError('historical answer revision cannot be overwritten')
                            db.execute(f'INSERT OR IGNORE INTO layer_{kind} VALUES (?, ?, ?, ?)', (row_id, question_id, ordinal, payload))
                db.execute('PRAGMA user_version=1')
