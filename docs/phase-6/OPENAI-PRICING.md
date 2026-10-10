# OpenAI development pilot pricing

Verified 2026-10-10 from https://developers.openai.com/api/docs/models/gpt-4.1-mini . The page lists gpt-4.1-mini-2025-04-14, Responses and structured outputs. Standard text pricing is USD0.40 per million input tokens and USD1.60 per million output tokens. No cached-input discount is assumed. Access for this project's account is only established by an actual request.

Pilot: dev-v2-01 only, frozen by the dataset content hash recorded before calling. Expected status ready; owner Mira; due 2026-11-02T09:00:00Z; active initial revision; exact quote from dev-v2-01-thread. The source explicitly commits to emailing the fixed-price quotation. This source/label has been reviewed before the pilot. Broader dataset labels and final freeze remain pending.

Runner uses the existing adapter, one call, 4096 output-token bound, no retries, one shared local/phase-6/budget.sqlite ceiling of USD1. Input UTF-8 bytes plus schema/system text are capped at 16000, with an 8192-token framing margin in the conservative cost reservation. Actual usage cannot free reservations. An overrun freezes further calls. Previous local/openai-canary.json remains untouched.
