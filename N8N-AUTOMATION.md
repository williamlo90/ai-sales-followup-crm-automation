# Automation Decision — 04 - AI Sales Follow-up & CRM Automation

## Urutan eksekusi terbaru

Ikuti [PHASES.md](PHASES.md) dan [aturan eksekusi lokal](docs/LOCAL-FIRST-EXECUTION.md). Phase 0–6: implementasi serta unit/contract/native tests tanpa kewajiban Docker. Phase 7: integrasi nyata, Docker/Linux dan reliability. Phase 8: delivery lokal dan support. Phase 9: cloud/hosting extension opsional, selalu terakhir. Checklist kemampuan di bawah adalah target release, bukan kewajiban menjalankan container pada fase awal. Test double tidak menggantikan connected acceptance.

Status V1: dua export n8n dipakai pada sandbox dan diuji impor, jadwal serta recovery. Lihat [workflow exports](automation/n8n/README.md), [audit Phase 7](docs/phase-7/COMPLETION-AUDIT.md) dan [audit delivery](docs/phase-8/DELIVERY-AUDIT.md). Uraian berikut adalah alasan dan requirement desain awal.

**Keputusan:** Pakai n8n sebagai orchestrator utama workflow bisnis.

**Peran:** Email/meeting → context → AI extraction → CRM/email proposal → human review → approved changes → verification. Python menjadi layanan untuk kemampuan khusus dan kontrol transaksi.

**Alasan:** Make.com dan Zapier menjadi varian pembanding satu workflow Sales yang sama, bukan runtime tambahan yang wajib berada di semua jalur.

Dokumen ini menggantikan kewajiban lama memasang n8n di semua proyek. Keputusan V1 proyek ini adalah satu engine n8n; lihat [keputusan Phase 9](docs/phase-9/DECISION.md) untuk extension yang tidak dipilih.

## Workflow target

1. **Workflow utama:** Email atau catatan meeting baru → n8n meneruskan referensi percakapan ke backend → skills menyiapkan CRM diff, task, dan email draft → operator menyetujui → backend menjalankan perubahan dan memverifikasi hasil.
2. **Monitoring dan tindak lanjut:** Jadwal follow-up → backend mengecek due date, opt-out, aktivitas terbaru, dan approval yang masih berlaku → n8n memicu pekerjaan yang eligible. Tidak ada pengiriman email hanya karena timer aktif.

## Ownership dan acceptance

- Pilih pemilik orchestration, retries, approval records dan business state secara eksplisit. Satu operasi bisnis punya satu sumber status otoritatif.
- n8n boleh menjalankan agent, tool calls, branching, wait/approval dan reusable sub-workflows bila cocok. Pembagian Python/n8n adalah keputusan proyek, bukan batas kemampuan n8n.
- Approval dari UI aplikasi maupun workflow harus terikat actor, tenant, payload/version dan kewenangan; penerimaan callback atau teks approved tidak cukup.
- Side effects membutuhkan deduplication/idempotency dan verifikasi hasil. Unknown outcomes direkonsiliasi sebelum retry; state berhasil di engine tidak otomatis berarti masalah bisnis selesai.
- Scope authorization berlaku pada semua jalur: assistant, MCP, worker, automation engine dan direct API.

## Checklist implementasi

- [ ] Tetapkan boundary n8n/domain service dan source of truth sebelum implementasi; gunakan architecture comparison bila memperluas repo existing.
- [ ] Siapkan config/service identity/credential storage dan node/version mapping lebih awal; instalasi/start n8n self-hosted, persistent state serta health nyata pada Phase 7.
- [ ] Implementasikan workflow target dan simpan export tersanitasi di `automation/n8n/`; credentials tidak masuk Git.
- [ ] Uji trigger → hasil platform, duplicate/out-of-order events, restart, expired token, wrong tenant, stale approval, timeout sesudah side effect, unknown outcome, dan safe replay.
- [ ] Catat outcome correctness, verified completion, p95 end-to-end, backlog, resources dan biaya; bukan node latency saja.
- [ ] Buktikan alert delivery, sanitized execution history/retention, restore dan import pada instance bersih.
- [ ] Sertakan owner, activation/deactivation, schedule/timezone, troubleshooting, dan rollback dalam delivery.

## Fase

Phase 0 menentukan ownership/versi; Phase 1 menyiapkan code/config tanpa start n8n; Phase 5 membuat export dan contract fixtures; Phase 7 mengimpor serta menjalankan n8n container, connected workflows dan reliability; Phase 8 menyerahkan delivery lokal dan memulai support; Phase 9 cloud/Make/Zapier opsional dan TERAKHIR.


## Make.com dan Zapier — perbandingan terpisah

- [ ] Pilih satu workflow yang sama: conversation → validated proposal → approval → CRM update/draft follow-up → verified result.
- [ ] Buat varian Make.com dan Zapier menggunakan data, domain API, permissions dan expected outcomes yang sama dengan n8n.
- [ ] Bandingkan correctness, duplicate handling, recovery, kemudahan mengubah aturan/mapping, handover, total biaya pada volume yang dinyatakan, dan fitur/lisensi yang dibutuhkan.
- [ ] Account/API access yang belum ada diberi status pending. Jangan menyebut varian tested hanya dari template.
- [ ] Pilih satu runtime utama; varian lain menjadi bukti kemampuan adaptasi, bukan tiga engine yang menjalankan side effect sama secara paralel.

Desain/contract fixtures dapat disiapkan pada Phase 5. Aktivasi dan eksekusi flow SaaS Make/Zapier ditempatkan pada Phase 9 agar aturan deployment cloud terakhir tetap berlaku. Native cloud flows Power Automate juga mengikuti batas ini.

Make.com/Zapier tetap rencana extension pembanding, bukan gate selesai V1 n8n. Tidak dipilih atau akses belum tersedia tidak mengubah release lokal yang lulus menjadi gagal. Jangan menyalakan engine alternatif bersamaan untuk side effect yang sama.
