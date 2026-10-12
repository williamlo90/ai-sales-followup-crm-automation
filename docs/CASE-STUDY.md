# Turning sales conversations into reviewed CRM updates

**Status:** Local V1 delivered and connected-sandbox validated. See the [delivery audit](phase-8/DELIVERY-AUDIT.md), [Phase 7 completion audit](phase-7/COMPLETION-AUDIT.md), [project overview](../README.md) and [phase plan](../PHASES.md).

## The business problem

After a customer conversation, a salesperson must identify the right deal, update changed commitments, schedule the next activity and prepare a follow-up. A wrong account, an outdated promise or a repeated email can create more work than the automation removes.

## Validated workflow

A synthetic email traversed project-owned Outlook OAuth, n8n, OpenAI, the shared domain, PostgreSQL and Odoo. AI flagged the missing internal owner; a lab operator resolved that fact using the source quote. Separate lab-role approvals produced one verified Odoo activity and one self-test follow-up, observed in Sent Items and the recipient's Junk folder. This was an automated lab review, not a human operator study or a general-routing trial.

Sending remains off by default. Connected send tests use controlled mailboxes and allowlisted recipients. An accepted request or a Sent Items record is not proof of delivery or reading.

## Engineering approach

The Odoo connector from project 02 provides the integration boundary. Python owns permissions, approval versions, idempotency and the operation record; a TypeScript MCP interface exposes scoped sales actions. n8n coordinates intake, waiting and schedules using the same domain API. React provides evidence, change review and recovery views.

The implementation includes reusable skills, provider adapters and MCP contracts. OpenAI is the validated hosted profile for V1; Claude/Grok remain adapter-only and the tested local Qwen3 profile failed the quality gate. Both n8n exports were imported and exercised on the pinned engine, including actual three-minute triggers.

## Measured sandbox evidence

- A 20-case frozen synthetic regression on HTTP/PostgreSQL/OpenAI yielded correct linkage and proposal count/recipient in 20/20; 19/19 invoked extractions were correct. This reused an earlier held-out set and is not new generalization evidence.
- One [connected Outlook run](evidence/phase-7-outlook-oauth-connected.json) verified two operations for one source-backed proposal: one Odoo activity read back and one allowlisted self-test email accepted by Graph, matched in Sent Items and seen in recipient Junk. AI required an internal owner to be supplied during review; no price was invented.
- Normal N=2, peak N=3 and short-soak N=4 deterministic n8n/PostgreSQL/Odoo jobs each verified once, with zero errors in those sessions. Their small-sample latency percentiles exclude Graph/model time.
- Recovery drills covered duplicate/unknown writes, n8n restart and rollback, PostgreSQL restore, Ubuntu distro restart and local readiness alert delivery. The WSL Docker proxy required manual reattachment after distro restart.
- The equivalent-task manual/assisted comparison used one operator and synthetic tasks. It is not a customer ROI or production throughput claim.

Detailed denominators, timing, cost and limits are linked from the [Phase 7 audit](phase-7/COMPLETION-AUDIT.md). No whole-stack p95 with paid model calls or production uptime is claimed.

## Delivery

The verified local release ZIP has a per-file manifest and was installed from a clean extraction: pinned Python/Node dependencies, full Python regression, UI/MCP builds and MCP reference-client tests passed. Two inactive n8n exports imported on the pinned engine from that extraction. The [English demo](phase-8/DEMO.md) and [operator guide](phase-8/OPERATOR-GUIDE.md) cover review, activation, troubleshooting, backup and rollback. A local API outage/recovery alert drill took 8.701 seconds; this is an incident exercise, not a support-service uptime measurement.

The local workflow stops when its host sleeps or loses power/network. Phase 7 showed queued-work catch-up after an engine stop in an accelerated lab, and observation of a cloned unknown Graph outcome without a resend. Cloud hosting and Make.com/Zapier were offered as Phase 9 extensions; the owner selected local V1 without those extensions.
