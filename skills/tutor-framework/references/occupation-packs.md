# Occupation and workflow packs

The current pack set is a reusable starting taxonomy rather than a claim that
every occupation has been fully automated. Twelve family manifests cover the
occupation guide's broad groups:

- agriculture and food;
- customer, sales, and marketing;
- education, care, and health;
- finance and accounting;
- legal, government, and public safety;
- media, design, and creative work;
- office and business;
- retail, hospitality, and services;
- social and community work;
- technology, engineering, and science;
- trades and production; and
- transport and logistics.

Seven common workflows can be reused across families: document assistance,
source-backed research, spreadsheet assistance, SOP tutoring, customer
conversation practice, voice-note structuring, and photo checklists.

When adding a pack:

1. Start from `packs/template/manifest.template.json`.
2. Define the job context, inputs, outputs, risks, review requirements, and
   connector needs without embedding secrets or provider-specific authority.
3. Mark uncertain, regulated, or high-impact behavior as review-required or
   `not_adopted`.
4. Add a synthetic fixture and run the release gate.

The manifest is a routing and teaching aid. It does not grant a licence,
credential, account access, consent, or publishing permission.
