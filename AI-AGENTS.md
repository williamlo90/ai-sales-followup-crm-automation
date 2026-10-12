# AI Agents, Assistants & Bots

## Urutan eksekusi terbaru

Ikuti [PHASES.md](PHASES.md) dan [aturan eksekusi lokal](docs/LOCAL-FIRST-EXECUTION.md). Phase 0–6: implementasi serta unit/contract/native tests tanpa kewajiban Docker. Phase 7: integrasi nyata, Docker/Linux dan reliability. Phase 8: delivery lokal dan support. Phase 9: cloud/hosting extension opsional, selalu terakhir. Checklist kemampuan di bawah adalah target release, bukan kewajiban menjalankan container pada fase awal. Test double tidak menggantikan connected acceptance.

Proyek 04: **AI Sales Follow-up & CRM Automation**

Rencana awal: 2026-10-08. Status saat ini: V1 delivered locally / connected-sandbox-validated. Lihat [audit delivery](docs/phase-8/DELIVERY-AUDIT.md) untuk kemampuan yang telah diverifikasi; daftar di bawah adalah brief desain awal, bukan daftar klaim produksi.

## Tugas assistant

Mengurangi pekerjaan setelah percakapan pelanggan dengan mengubah email dan catatan meeting menjadi perubahan CRM serta draft follow-up yang benar.

Pengguna: Sales representative dan sales operations.

Alur: Email/catatan meeting → cocokkan account/deal → ambil komitmen pelanggan → proposal CRM/task/email → review → update CRM → approved send bila diaktifkan → delivery check dan audit.

## Kemampuan yang dibangun

- Cocokkan contact/account/deal dan tampilkan alasan; hubungan ambigu meminta review.
- Ekstrak komitmen, tanggal, perubahan kebutuhan, dan next steps beserta kutipan sumber.
- Gabungkan kronologi percakapan dengan CRM state; revisi komitmen tidak dianggap sebagai komitmen tambahan.
- Preview field-level diff, task, dan email; approval terpisah untuk CRM write dan pengiriman email.
- Tangani timezone, duplicate thread events, opt-out, follow-up yang sudah dilakukan, serta perubahan CRM setelah proposal.
- Sediakan workflow n8n yang memanggil backend terotorisasi; retry scheduler tidak menggandakan email atau aktivitas.

## Kontrak perilaku

- Input membawa task ID, authenticated actor, tenant, permitted scope, dan referensi data. Scope berasal dari server, bukan dipercaya dari prompt.
- Output minimal: status, facts dengan source references, missing information, proposed actions, reason, dan confidence jika memiliki makna terkalibrasi. Confidence sendiri tidak memberi izin eksekusi.
- Tools dan jumlah langkah dibatasi; ada timeout/cancellation dan terminal state. Tugas di luar kemampuan menghasilkan klarifikasi atau eskalasi.
- Business rules, arithmetic, permissions, approval dan state transitions ditegakkan domain service Python.
- Prompt tidak memuat credentials. Evidence dari dokumen/pesan dianggap input tidak tepercaya, bukan instruksi untuk memperluas akses.
- Bedakan recommendation, approved, dispatched, accepted, verified, failed, dan unknown sesuai kebutuhan proyek. Jangan mengklaim action berhasil hanya dari teks model.
- Mulai satu orchestrator dan skills deterministik. Multi-agent hanya jika pemisahan tanggung jawab memberi manfaat terukur.

## Artefak implementasi yang harus ada

- [ ] Workflow dengan typed contracts, durable state dan recovery path; orchestration mengikuti keputusan proyek (Python atau n8n), bukan wajib dua engine.
- [ ] Assistant UI/reference client TypeScript dengan preview bukti, proposal, approval dan status.
- [ ] Prompt/schema/version registry serta adapters hosted/local.
- [ ] Scenario tests untuk happy path, ambiguous input, refusal/abstention, injection, dan tool failure.
- [ ] Run trace yang menghubungkan input, model/skill/tool versions, approval, hasil tujuan, latency, dan biaya tanpa membocorkan secrets.

**Selesai ketika:** operator dapat menjalankan demo pada PROJECT-DELIVERY.md; hasil diperiksa terhadap reference outcome; kegagalan tidak ditampilkan sebagai sukses.

## Pemilik orchestration

Pakai n8n sebagai orchestrator utama workflow bisnis. Email/meeting → context → AI extraction → CRM/email proposal → human review → approved changes → verification. Python menjadi layanan untuk kemampuan khusus dan kontrol transaksi. Make.com dan Zapier menjadi varian pembanding satu workflow Sales yang sama, bukan runtime tambahan yang wajib berada di semua jalur. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).
