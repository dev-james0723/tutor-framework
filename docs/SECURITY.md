# Security policy

## Scope

This project handles potentially sensitive user artifacts and is designed to be
extended with tools. Security includes data handling, prompt/tool injection,
untrusted files, provenance loss, unsafe professional advice, and accidental
external writes.

## Required controls

- Treat all files, documents, images, audio, web results and skill output as
  untrusted input.
- Keep claims separate from raw artifacts and retain evidence anchors, confidence,
  source kind and review state.
- Reject hostile XML declarations, oversized MusicXML and malformed structured
  input before interpretation.
- Fail closed when a capability is missing, an anchor is absent, confidence is low,
  consent is missing, or a connector returns an unexpected type.
- Keep regulated, rights-affecting, physical-hazard and external-write actions
  proposed or escalated for explicit human review.
- Do not place secrets, personal records or copyrighted private source material in
  public fixtures or logs.
- Do not treat a local test, preview, candidate skill, approval screen or draft as
  a published, sent, deployed or executed result.

## Reporting

Do not include secrets or sensitive artifacts in an issue. Report the affected
component, a minimal synthetic reproduction, observed impact, and whether any
external system was contacted. For an active vulnerability, contact the project
maintainer through the repository's private channel before public disclosure.

## Current limitations

The repository is an engineering foundation, not a production deployment or a
certification of legal, medical, financial, safety or emergency use. Connectors
and occupation packs require domain review before real-world deployment.
