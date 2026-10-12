# Custom MCP Server, APIs & Database

## Urutan eksekusi terbaru

Ikuti [PHASES.md](PHASES.md) dan [aturan eksekusi lokal](docs/LOCAL-FIRST-EXECUTION.md). Phase 0–6: implementasi serta unit/contract/native tests tanpa kewajiban Docker. Phase 7: integrasi nyata, Docker/Linux dan reliability. Phase 8: delivery lokal dan support. Phase 9: cloud/hosting extension opsional, selalu terakhir. Checklist kemampuan di bawah adalah target release, bukan kewajiban menjalankan container pada fase awal. Test double tidak menggantikan connected acceptance.

Proyek 04: **AI Sales Follow-up & CRM Automation**

Tanggal brief awal: 2026-10-08. Status V1: MCP stdio dan reference client lulus pengujian dari paket rilis bersih; rincian ada di [MCP server](mcp-server/README.md) dan [audit delivery](docs/phase-8/DELIVERY-AUDIT.md). Bagian berikut adalah requirement desain awal.

## Arsitektur keputusan

Assistant/client → **custom MCP server TypeScript** → domain API **Python** → **PostgreSQL** dan adapter **Odoo CRM + Microsoft 365**. MCP server tidak melewati business validation dengan menulis tabel langsung. AI memperoleh data SQL melalui query service yang terotorisasi dan terparameterisasi.

MCP server proyek ini punya capability spesifik, bukan server generik yang mengekspos semua API. Jika memakai konektor 02/03, import atau panggil kontraknya; jangan menyalin codebase konektor.

## Tools rencana

| Tool | Jenis | Kontrak ringkas |
| --- | --- | --- |
| `sales.get_deal_context` | read | deal reference → CRM + permitted messages |
| `sales.extract_commitments` | read | conversation ID → source-linked facts |
| `sales.prepare_changes` | prepare | facts + record version → proposal |
| `sales.apply_crm_changes` | write | approved proposal → CRM outcome |
| `sales.send_approved_draft` | write | draft + explicit approval → message receipt |
| `sales.verify_followup` | read | operation ID → delivery/CRM state |

## Syarat kontrak

- [ ] Pin MCP SDK dan protocol version yang didukung client; gunakan stdio untuk client lokal bila sesuai, authenticated HTTP untuk remote hanya saat deployment terakhir.
- [ ] Setiap tool memiliki description, strict input/output schema, source references, stable error codes, pagination bila perlu, dan output limits.
- [ ] Server memverifikasi identity, tenant/record scope, role, approval payload/version, serta idempotency key; input model bukan otorisasi.
- [ ] Write tools membutuhkan proposal dan approval sesuai risiko. Approval tidak boleh dibuat oleh agent yang hendak melakukan action tersebut.
- [ ] Uji protocol dari client, schema rejection, credentials expiry, injection, cancellation, error propagation, concurrency, dan retry.
- [ ] Simpan correlation ID dari assistant → MCP → Python → platform; logs cukup untuk diagnosis tanpa body sensitif secara default.

## Model data awal

tenant, account_map, deal, conversation, commitment, proposal, task, email_draft, approval, delivery_attempt, workflow_cursor, audit_event.

Tambahkan tenant foreign keys, unique constraints untuk external references/idempotency, optimistic versioning atau locking sesuai transaksi, migrations, retention, dan audit. SQL read-only query untuk reporting tidak menerima arbitrary SQL dari model.

**Selesai ketika:** satu alur melalui MCP mengubah atau membaca platform sesuai scope, database mencatat provenance, dan hasil benar dibuktikan lewat read-back/expected state. Unit tests langsung ke fungsi belum cukup untuk protocol acceptance.

## Hubungan dengan automation engine

Pakai n8n sebagai orchestrator utama workflow bisnis. Agent dapat memakai custom MCP tools; workflow memakai API atau MCP sesuai kebutuhan. Semua jalur menuju kontrol domain otoritatif, tanpa dua implementasi business rules.
