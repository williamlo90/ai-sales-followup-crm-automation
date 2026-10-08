# Phase Plan — AI Sales Follow-up and CRM Automation

Proyek 04: pekerjaan sales setelah percakapan, memakai Odoo, Microsoft 365 dan n8n. Diperbarui 2026-10-08. **Rencana implementasi, bukan hasil yang sudah dicapai.**

Urutan V1: **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**. **Phase 9 opsional, selalu terakhir.** Ikuti [aturan eksekusi lokal](../LOCAL-FIRST-EXECUTION.md): Phase 0–6 tanpa kewajiban Docker; testing ringan dan security sejak awal. Integrasi nyata/container acceptance tertunda tetap tercatat untuk Phase 7; mock bukan bukti live integration.

## Phase 0 — Scope bisnis dan dependency nyata

- [x] Dua perjalanan utama: email/meeting → proposal CRM + draft follow-up; due follow-up → cek aktivitas/opt-out/approval → tindakan yang masih valid. Scope: `docs/phase-0/BUSINESS-SCOPE.md`.
- [x] Output benar: account/deal tepat, komitmen terbaru, field diff dapat diperiksa, tidak ada aktivitas/email ganda dan hasil memiliki bukti. Expected outcomes: `docs/phase-0/ACCEPTANCE.md`; ini definisi, bukan klaim hasil implementasi.
- [x] Audit kontrak MCP/API Odoo #2; gunakan konektor itu tanpa membuat ulang server generik atau menyalin seluruh repo. Audit reuse dan capability gap: `docs/phase-0/DEPENDENCIES.md`.
- [ ] Inventaris test mailbox Microsoft 365, Graph scopes/consent/license, credentials Odoo/model dan hardware. Akun uji milik sendiri cukup; akses gratis tidak diasumsikan.
- [x] Pin versi n8n, mapping node/API dan resource budget; engine container menunggu Phase 7. Jangan mewajibkan workaround npm yang deprecated. Evidence: `docs/phase-0/N8N-MAPPING.md`; endpoint plan belum seluruhnya implemented.
- [ ] Bekukan acceptance matrix dan fixtures; dependency belum tersedia dicatat spesifik, tanpa menghentikan unit/contract work yang independen.

**Gate:** scope, permissions, mapping, budgets dan expected outcomes jelas; tidak menyalakan Docker.

## Phase 1 — Fondasi Python, TypeScript dan kontrol transaksi

- [ ] Bangun FastAPI, UI TypeScript/React, PostgreSQL schema/migrations dan config/health sebagai proses lokal.
- [ ] Implementasikan tenant/role scope, proposal versions, approval terpisah untuk CRM dan email send, operation contracts serta audit.
- [ ] Buat adapter boundaries Odoo/Graph/model/scheduler dan contract doubles. Native PostgreSQL terisolasi opsional bila sudah tersedia.
- [ ] Siapkan Dockerfile/Compose dan n8n persistent-state/encryption-key configuration secara statis tanpa build/start.
- [x] Uji auth, input validation, preview UI dan error states sejak fitur dibuat. Evidence fondasi: `docs/evidence/foundation-checks.md`; pengujian berlanjut saat fitur ditambah.

**Gate:** proposal dapat dibuat/diperiksa/disetujui pada local harness, unauthorized actions ditolak; database/engine acceptance tetap Phase 7.

## Phase 2 — Alur sales deterministik

- [ ] Cocokkan contact/account/deal dengan alasan; ambiguous identity masuk review.
- [ ] Commitment schema mencatat kutipan, tanggal/timezone, owner, revision dan conflict; uji merge rules memakai labeled fixtures.
- [ ] Buat field diff, CRM activity dan email draft; source/CRM berubah membatalkan approval lama.
- [ ] Tangani opt-out, duplicate/out-of-order events, follow-up yang sudah dilakukan, deleted records serta partial outcomes.
- [ ] Pisahkan prepared/approved/dispatched/accepted/verified/unknown. Graph accepted atau Sent Items tidak otomatis membuktikan delivered/read.
- [ ] Send switch default off; recipient allowlist hanya mailbox uji. Tidak mengirim email pelanggan nyata untuk acceptance.

**Gate:** business rules, approval dan reconciliation lulus pada reference/failure cases tanpa membutuhkan LLM untuk menegakkan aturan.

## Phase 3 — Assistant dan reusable skills

