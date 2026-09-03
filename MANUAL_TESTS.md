# Manual hardware tests

Tanggal pembaruan fokus: 2026-08-13 (Asia/Jakarta)

## Peace Blur — Two Hands

| Scenario | Status | Catatan |
|---|---|---|
| Kamera terbuka dan feed mirrored | NOT RUN | Jalankan pada kamera pilihan pengguna. |
| Tangan tampil sebagai 21 landmark | NOT RUN | Perlu observasi webcam nyata. |
| Peace stabil pada tangan pertama mengaktifkan blur penuh | NOT RUN | Jalur classifier, debounce, dan blur lulus tes otomatis; kenyamanan gesture perlu diuji nyata. |
| Peace stabil pada salah satu dari dua tangan mengaktifkan blur | PASS (automated) | Guard runtime menguji peace pada slot kedua. |
| Satu frame Peace tidak memicu | PASS (automated) | Debounce tiga observasi tercakup tes. |
| Open Palm/Fist/Pointing/Unknown tidak memicu blur | PASS (automated) | Guard runtime diuji langsung. |
| Tangan hilang mematikan blur | PASS (automated) | Blur mensyaratkan `hand_present`. |
| `Esc`, `Q`, dan window close melepas kamera | PASS (automated) | Cleanup normal dan controlled failure diuji. |

Jangan klaim akurasi gesture atau FPS hardware sebelum menjalankan aplikasi dengan webcam nyata.
