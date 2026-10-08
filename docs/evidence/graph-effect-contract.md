# Graph mail effect contract

`backend/graph_effects.py` sends the locally approved immutable draft content through Graph `sendMail`, with one configured mailbox, local tenant binding, recipient allowlist and a default-off send switch. Subject uses the approved proposal summary. The whole payload hash is checked before any request. The normal app factory does not instantiate the adapter or enable external writes.

The existing core persists the operation before dispatch and prevents a second dispatch after restart. The adapter itself makes one POST attempt, with no automatic retries, redirects or provider fallback. A client request ID is correlation only; it is not claimed as Graph idempotency. Timeout and unsuccessful responses remain unknown. A 202 response is accepted only with a valid Graph request ID, stored with `graph-request:` prefix to distinguish it from a message ID.

Observation reads Sent Items using the operation's single-value extended-property correlation. Missing, duplicate or paginated matches remain unknown. A single result must match the operation property, recipient list, empty CC/BCC, approved subject/body, non-draft state and an aware sent timestamp before producing a sent observation. Core status remains `accepted`; neither API acceptance nor Sent Items is proof of delivery/read. Observation never resends. An effect router delegates only to the configured CRM/mail adapter and has no fallback.

Native tests use HTTP boundary doubles: accepted vs sent, timeout/read-back, missing/duplicate correlation, wrong content/recipients/operation, rate limit/auth/server/redirect responses without retry, switch/allowlist/scope/hash guards, and shared-core restart/replay after a lost send response. No actual Graph connection or email was sent.

References: [sendMail contract and acceptance semantics](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0), [extended-property creation](https://learn.microsoft.com/en-us/graph/api/singlevaluelegacyextendedproperty-post-singlevalueextendedproperties?view=graph-rest-1.0), [extended-property lookup](https://learn.microsoft.com/en-us/graph/api/singlevaluelegacyextendedproperty-get?view=graph-rest-1.0). The composed sendMail extended-property persistence/filter behavior and exact text read-back still require real tenant acceptance in Phase 7; boundary tests cannot establish that behavior. Message-body normalization differences conservatively remain unknown.

Outstanding: consent/token refresh, mailbox mapping, immutable payload repository wiring, controlled live acceptance and recovery UI. No mailbox draft creation is needed for this path: review occurs locally and approved content is supplied atomically in the send request. A mailbox-visible draft workflow, if added, must address edits between approval and send.

Validation on 2026-10-09 Asia/Jakarta: `.venv/Scripts/python.exe -m pytest -q` → 183 passed, including 20 Graph adapter/core tests.
