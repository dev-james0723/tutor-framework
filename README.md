# Tutor Framework

Language: [English](#english) | [繁體中文](#繁體中文) | [简体中文](#简体中文) | [Español](#español) | [日本語](#日本語) | [Português](#português) | [हिन्दी](#हिन्दी) | [العربية](#العربية)

## English

Tutor Framework is a platform-neutral, evidence-grounded foundation for building
tutors that can support many occupations without pretending to be a licensed
professional or an autonomous operator. The reusable Codex skill is
[`skills/tutor-framework/SKILL.md`](skills/tutor-framework/SKILL.md).

### Quick start

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m tutor_framework.release_gate .
```

Read the skill instructions first, then [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
[`docs/EXECUTION-STATES.md`](docs/EXECUTION-STATES.md), and
[`packs/README.md`](packs/README.md). The repository has no runtime dependency;
Python 3.11+ is required. `pytest` is optional.

### Included

- A versioned JSON protocol with claims, confidence, provenance, anchors, review state, and consent boundaries.
- A deterministic `TutorEngine`, fail-closed policies, occupation routing, connector interfaces, and draft-only pack manifests.
- Twelve occupation families covering the supplied global occupation guide, seven reusable workflows, and public synthetic fixtures.
- A narrow MusicXML score-literacy slice that demonstrates domain-specific extension without claiming full optical music recognition.
- A third-party skill adoption registry and security/licensing guidance.

### Safety and scope

The framework is a foundation, not a professional licence, provider credential,
or permission to send messages, publish, schedule, upload, transact, or alter
external systems. Keep ambiguity and provenance visible. Treat occupation packs,
connector integrations, and third-party skills as draft or reviewable until the
appropriate human and domain checks are complete. Do not add real patient,
customer, student, case, or private-message data to fixtures.

## 繁體中文

一個跨平台、以證據為本的 tutor foundation，讓同一套核心可以支援不同工種，
同時保留來源、信心、審核、同意及外部操作邊界。先閱讀
[`skills/tutor-framework/SKILL.md`](skills/tutor-framework/SKILL.md)，再執行上面的三個驗證指令。
目前包含 12 個工種 family、常見工作流程、MusicXML 樂譜識讀示範，以及第三方 skill 審核登記表。

## 简体中文

这是一个跨平台、证据导向的 tutor foundation，用同一套核心支持不同职业，
并保留来源、置信度、审核、同意和外部操作边界。先阅读
[`skills/tutor-framework/SKILL.md`](skills/tutor-framework/SKILL.md)，再运行上面的三个验证命令。
仓库包含 12 个职业 family、常见工作流、MusicXML 乐谱识读示例，以及第三方 skill 审核登记。

## Español

Una base de tutoría neutral respecto a la plataforma y centrada en evidencia.
Conserva procedencia, confianza, revisión y consentimiento, y no concede autoridad
profesional ni permisos de escritura externa. Lee el skill y ejecuta las tres
comprobaciones de la sección de inicio rápido.

## 日本語

職種をまたいで使える、証拠ベースの tutor foundation です。出典、信頼度、
レビュー、同意、外部操作の境界を保持し、専門資格や自動実行権限を与えません。
skill を読んで、クイックスタートの 3 つの検証を実行してください。

## Português

Uma base de tutoria neutra em relação à plataforma e orientada por evidências.
Ela preserva procedência, confiança, revisão e consentimento, sem conceder licença
profissional ou permissão para escrever em sistemas externos. Leia o skill e execute
as três validações do início rápido.

## हिन्दी

यह अलग-अलग पेशों के लिए evidence-grounded tutor बनाने का platform-neutral आधार है।
यह स्रोत, confidence, review, consent और external-action सीमाएँ सुरक्षित रखता है;
यह professional licence या external write permission नहीं देता। skill पढ़कर quick start
में दिए गए तीन validation commands चलाएँ।

## العربية

إطار أساس محايد للمنصة لبناء مساعدين تعليميين قائمين على الأدلة لمهن متعددة.
يحافظ على المصدر ودرجة الثقة والمراجعة والموافقة وحدود الإجراءات الخارجية، ولا يمنح
ترخيصاً مهنياً أو صلاحية تنفيذ خارجية. اقرأ الـ skill ثم شغّل اختبارات التحقق الثلاثة.

## Project documents

- [Architecture](docs/ARCHITECTURE.md)
- [Execution states](docs/EXECUTION-STATES.md)
- [Contribution guide](docs/CONTRIBUTING.md)
- [Security policy](docs/SECURITY.md)
- [Licensing notes](docs/LICENSES.md)
- [Third-party skill audit](docs/THIRD_PARTY_SKILL_AUDIT.md)
- [Skill adoption registry](docs/skill-adoption-registry.json)
- [Pack authoring guide](packs/README.md)

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
