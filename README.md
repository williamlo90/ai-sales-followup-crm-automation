# AI Sales Follow-up & CRM Automation

Proyek 04: **AI Sales Follow-up & CRM Automation**

Tanggal rencana: 2026-10-08. Status 2026-10-09: **Phase 0–1 sedang dikerjakan; fondasi proposal/review lokal sudah berjalan**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia. Lihat [checkpoint](docs/EXECUTION-STATUS.md), [panduan lokal](docs/LOCAL-DEVELOPMENT.md), dan [hasil pengujian fondasi](docs/evidence/foundation-checks.md).

**Pengguna:** Sales representative dan sales operations.

**Hasil bisnis:** Mengurangi pekerjaan setelah percakapan pelanggan dengan mengubah email dan catatan meeting menjadi perubahan CRM serta draft follow-up yang benar.

**Alur:** Email/catatan meeting → cocokkan account/deal → ambil komitmen pelanggan → proposal CRM/task/email → review → update CRM → approved send bila diaktifkan → delivery check dan audit.

**Stack keputusan:** Python + FastAPI; TypeScript + React; custom MCP server TypeScript yang memakai konektor 02; Microsoft Graph untuk Microsoft 365; Odoo API; n8n sebagai orchestrator workflow; Make.com dan Zapier sebagai extension pembanding Phase 9 opsional; PostgreSQL; Docker/Linux; OpenAI, Claude, Grok; Ollama.

**Automation:** Pakai n8n sebagai orchestrator utama workflow bisnis. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).

Pilihan framework adalah keputusan implementasi kita, bukan klaim bahwa JD mewajibkan merek framework tersebut. Versi API/library/model ditetapkan saat Phase 0 berdasarkan dokumentasi resmi dan lingkungan yang tersedia.

## Baseline dan reuse

Proyek baru. Gunakan kontrak konektor Odoo dari 02. Implementasi awal memakai contract fake sampai konektor siap; acceptance akhir wajib connected sandbox. n8n tidak menjadi pemilik aturan approval atau data bisnis.

## Dokumen kerja

- [PHASES.md](PHASES.md)
- [AI-AGENTS.md](AI-AGENTS.md)
- [REUSABLE-SKILLS.md](REUSABLE-SKILLS.md)
- [MCP-INTEGRATIONS.md](MCP-INTEGRATIONS.md)
- [BUSINESS-PLATFORM.md](BUSINESS-PLATFORM.md)
- [LOCAL-AI-AND-PROVIDERS.md](LOCAL-AI-AND-PROVIDERS.md)
- [SECURITY-TESTING-MONITORING.md](SECURITY-TESTING-MONITORING.md)
- [PROJECT-DELIVERY.md](PROJECT-DELIVERY.md)

## Ukuran keberhasilan

CRM update precision dan coverage; correct account/deal linkage; commitment revision correctness; manual touches; follow-up preparation time; duplicate sends; p95 verified workflow; biaya per tugas benar.

## Cara mulai

1. Buka PHASES.md dan kerjakan Phase 0.
2. Catat apa yang existing, perlu verifikasi, dan baru. Semua checklist folder ini dimulai belum selesai.
3. Buat satu alur lengkap, uji hasilnya, baru tambah variasi; ikuti urutan fase dan dependency.
4. Catat evidence path/run ID saat menutup fase. Phase 0–6 tanpa kewajiban Docker; engine/connected acceptance Phase 7, delivery/support Phase 8. Cloud Phase 9 opsional, selalu terakhir.

Implementasi awal berisi FastAPI, React review UI dan penyimpanan SQLite khusus local harness. MCP, AI skills, operasi eksternal dan workflow n8n executable masih dalam antrean implementasi. PostgreSQL/Docker disiapkan statis; connected acceptance tetap Phase 7.

## Keputusan delivery terbaru

[Aturan eksekusi lokal](../LOCAL-FIRST-EXECUTION.md) mengatur penggunaan mesin. Implementasikan domain, UI, MCP, model adapters dan n8n exports sebelum sesi Docker. Microsoft 365 read-only canary/model API boleh dari proses lokal; Odoo/n8n end-to-end nyata wajib pada Phase 7.

V1 selesai pada Phase 8 sebagai local-delivered/connected-sandbox-validated. Cloud opsional bila membutuhkan jadwal 24 jam atau shared access. Make.com/Zapier tetap extension terencana pada fase terakhir, tidak menjadi syarat release n8n. Tidak mengulang pembangunan konektor Odoo #2; proyek ini membuktikan pekerjaan sales lintas aplikasi.
