# Commitment binding and provider contracts — 2026-10-09

Verification: 96 Python tests passed. TypeScript/Vite build passed. Two Edge browser scenarios cover independent approval and unknown-result presentation. Migration planning enumerates SQL/checksums without a database connection; runner replay/checksum/rollback checks use a connection double and are not PostgreSQL acceptance.

Implemented: proposal binding to exact commitment revision/due/evidence; cancellation and revision invalidation; review rather than duplicate creation after an existing commitment action; scoped operation-read API; recovery status UI; four application skill bindings and exported schemas; OpenAI Responses, Claude Messages, Grok Chat Completions and Ollama Chat structured-output adapters. One request in flight per adapter, request-count budget, bounded request/response size, transport timeout, no retry/fallback and metadata-only success/failure traces.

All provider checks used HTTPX MockTransport. No model API was called and no native model inference was run. Model IDs are explicit profile inputs; no default model has been chosen or validated. API key configuration is pending. Local-only blocks application hosted fallback and obvious cloud model aliases; actual Ollama artifact/runtime egress validation is still required before claiming local-only inference validated.

Source/schema references checked before adapter implementation:

- OpenAI: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
- Claude: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Grok: https://docs.x.ai/developers/model-capabilities/text/structured-outputs
- Ollama: https://docs.ollama.com/api/chat

Skill reuse is proved between the API and direct Python binding. MCP/n8n and second-business-configuration reuse remain pending. Output envelope schemas for non-extraction skills are not yet fully closed nested domain schemas. Full quality evaluation and live canaries remain required. The regular app factory does not yet load .env/model profiles; do not assume entering a key activates inference.
