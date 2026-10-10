# OpenAI development pilot pricing

Verified 2026-10-10 from https://developers.openai.com/api/docs/models/gpt-4.1-mini . The page lists gpt-4.1-mini-2025-04-14, Responses and structured outputs. Standard text pricing is USD0.40 per million input tokens and USD1.60 per million output tokens. No cached-input discount is assumed. Access for this project's account is only established by an actual request.

Pilot: dev-v2-01 only, frozen by the dataset content hash recorded before calling. Expected status ready; owner Mira; due 2026-11-02T09:00:00Z; active initial revision; exact quote from dev-v2-01-thread. The source explicitly commits to emailing the fixed-price quotation. This source/label has been reviewed before the pilot. Broader dataset labels and final freeze remain pending.

Runner uses the existing adapter, one call, 4096 output-token bound, no retries, one shared local/phase-6/budget.sqlite ceiling of USD1. Input UTF-8 bytes plus schema/system text are capped at 16000, with an 8192-token framing margin in the conservative cost reservation. Actual usage cannot free reservations. An overrun freezes further calls. Previous local/openai-canary.json remains untouched.

## Additional development profile, 2026-10-10

GPT-5.6 Luna with explicit low reasoning uses the same Responses adapter and 4096 total output limit. Official model page https://developers.openai.com/api/docs/models/gpt-5.6-luna lists USD0.20/M input, USD1.20/M output and cache writes at 1.25 times input. Reservations and usage estimates conservatively use USD0.25/M for every input token and USD1.20/M output, without cache discount. The alias has no dated snapshot listed; raw response model and run provenance are retained. This is a development comparison, not an accepted default. All profiles share the existing USD1 ledger; app configuration is unchanged.