- [ ] Implementasikan `extract_commitments`, `prepare_crm_update`, `draft_followup`, `reconcile_followup`; satu core implementation dipakai UI/MCP/n8n.
- [ ] Implementasikan OpenAI, Claude dan Grok adapters dengan output contract sama; jalankan canary nyata dari proses lokal pada data yang diizinkan bila credentials tersedia.
- [ ] Jalankan Ollama native pada tugas yang sama; local-only inference menolak hosted fallback. Microsoft 365 tetap online, sehingga keseluruhan sistem bukan offline.
- [ ] Validasi source claims, schemas, long threads, conflicting commitments, injection dan missing information. Pilih default model dari hasil evaluasi.
- [ ] Simpan model/prompt/schema revision, latency, usage/cost dan outcome; missing credentials/canary tetap pending, bukan live-validated.

**Gate:** satu hosted profile menjalankan tugas lengkap dengan benar; contract suite lulus. Status tiap provider/local profile terpisah; gap tersisa harus ditutup sebelum klaim cakupan penuh.

## Phase 4 — MCP dan business adapters

- [ ] Implementasikan sales tools spesifik: context, commitments, prepare, approved CRM apply, approved send dan verify; reuse konektor Odoo #2.
- [ ] Jalankan stdio MCP reference client nyata tanpa Docker; uji scope, errors, cancellation, stale proposals dan replay pada adapter doubles.
- [ ] Implementasikan Graph/Odoo clients: pagination, mailbox scope, checkpoint/delta bila tersedia, token expiry, rate limits dan bounded retries.
- [ ] Read-only Graph canary boleh pada mailbox uji sendiri dari proses lokal. Connected state-changing acceptance lengkap dijadwalkan Phase 7.
- [ ] Operation ID dan read-back menangani unknown outcomes; send timeout tidak memicu pengiriman ulang tanpa rekonsiliasi.

**Gate:** adapters/protocol contracts executable; pending live acceptance jelas. Fake tidak disebut connected integration.

## Phase 5 — Workflow n8n siap import dan workspace

- [ ] Buat dua export versioned di `automation/n8n/`: intake → prepare → approval wait → apply/verify; due follow-up → eligibility → prepare/review → apply/verify.
- [ ] n8n memiliki trigger/jadwal/koordinasi. Python/PostgreSQL memiliki permissions, proposal, approval, idempotency dan outcome. Jangan menduplikasi business rules pada nodes.
- [ ] Local V1 memakai authenticated outbound polling supaya tidak wajib webhook publik. Approval disimpan di backend; workflow memeriksa status dengan izin yang benar.
- [ ] Siapkan node/version mapping, service identity, credential placeholders, timezone, checkpoints dan bounded retry; export tidak memuat secrets.
- [ ] Periksa export/schema statis dan endpoint contracts melalui reference runner. Itu bukan bukti engine n8n; import/execute/wait/restart nyata wajib Phase 7.
- [ ] UI menampilkan evidence, field diff, separate approvals, unknown outcomes dan operator recovery.

**Gate:** workflow definitions/endpoints/UI siap sesi engine nyata; status workflow-designed/contract-validated, belum n8n-validated.

## Phase 6 — Kualitas dan manfaat sebelum Docker

- [ ] Bekukan dev/regression dan held-out berdasarkan thread/account families; expected outcomes berasal dari source dan rules.
- [ ] Ukur account/deal linkage, commitment extraction/revisions, proposal correctness, draft factuality, abstention dan policy compliance.
- [ ] Bandingkan OpenAI/Claude/Grok pada tugas sama dengan real canaries; satu default runtime cukup, adapter-only belum membuktikan ketiga API.
- [ ] Evaluasi local profile nyata; model gagal tidak disebut sukses hanya karena guardrail menahan write.
- [ ] Bandingkan direct CRM/manual dan assisted pada tugas setara: correctness, corrections, manual touches, active work dan waiting time. Single-operator mandiri boleh, dilabeli sesuai lingkup; bukan customer ROI.
- [ ] Tetapkan workload/SLO/resource budget, freeze candidate dan matrix acceptance n8n/Graph/Odoo/Docker. Jangan melaporkan p95 engine dari mock runner.

**Gate:** kualitas native/domain memenuhi rubric scope; dependency/live-provider gaps tetap terlihat. Release menunggu connected/container acceptance Phase 7.

## Phase 7 — Docker, n8n dan connected acceptance nyata

