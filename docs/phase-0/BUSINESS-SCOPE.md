# Phase 0 business scope — working baseline

Status: draft baseline for implementation, not a completed Phase 0 gate.

## Users and outcome

Sales representatives prepare follow-ups and CRM changes from customer conversations. Approvers review exact changes before execution. Reduce preparation work while preserving correct customer/deal linkage, current commitments and evidence.

## Journey A: conversation intake

Email or meeting notes arrive with source identity and version. Resolve the permitted account/deal, extract source-linked commitments and revisions, prepare a CRM field diff or supported activity plus an email draft, and show the evidence for human review. CRM approval and email-send approval are separate. A changed source or CRM version invalidates an older approval.

Reference example: a customer moves a demo from 14 October 2026 at 10:00 Asia/Jakarta to 15 October 2026 at 14:00 Asia/Jakarta. The proposal must retain only the latest agreed date as current, preserve revision provenance, identify one exact deal, and prepare one activity and one factual draft. Replaying the event must not create a duplicate activity or send.

## Journey B: due follow-up

At the due time, check latest activity, opt-out, source/CRM freshness and approval validity. Prepare or execute only eligible work through the same domain controls. Already-contacted and opted-out customers receive no duplicate or prohibited follow-up. Ambiguous identity requires review.

## Ownership

- Python domain service: authorization, matching rules, proposals, approvals, idempotency and authoritative operation outcomes.
- PostgreSQL: durable business/control state; lightweight doubles can support early tests without claiming database acceptance.
- n8n: triggers, schedules and workflow coordination using authenticated domain endpoints.
- TypeScript React UI: source evidence, exact diff, independent approvals and recovery state.
- TypeScript MCP: bounded sales tools calling the same domain service.
- Odoo connector 02: reused via its supported contract; no copied generic connector implementation.
- AI: extraction and drafting behind validated output schemas; never grants execution authority.

## Initial acceptance cases to formalize

Correct linkage; two deals for one customer; revised date; timezone conversion; duplicate and out-of-order events; opt-out; already contacted; stale approval; tenant/role rejection; prompt injection in email; partial outcome; timeout after accepted send and reconciliation without blind resend.

## Execution boundary

Phase 0–6 use local processes, unit/contract tests, native inference and permitted bounded provider/read-only Graph canaries. Workflow exports are statically checked before actual n8n execution in Phase 7. Email send remains disabled. External access gaps must be recorded, not substituted with claims of real integration.
