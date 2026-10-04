-- Additive schema. Explicit home region is required from the migration operator.
BEGIN;
CREATE TABLE schema_versions(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE app_region(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),home_region text NOT NULL CHECK(home_region IN ('global','cn')));
INSERT INTO app_region(home_region) VALUES (current_setting('tutor.home_region',true));
CREATE TABLE users(
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text CHECK(id ~ '^[A-Za-z0-9-]{1,64}$'),
 name text NOT NULL,email_normalized text NOT NULL UNIQUE CHECK(email_normalized=lower(btrim(email_normalized))),
 email_verified boolean NOT NULL DEFAULT false,email_verified_at timestamptz,image text,
 home_region text NOT NULL CHECK(home_region IN ('global','cn')),
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),deleted_at timestamptz
);
CREATE FUNCTION enforce_user_region() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='UPDATE' AND OLD.home_region IS DISTINCT FROM NEW.home_region THEN
  RAISE EXCEPTION 'home region is immutable; administrative migration required' USING ERRCODE='23514';
 END IF;
 IF NEW.home_region IS DISTINCT FROM (SELECT home_region FROM app_region WHERE singleton) THEN
  RAISE EXCEPTION 'account region differs from database realm' USING ERRCODE='23514';
 END IF;
 IF NEW.email_verified THEN NEW.email_verified_at:=COALESCE(NEW.email_verified_at,now()); ELSE NEW.email_verified_at:=NULL; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER users_region_guard BEFORE INSERT OR UPDATE ON users FOR EACH ROW EXECUTE FUNCTION enforce_user_region();
-- Auth owns credential and session storage. No passwords are stored in learner/application records.
CREATE TABLE auth_sessions(id text PRIMARY KEY,user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 token text NOT NULL UNIQUE,expires_at timestamptz NOT NULL,ip_address text,user_agent text,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE auth_accounts(id text PRIMARY KEY,user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 account_id text NOT NULL,provider_id text NOT NULL,access_token text,refresh_token text,id_token text,
 access_token_expires_at timestamptz,refresh_token_expires_at timestamptz,scope text,password text,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),UNIQUE(provider_id,account_id));
CREATE TABLE auth_verifications(id text PRIMARY KEY,identifier text NOT NULL,value text NOT NULL,expires_at timestamptz NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX auth_verification_identifier ON auth_verifications(identifier);
CREATE INDEX auth_session_user ON auth_sessions(user_id);
CREATE TABLE learner_profiles(user_id text PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 locale text NOT NULL DEFAULT 'en' CHECK(locale IN ('en','zh-CN','zh-TW')),
 terminology_system text NOT NULL DEFAULT 'ask' CHECK(terminology_system IN ('uk','us','ask')),
 note_naming text NOT NULL DEFAULT 'letter',solfege_system text NOT NULL DEFAULT 'ask' CHECK(solfege_system IN ('fixed_do','movable_do','ask')),
 minor_do_basis text NOT NULL DEFAULT 'ask' CHECK(minor_do_basis IN ('la','do','ask')),
 curriculum_id text,curriculum_version text,explanation_depth text NOT NULL DEFAULT 'normal' CHECK(explanation_depth IN ('concise','normal','detailed')),
 reduced_motion boolean NOT NULL DEFAULT false,onboarding_completed boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE conversations(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 200),primary_topic text NOT NULL,saved boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),archived_at timestamptz);