- [ ] Sesi mesin terbatas mengikuti LOCAL-FIRST-EXECUTION.md: cek read-only, data/ports/volumes khusus, tidak menghentikan stack #1/#2/#3.
- [ ] **7A Data/adapter:** PostgreSQL nyata, migrations, locking/transactions/tenant isolation; Odoo nyata melalui #2 pada database test khusus, dengan company/record mapping terverifikasi.
- [ ] **7B Engine:** jalankan n8n versi dipin pada profil minimal; import kedua export, credentials lab, trigger/wait/approval/restart, timezone dan error branches.
- [ ] **7C Connected slice:** mailbox Microsoft 365 uji → n8n → AI/domain → review → Odoo update/draft → read-back; komponen minimum tersedia bersamaan, bukan fake acceptance.
- [ ] **7D Controlled send:** aktifkan send switch lab dengan approval eksplisit, hanya recipient uji allowlisted. Verifikasi accepted/sent/received sesuai bukti tenant. Timeout masuk unknown; rekonsiliasi sebelum retry. Jangan mengklaim delivered/read tanpa observasi.
- [ ] **7E Failure/security:** expired token, rate limit, duplicate trigger, wrong tenant, stale approval, engine/worker restart, unknown write, missed schedule dan partial success. Periksa jumlah efek akhir, bukan node success.
- [ ] **7F Beban/kualitas:** ulangi kualitas pada stack final; normal/peak/soak dalam budget, pisahkan stub load dan bounded real-provider tests. Ukur p50/p90/p95 verified workflow, errors, throughput, backlog, RAM dan cost per correct task.
- [ ] **7G Operasi:** restore database/n8n state/encryption configuration, clean import, rollback, Linux/VM startup/reboot dan alert delivery dalam lab terisolasi.
- [ ] Tutup acceptance provider/local yang masih pending atau nyatakan scope terbatas yang disepakati; jangan menyebut semua requirement terpenuhi bila belum. Perbaikan integrasi diikuti regression dan acceptance ulang.

**Gate:** local connected candidate lulus n8n/Odoo/Microsoft 365 nyata; critical bypass/duplicate effect/false-success nol pada declared suite. Hardware/akun belum tersedia berarti acceptance blocked, bukan mock-pass.

## Phase 8 — Delivery lokal dan support

- [ ] Demo English: conversation → CRM diff/follow-up → approval → hasil Odoo/mailbox → failure/recovery, memakai data uji.
- [ ] Serahkan user/operator guide, export n8n tersanitasi, credential setup, activation/deactivation, schedule/timezone, troubleshooting, backup/restore dan rollback.
- [ ] Clean install/import dari release artefact dan versi dipin; evidence cocok dengan source snapshot.
- [ ] Mulai support lokal: health/failed jobs/unknown outcomes review, incident drill, recovery dan regression setelah perubahan. Catat durasi aktual, bukan klaim customer production support.
- [ ] Jelaskan laptop sleep/offline menghentikan workflow; buktikan catch-up/checkpoint tanpa pengiriman ulang setelah restart.
- [ ] Case study berisi hasil terukur, integration/model status dan batas kemampuan. Buktikan reuse skills lintas caller tanpa menyalin logic.

**Gate V1:** **local-delivered / connected-sandbox-validated** dengan n8n. Cloud dan Make.com/Zapier tidak menghalangi release utama; extension tetap tercatat.

## Phase 9 — Cloud dan varian automation opsional, paling akhir

- [ ] Jika dibutuhkan jadwal 24 jam/shared access, pilih Azure hosting sesuai runtime dan persistent n8n state; siapkan biaya, secrets, access, backup, alerts dan rollback sebelum provisioning.
- [ ] Setelah Phase 0–8 lulus, deploy bila dipilih; ulangi connected workflow, authorization, quality, bounded load, recovery dan alerts. Bukti lokal bukan bukti cloud.
- [ ] Pertahankan rencana Make.com/Zapier: satu workflow setara pada sandbox, domain API/permissions/expected outcomes sama. Jalankan varian terpisah dengan engine lain nonaktif agar tidak menggandakan side effects.
- [ ] Bandingkan correctness, recovery, handover dan biaya; credentials/license/access belum tersedia dicatat. Aktivasi SaaS automation hanya pada fase terakhir ini.
- [ ] Catat runtime, owner support, biaya dan teardown. Jika cloud tidak dipilih: **not selected — local V1 selesai**, tanpa klaim uptime 24 jam.

**Gate extension:** cloud/Make/Zapier hanya disebut validated setelah bukti varian tersedia. Ongoing support lokal sudah dimulai Phase 8.
