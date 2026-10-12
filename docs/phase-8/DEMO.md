# Demo: proposal follow-up to reviewed actions

Use the synthetic Northstar 25-seat proposal case for the local workspace walkthrough. It needs no mailbox or external write.

| Customer request | Prepared action | Human check |
| --- | --- | --- |
| “Thanks for sharing the revised 25-seat proposal. Please call me on 15 October 2026 at 14:00 Asia/Jakarta to discuss pricing, and email me the call details.” | CRM follow-up activity: **Call Northstar about 25-seat proposal**, due at the requested time. An email draft confirms the call and its purpose. | Check the quoted source, account, time, recipient and exact draft before approving CRM and email separately. |

1. **Open the conversation.** In the local review workspace, select the Northstar proposal. The full customer request appears under “What the customer said,” with its source revision. The recipient comes from the scoped CRM deal, not from model text.
2. **Inspect the proposal.** Compare the due time and CRM activity with the source. Read the follow-up email draft beside it. Preparing either item does not execute the CRM action or send the email.
3. **Approve and queue independently.** The operator prepares a source-backed commitment and proposal; a separate approver authorizes the exact CRM and email payloads. Sign back in as the operator to use the two queue buttons in the decision panel. The worker checks approval and due time before any effect. Email sending is off in this fixture. A changed source or deal version requires new review.
4. **Check the outcome and recovery path.** The local screenshot uses a synthetic browser fixture for the verified-result presentation. The earlier [connected Phase 7 run](../evidence/phase-7-connected-email-ai-odoo.json) used a different rescheduled-demo message and verified one Odoo activity by read-back. It validates the same pipeline, not this new Northstar wording. No email was sent in that connected run.

For failure handling, show an `unknown` outcome in the recovery view. The operator observes external state before retrying, preventing a blind duplicate. See the [missed-schedule drill](../evidence/phase-7-missed-schedule-recovery.json) and [Graph reconciliation](../evidence/phase-7-graph-unknown-reconciliation.json). These are recorded synthetic results, not a fresh live send or an unassisted user study.
