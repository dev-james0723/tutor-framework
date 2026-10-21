# Caplin Tutor v3.6 — Agent Handoff Prompt (NO automatic deployment)

芝麻開門。使用 Kynlo Hybrid 接續 **Caplin Tutor v3.6 Evidence-Driven Assignment Engine** 已完成嘅隔離本機實作。請先唯讀核實：

- Worktree: `/Users/ouxianxing/Projects/tutor-framework-caplin-v36-20261021`
- Branch: `feat/caplin-evidence-driven-v36-20261021`
- Baseline: `aa5bcb4a096ff8538d581b514d1480cc8671a54d`
- Closeout: `docs/release/CAPLIN-V36-EVIDENCE-ENGINE-20261021.md`
- Staged skill: `integrations/caplin-form-tutor-v36/SKILL.md`
- Professor fix: `integrations/caplin-form-tutor-v36/scripts/learning_models.py`
- Engines: `src/tutor_framework/domains/music/lesson/learning_pack/assignment_engine.py` and `assignment_pdf.py`
- New tests: `tests/unit/test_caplin_v36_professor.py`, `tests/integration/test_caplin_v36_assignment.py`
- Repro smoke: `tools/smoke_caplin_v36.py` and `artifacts/caplin-v36-candidate-20261021/receipt.json`

**End goal:** Deliver a fully evidence-grounded Caplin Tutor v3.6 with professor-language precision, verified score-to-annotation correspondence, clean nested brackets and cadence boxes, independent music QA, score-before-essay PDF and separate adversarial self-proof. Preserve all prior Learn Mode/knowledge graph/score-analyzer/Mochi features.

**Operating rule:** Maximize safe autonomous TDD in an independent worktree; do not stop for reversible code/debug/fixture tasks. Protect Mac under memory/swap pressure: one light test job at a time, no heavy parallel builds or dependency installs. Preserve all other Agents and source files.

**Next actions:**
1. Inspect exact commit/diff and validate staged Professor Evidence patterns on documented *real authorized* course data in read-only mode. Never infer what the professor taught from unrelated or unverified claims.
2. Extend `ScoreMark` with an authoritative edition-aware measure/beat map; connect score-harmony-analyzer verified symbolic inputs, including source revisions and real-source image review. Challenge each proof using independent notes/rhythm/bass/harmony rather than author assertions alone.
3. Build real authorized fixture tests for multi-system notation, shifts/insertions between exposition/recap, multiple nested Sentence/Presentation/Continuation/BI/BI′ bracket tiers, engraving collisions, correct cadence arrival and Crux. Keep honest `review_required` where true listening/score checks are impossible.
4. Wire assignment export into existing Learning Pack guided/coached/worked/review pathways without leaking answers or changing legacy APIs. Provide exact requirement coverage and ensure proof content is standalone.
5. Run updated isolated tests, all relevant existing regression tests, full page-by-page QA on representative real scores, content source hashes, security/rights review, and record actual verification statuses.
6. Save independent closeout, rollback, local commit SHA, final GO/NO-GO. Leave source and staged candidate auditable if gates remain blocked.

**Hard boundaries:** Do not modify installed `~/.agents/skills/caplin-form-tutor/SKILL.md`, installed scripts, original `~/Projects/tutor-framework` dirty tree, `~/.local/share/caplin-form-tutor`, Professor source material, live data, active Agents, budgets, credentials or configurations. Do not Push, Merge, deploy, install, start paid services or create media uploads. Any future deployment requires explicit independent authorization after the remaining real-score and QA gates pass.

**User's non-negotiable rule:** Keep the current standing 1–3 intentional errors for all applicable essay/score assignment packages, independently disclosed and corrected in self-proof. **Challenge Mode remains proposal only; never quietly replace the standing rule.**
