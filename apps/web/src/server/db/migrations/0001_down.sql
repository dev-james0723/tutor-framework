-- Destructive removal is only for disposable tests or separately approved empty installations.
-- Production rollback keeps the additive schema and rolls application code back one window.
DROP TABLE audit_events,usage_ledger,competency_evidence,practice_attempts,practice_sessions,
 score_assets,evidence_links,messages,conversations,learner_profiles,
 auth_verifications,auth_accounts,auth_sessions,users,app_region,schema_versions;
DROP FUNCTION enforce_usage_region(),enforce_evidence_owner(),immutable_evidence(),enforce_user_region();
