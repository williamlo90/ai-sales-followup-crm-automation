# Business Platform & Workflow Integration

## Urutan eksekusi terbaru

Ikuti [PHASES.md](PHASES.md) dan [aturan eksekusi lokal](../LOCAL-FIRST-EXECUTION.md). Phase 0–6: implementasi serta unit/contract/native tests tanpa kewajiban Docker. Phase 7: integrasi nyata, Docker/Linux dan reliability. Phase 8: delivery lokal dan support. Phase 9: cloud/hosting extension opsional, selalu terakhir. Checklist kemampuan di bawah adalah target release, bukan kewajiban menjalankan container pada fase awal. Test double tidak menggantikan connected acceptance.

Proyek 04: **AI Sales Follow-up & CRM Automation**

Tanggal rencana: 2026-10-08. Status: **rencana implementasi; belum ada implementasi baru dalam folder ini**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

**Platform utama:** Odoo CRM + Microsoft 365.

**Alur bisnis:** Email/catatan meeting → cocokkan account/deal → ambil komitmen pelanggan → proposal CRM/task/email → review → update CRM → approved send bila diaktifkan → delivery check dan audit.

## Checklist implementasi

- [ ] Tetapkan produk/edition/API version, permission scopes, batas sandbox, dan credential owner. Verifikasi endpoints dari dokumentasi resmi saat implementasi.
- [ ] Dokumentasikan entity mapping, external IDs, sumber otoritatif tiap field, timestamp/timezone, freshness, dan aturan konflik.
- [ ] Implementasikan read/sync terlebih dahulu, kemudian prepare/approve/write/verify. Webhooks perlu autentikasi/signature bila tersedia dan replay protection.
- [ ] Gunakan test tenant atau instalasi lokal; data sintetis mengandung kasus valid, ambiguity, dan exception.
- [ ] Tangani pagination, rate limit, retries dengan backoff, expired credentials, deleted records, event out-of-order, dan partial success.
- [ ] Catat result verification yang spesifik terhadap operasi. HTTP 2xx/accepted tidak otomatis berarti hasil bisnis final.
- [ ] Terapkan keputusan automation: Pakai n8n sebagai orchestrator utama workflow bisnis. Rincian di [N8N-AUTOMATION.md](N8N-AUTOMATION.md); semua jalur memakai aturan akses dan verifikasi hasil yang konsisten.
- [ ] Buktikan mapping/business configuration kedua, recovery unknown outcome, serta tidak adanya duplicate side effects dalam skenario yang diuji.

## Akses yang belum tersedia

Catat dependency nyata beserta status dan langkah memperoleh akses. ConnectWise/Microsoft 365/Odoo hosted mungkin membutuhkan tenant, scope, edition, atau lisensi yang sesuai. Jangan menganggap sandbox gratis tersedia. Sambil menunggu, lanjutkan contract fake dan lokal, tetapi connected acceptance tetap pending. Tidak ada permintaan agar orang lain mencoba demo sebagai prerequisite.

## Bukti yang disimpan

- Request/response disanitasi atau snapshot field penting; bukan credentials atau data pelanggan.
- External record ID, approval ID, source versions, timestamp, expected outcome, observed outcome, dan read-back.
- Hasil retry/concurrency dan bukti jumlah side effects di platform tujuan.
- Batas integrasi yang masih draft-only, sandbox-only, atau belum diuji live ditulis jelas.

**Selesai ketika:** business owner bisa mengikuti satu pekerjaan dari input sampai hasil platform, termasuk satu kegagalan dan pemulihannya.

## Connected acceptance terjadwal

Phase 0 memeriksa akses/edition/scopes; Phase 4 boleh read-only Graph canary dari proses lokal. Phase 7 wajib menjalankan satu alur n8n → domain → Odoo/Microsoft 365 nyata pada test records/mailboxes. Send default off; hanya approval eksplisit dan recipient uji allowlisted. HTTP accepted/Sent Items bukan bukti delivered/read; nyatakan tingkat verifikasi aktual dan rekonsiliasi unknown send sebelum retry.