CREATE INDEX conversation_user_recent ON conversations(user_id,updated_at DESC);
CREATE TABLE messages(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,conversation_id text NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
 role text NOT NULL CHECK(role IN ('user','assistant')),mode text NOT NULL CHECK(mode IN ('explain','practice','check','deep')),
 content_json jsonb NOT NULL,model_alias text CHECK(model_alias IN ('fast','tutor','deep')),provider_request_id_redacted text,
 created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX message_conversation_order ON messages(conversation_id,created_at,id);
CREATE TABLE evidence_links(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,message_id text NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
 claim_id text,source_id text,evidence_type text NOT NULL,status text NOT NULL,CHECK(claim_id IS NOT NULL OR source_id IS NOT NULL));
CREATE TABLE score_assets(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 storage_key text NOT NULL UNIQUE,sha256 text NOT NULL CHECK(sha256 ~ '^[a-f0-9]{64}$'),mime_type text NOT NULL,
 original_filename text NOT NULL CHECK(length(original_filename) BETWEEN 1 AND 200),
 parse_status text NOT NULL DEFAULT 'pending' CHECK(parse_status IN ('pending','parsed','review_required','failed')),
 engine_version text,analysis_json jsonb,created_at timestamptz NOT NULL DEFAULT now(),
 CHECK(storage_key LIKE user_id || '/%'),UNIQUE(user_id,sha256));
CREATE TABLE practice_sessions(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 topic text NOT NULL,curriculum_id text,curriculum_version text,mode text NOT NULL DEFAULT 'practice' CHECK(mode IN ('practice','check')),
 grade integer CHECK(grade BETWEEN 1 AND 5),seed integer CHECK(seed>=0),item_index integer NOT NULL DEFAULT 0 CHECK(item_index BETWEEN 0 AND 4),
 item_json jsonb,status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','completed','abandoned')),
 started_at timestamptz NOT NULL DEFAULT now(),completed_at timestamptz);
CREATE TABLE practice_attempts(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,practice_session_id text NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
 item_id text NOT NULL,rubric_version text NOT NULL,response_json jsonb NOT NULL,hints_used integer NOT NULL DEFAULT 0 CHECK(hints_used>=0),
 answer_exposed boolean NOT NULL DEFAULT false,prior_answer_exposed boolean NOT NULL DEFAULT false,
 attempt_number integer NOT NULL DEFAULT 1 CHECK(attempt_number>0),
 result_state text NOT NULL CHECK(result_state IN ('correct','partly_correct','incorrect','insufficient_information','review_required')),
 independent_result boolean NOT NULL DEFAULT false,uncertainty jsonb NOT NULL DEFAULT '{}',idempotency_key text,
 created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(practice_session_id,idempotency_key));
CREATE FUNCTION immutable_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'attempt and evidence records are append-only' USING ERRCODE='23514'; END $$;
CREATE TRIGGER attempt_append_only BEFORE UPDATE ON practice_attempts FOR EACH ROW EXECUTE FUNCTION immutable_evidence();
CREATE TABLE competency_evidence(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 concept_id text NOT NULL,item_id text NOT NULL,
 evidence_state text NOT NULL CHECK(evidence_state IN ('unassessed','assisted_success_evidence','independent_success_evidence','delayed_transfer_success_evidence')),
 practice_attempt_id text REFERENCES practice_attempts(id) ON DELETE CASCADE,observed_at timestamptz NOT NULL DEFAULT now(),notes_json jsonb NOT NULL DEFAULT '{}');
CREATE FUNCTION enforce_evidence_owner() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner_id text;
BEGIN
 IF NEW.practice_attempt_id IS NOT NULL THEN
  SELECT s.user_id INTO owner_id FROM practice_attempts a JOIN practice_sessions s ON a.practice_session_id=s.id WHERE a.id=NEW.practice_attempt_id;
  IF owner_id IS DISTINCT FROM NEW.user_id THEN RAISE EXCEPTION 'evidence owner differs from attempt owner' USING ERRCODE='23514'; END IF;
 END IF;
 IF NEW.evidence_state<>'unassessed' AND NEW.practice_attempt_id IS NULL THEN RAISE EXCEPTION 'success evidence needs an attempt' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER competency_owner BEFORE INSERT ON competency_evidence FOR EACH ROW EXECUTE FUNCTION enforce_evidence_owner();
CREATE TRIGGER competency_append_only BEFORE UPDATE ON competency_evidence FOR EACH ROW EXECUTE FUNCTION immutable_evidence();
CREATE INDEX competency_user_concept ON competency_evidence(user_id,concept_id,observed_at DESC);
CREATE TABLE usage_ledger(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 region text NOT NULL CHECK(region IN ('global','cn')),model_alias text NOT NULL CHECK(model_alias IN ('fast','tutor','deep')),
 input_units bigint NOT NULL CHECK(input_units>=0),output_units bigint NOT NULL CHECK(output_units>=0),estimated_cost numeric(16,8) NOT NULL CHECK(estimated_cost>=0),
 created_at timestamptz NOT NULL DEFAULT now());
CREATE FUNCTION enforce_usage_region() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.region IS DISTINCT FROM (SELECT home_region FROM users WHERE id=NEW.user_id) THEN RAISE EXCEPTION 'usage region differs from account home region' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER usage_region_guard BEFORE INSERT ON usage_ledger FOR EACH ROW EXECUTE FUNCTION enforce_usage_region();
CREATE INDEX usage_user_day ON usage_ledger(user_id,created_at);
CREATE TABLE audit_events(id text PRIMARY KEY DEFAULT gen_random_uuid()::text,user_id text REFERENCES users(id) ON DELETE SET NULL,
 event_type text NOT NULL,request_id text NOT NULL,region text NOT NULL CHECK(region IN ('global','cn')),safe_metadata_json jsonb NOT NULL DEFAULT '{}',created_at timestamptz NOT NULL DEFAULT now());
INSERT INTO schema_versions(version) VALUES ('0001');
COMMIT;
