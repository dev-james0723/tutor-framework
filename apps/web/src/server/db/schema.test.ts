// @vitest-environment node
import { beforeAll, afterAll, expect, test } from 'vitest';
import { Pool, type PoolClient } from 'pg';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { assertDatabaseRealm } from './client';

const pool = new Pool({ connectionString: process.env.TEST_DATABASE_URL, max: 1 });
const namespace = 'stt_test_' + randomUUID().replaceAll('-','');
let db: PoolClient;
const migration = path.join(import.meta.dirname,'migrations/0001_initial.sql');
beforeAll(async () => {
  if(!process.env.TEST_DATABASE_URL) throw new Error('validation_unavailable: disposable PostgreSQL TEST_DATABASE_URL is required');
  const url = new URL(process.env.TEST_DATABASE_URL);
  if(!['localhost','127.0.0.1'].includes(url.hostname) || url.pathname !== '/super_theory_test') throw new Error('Refusing to run disposable tests against a nonlocal or unapproved database');
  db = await pool.connect();
  await db.query(`CREATE SCHEMA ${namespace}`);
  await db.query(`SET search_path TO ${namespace}`);
  await db.query("SET tutor.home_region = 'global'");
  await db.query(await readFile(migration,'utf8'));
});
afterAll(async () => {
  if(db) { await db.query('ROLLBACK'); await db.query(`DROP SCHEMA IF EXISTS ${namespace} CASCADE`); db.release(); }
  await pool.end();
});

test('migration creates the complete persistent MVP table set', async () => {
  const result = await db.query('SELECT tablename FROM pg_tables WHERE schemaname=$1',[namespace]);
  const tables = result.rows.map(row=>row.tablename);
  expect(tables).toEqual(expect.arrayContaining(['users','learner_profiles','conversations','messages','evidence_links','score_assets','practice_sessions','practice_attempts','competency_evidence','usage_ledger','audit_events']));
});
test('database client accepts only a matching migrated deployment realm', async () => {
  await expect(assertDatabaseRealm(db,'global')).resolves.toBeUndefined();
  await expect(assertDatabaseRealm(db,'cn')).rejects.toThrow(/region/i);
});
test('database blocks mixed-region account insertion', async () => {
  await expect(db.query("INSERT INTO users(id,name,email_normalized,home_region) VALUES ('cn-user','Test','cn@example.invalid','cn')")).rejects.toThrow(/region/i);
});
test('account region cannot be changed through a profile update', async () => {
  await db.query("INSERT INTO users(id,name,email_normalized,home_region) VALUES ('u1','Test','u1@example.invalid','global')");
  await expect(db.query("UPDATE users SET home_region='cn' WHERE id='u1'")).rejects.toThrow(/immutable/i);
  const row=await db.query("SELECT home_region FROM users WHERE id='u1'");
  expect(row.rows[0].home_region).toBe('global');
});
test('unique email normalization prevents separate identities for casing', async () => {
  await db.query("INSERT INTO users(id,name,email_normalized,home_region) VALUES ('norm1','Test','norm@example.invalid','global')");
  await expect(db.query("INSERT INTO users(id,name,email_normalized,home_region) VALUES ('norm2','Test','NORM@EXAMPLE.INVALID','global')")).rejects.toThrow();
  const row=await db.query("SELECT COUNT(*)::integer AS count FROM users WHERE email_normalized='norm@example.invalid'");
  expect(row.rows[0].count).toBe(1);
});
test('profile language does not change account residency', async () => {
  await db.query("INSERT INTO learner_profiles(user_id,locale) VALUES ('u1','zh-CN')");
  const row=await db.query("SELECT u.home_region,p.locale FROM users u JOIN learner_profiles p ON u.id=p.user_id WHERE u.id='u1'");
  expect(row.rows[0]).toEqual({home_region:'global',locale:'zh-CN'});
});
test('practice evidence enforces allowed states and append-only attempts', async () => {
  await db.query("INSERT INTO practice_sessions(id,user_id,topic) VALUES ('p1','u1','fundamentals')");
  await db.query("INSERT INTO practice_attempts(id,practice_session_id,item_id,rubric_version,response_json,result_state) VALUES ('a1','p1','item1','1','{}','correct')");
  await expect(db.query("UPDATE practice_attempts SET result_state='incorrect' WHERE id='a1'")).rejects.toThrow(/append.only/i);
  await expect(db.query("INSERT INTO competency_evidence(id,user_id,concept_id,item_id,evidence_state,practice_attempt_id) VALUES ('e1','u1','concept1','item1','mastered','a1')")).rejects.toThrow();
});
test('competency evidence cannot reference another account attempt', async () => {
  await db.query("INSERT INTO users(id,name,email_normalized,home_region) VALUES ('other','Other','other@example.invalid','global')");
  await expect(db.query("INSERT INTO competency_evidence(id,user_id,concept_id,item_id,evidence_state,practice_attempt_id) VALUES ('e2','other','concept1','item1','independent_success_evidence','a1')")).rejects.toThrow(/owner/i);
});
test('usage ledger blocks cross-region recording', async () => {
  await expect(db.query("INSERT INTO usage_ledger(id,user_id,region,model_alias,input_units,output_units,estimated_cost) VALUES ('usage1','u1','cn','tutor',1,1,0)")).rejects.toThrow(/region/i);
});
test('account deletion cascades relational learning data and revokes sessions', async () => {
  await db.query("INSERT INTO auth_sessions(id,user_id,token,expires_at) VALUES ('login1','u1','test-session-token',now()+interval '1 day')");
  await db.query("INSERT INTO conversations(id,user_id,title,primary_topic) VALUES ('c1','u1','Intervals','fundamentals')");
  await db.query("INSERT INTO messages(id,conversation_id,role,mode,content_json) VALUES ('m1','c1','assistant','explain','{}')");
  await db.query("INSERT INTO score_assets(id,user_id,storage_key,sha256,mime_type,original_filename) VALUES ('s1','u1','u1/score','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','application/xml','study.musicxml')");
  await db.query("DELETE FROM users WHERE id='u1'");
  for(const table of ['auth_sessions','learner_profiles','conversations','messages','practice_sessions','practice_attempts','score_assets']) {
    const row=await db.query(`SELECT COUNT(*)::integer as count FROM ${table}`);
    expect(row.rows[0].count).toBe(0);
  }
});

test('disposable schema migrates down and back up without stale product tables', async () => {
  await db.query('BEGIN');
  await db.query(await readFile(path.join(import.meta.dirname,'migrations/0001_down.sql'),'utf8'));
  const empty=await db.query('SELECT tablename FROM pg_tables WHERE schemaname=$1',[namespace]);
  expect(empty.rows).toHaveLength(0);
  await db.query('COMMIT');
  await db.query(await readFile(migration,'utf8'));
  const version=await db.query('SELECT version FROM schema_versions');
  expect(version.rows).toEqual([{version:'0001'}]);
});
