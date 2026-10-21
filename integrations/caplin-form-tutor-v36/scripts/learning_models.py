#!/usr/bin/env python3
from __future__ import annotations

def record_correction(conn,original_claim_id,correcting_claim_id,category,note=''):
    row=conn.execute('SELECT id FROM corrections WHERE original_claim_id=? AND correcting_claim_id=? AND category=?',(original_claim_id,correcting_claim_id,category)).fetchone()
    if row: return row[0]
    cur=conn.execute('INSERT INTO corrections(original_claim_id,correcting_claim_id,category,note) VALUES(?,?,?,?)',(original_claim_id,correcting_claim_id,category,note)); conn.commit(); return cur.lastrowid

def derive_learning_patterns(conn):
    out=[]
    cats=conn.execute('SELECT category,COUNT(*) n,MAX(created_at) last FROM corrections GROUP BY category HAVING COUNT(*)>=2').fetchall()
    for category,n,last in cats:
        wording=f'In {n} prior exercises, the analysis needed correction for {category}; check the relevant formal evidence before labeling.'
        check=f'Before deciding, what evidence tests {category}?'
        conn.execute('INSERT INTO learning_patterns(category,occurrence_count,confidence,wording,socratic_check,last_observed) VALUES(?,?,?,?,?,?) ON CONFLICT(category) DO UPDATE SET occurrence_count=excluded.occurrence_count,confidence=excluded.confidence,wording=excluded.wording,socratic_check=excluded.socratic_check,last_observed=excluded.last_observed',(category,n,min(.95,.5+.1*n),wording,check,last))
        pid=conn.execute('SELECT id FROM learning_patterns WHERE category=?',(category,)).fetchone()[0]
        for r in conn.execute('SELECT id FROM corrections WHERE category=?',(category,)): conn.execute('INSERT OR IGNORE INTO learning_pattern_evidence(pattern_id,correction_id) VALUES(?,?)',(pid,r[0]))
        out.append(dict(conn.execute('SELECT * FROM learning_patterns WHERE id=?',(pid,)).fetchone()))
    conn.commit(); return out

def relevant_learning_patterns(conn,concept_names):
    names={x.casefold() for x in concept_names}; return [dict(r) for r in conn.execute('SELECT * FROM learning_patterns') if any(n in r['category'].casefold() for n in names)]

def derive_professor_patterns(conn,category):
    """Only directly relevant, verified, independently anchored instructor evidence counts.

    Do not widen a failed category lookup to unrelated claims. Treat this as a
    rebuildable derived index; remove stale evidence when a claim loses review.
    """
    import re
    normalized=' '.join(category.casefold().replace('-', ' ').split())
    if not normalized:
        raise ValueError('professor concept category cannot be empty')
    concept_ids={row[0] for row in conn.execute(
        'SELECT id FROM concepts WHERE lower(trim(name))=?',(normalized,))}
    links={}
    for claim_id,concept_id in conn.execute('SELECT claim_id,concept_id FROM claim_concepts'):
        links.setdefault(claim_id,set()).add(concept_id)
    candidates=conn.execute("""SELECT id,source_id,locator,text,stance
        FROM claims WHERE authority='instructor' AND verification='verified'
          AND stance IN ('support','counterexample') ORDER BY id""").fetchall()
    scoped=[]
    for row in candidates:
        claim_id, source_id, locator, statement, stance=row
        if not source_id or not locator:
            continue
        is_linked=bool(links.get(claim_id,set()) & concept_ids)
        is_named=bool(re.search(r'(?<![a-z0-9_])'+re.escape(normalized)+r'(?![a-z0-9_])',
                                ' '.join((statement or '').casefold().replace('-', ' ').split())))
        if is_linked or is_named:
            scoped.append((claim_id,source_id,locator,stance))
    # Different claims at the same recording/time are one evidence instance.
    independent={}
    for cid,source,locator,stance in scoped:
        if stance=='support':
            independent.setdefault((source,locator),cid)
    support=sorted(independent.values())
    old=conn.execute('SELECT id FROM professor_patterns WHERE category=?',(category,)).fetchone()
    if len(support)<2:
        if old:
            conn.execute('DELETE FROM professor_pattern_evidence WHERE pattern_id=?',(old[0],))
            conn.execute('DELETE FROM professor_patterns WHERE id=?',(old[0],))
            conn.commit()
        return []
    wording=(f'Across {len(support)} independent verified course passages, '
             f'the professor discusses {category}; inspect the linked source '
             'before applying this to a particular piece.')
    conn.execute('INSERT INTO professor_patterns(category,support_count,wording) VALUES(?,?,?) '
                 'ON CONFLICT(category) DO UPDATE SET support_count=excluded.support_count,'
                 'wording=excluded.wording',(category,len(support),wording))
    pid=conn.execute('SELECT id FROM professor_patterns WHERE category=?',(category,)).fetchone()[0]
    conn.execute('DELETE FROM professor_pattern_evidence WHERE pattern_id=?',(pid,))
    for cid in support:
        conn.execute('INSERT INTO professor_pattern_evidence VALUES(?,?,?)',(pid,cid,'support'))
    for cid,source,locator,stance in scoped:
        if stance=='counterexample':
            conn.execute('INSERT OR IGNORE INTO professor_pattern_evidence VALUES(?,?,?)',
                         (pid,cid,'counterexample'))
    conn.commit()
    return [dict(conn.execute('SELECT * FROM professor_patterns WHERE id=?',(pid,)).fetchone())]

def professor_evidence(conn,pattern_id):
    rows=conn.execute('SELECT claim_id,relation FROM professor_pattern_evidence WHERE pattern_id=?',(pattern_id,)).fetchall()
    return {'support_claim_ids':[r[0] for r in rows if r[1]=='support'],'counterexample_claim_ids':[r[0] for r in rows if r[1]=='counterexample']}
