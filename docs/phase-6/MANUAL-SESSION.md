# Sesi manual vs assisted

Status: satu sesi manusia selesai dan tervalidasi pada2026-10-10; bukti docs/evidence/phase-6-manual-comparison.json. Manual3/4 benar,205.298s aktif; assisted4/4 benar,125.2705s aktif. Scope worksheet/cached assistance; belum mengukur waktu tunggu sistem live. Buka local/phase-6/manual-review.html di browser. Halaman mandiri tanpa server, API, email atau perubahan CRM.

1. Baca aturan pada halaman sebelum mulai. Kerjakan sendiri tanpa bantuan AI atau membuka label fixture.
2. Klik Mulai tugas. Tinjau data dan isi keputusan beserta alasan. Pada mode assisted, periksa saran core yang sudah terisi; koreksi bila perlu.
3. Gunakan Jeda jika terganggu. Pindah tab otomatis menjeda; klik Lanjut saat kembali. Jangan refresh/tutup di tengah sesi. Jawaban tugas selesai juga disimpan dalam localStorage browser sebagai cadangan.
4. Selesaikan delapan tugas, klik Simpan hasil JSON, lalu kirim file sales-manual-session-*.json di chat. Tidak perlu menyalin angka waktu secara manual.

Desain dibekukan di fixtures/evaluation/manual-review-v1.json: empat pasangan tugas due-follow-up setara (siap, opt-out, sudah dihubungi, data stale); urutan manual/assisted bergantian per pasangan. Empat tugas per mode, satu operator. Kondisi pasangan sama dengan account/tanggal berbeda, sehingga learning/carry-over tetap keterbatasan. Saran berasal dari due_eligibility core yang sama melalui scripts/prepare_manual_review.py. Label manual tidak dimasukkan ke halaman; label pembanding tetap di fixture. Ini baseline worksheet review keputusan, bukan pengukuran penggunaan CRM lengkap, live AI generation atau customer ROI.

Data: interval foreground aktif memakai performance.now, jeda terpisah, event perubahan field dan submit, timestamp UTC, jawaban awal/akhir serta hash fixture. Waktu aktif termasuk membaca dan overhead halaman, bukan bukti perhatian terus-menerus. Field changes adalah edit, bukan otomatis koreksi benar. Corrections dan correctness harus dinilai dari jawaban terhadap label; system waiting null karena bantuan sudah dihitung. Jangan mengganti null dengan angka latency AI atau menganggapnya penghematan waiting time.

Sebelum laporan: verifikasi hash, delapan ID unik/urutan/mode, event/timestamp/interval masuk akal dan completed=true. Nilai tiap jawaban, pisahkan per mode/pasangan; laporkan angka mentah dan sampel kecil, jangan mengekstrapolasi ROI. Bukti tes browser otomatis tidak dihitung sebagai sesi manusia.

Regenerasi: .venv/Scripts/python.exe -m scripts.prepare_manual_review. CLI scripts/manual_session.py tersedia untuk pencatatan sesi aplikasi lain dengan interval work/wait eksplisit; hasil CLI tidak dicampur dengan worksheet ini.

Pemeriksaan hasil oleh agent: `.venv/Scripts/python.exe -m scripts.score_manual_review PATH_HASIL.json --output local/phase-6/manual-scored.json`. Output eksklusif tidak menimpa hasil lama. Pemeriksaan tidak mengklaim file otomatis berasal dari manusia; konfirmasi operator tetap diperlukan.
