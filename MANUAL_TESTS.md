# Manual hardware tests

Tanggal: 2026-08-12 (Asia/Jakarta)

Environment yang terdeteksi:

- Windows 11 Home 64-bit, build 10.0.26200.
- AMD Ryzen 7 6800H with Radeon Graphics.
- Device kamera berstatus OK di Windows: `Integrated Camera` dan `V380 FHD Camera`. OpenCV index `0` tidak dipetakan secara pasti ke nama device oleh API yang dipakai.
- Python 3.12.10, MediaPipe 0.10.35, OpenCV 4.12.0, NumPy 2.2.6.

## Hasil yang dijalankan

| Check | Hasil | Bukti/catatan |
|---|---|---|
| Dependency/model smoke | PASS | Hand Landmarker `VIDEO` memproses frame RGB sintetis dan ditutup. Hanya `opencv-contrib-python` yang terpasang. |
| Default camera open/read/release | PASS (satu probe) | Frame pertama 329 ms, ukuran aktual 1280×720, capture melaporkan 30 FPS, lalu `release()` dipanggil. |
| AC-M01 startup <=5 detik atau error actionable | PASS | Window startup terdeteksi dalam 769 ms. Pada run berikutnya, kegagalan driver stream menghasilkan pesan terkontrol `Camera frame stream failed 30 consecutive times...`. |

Setelah harness pengujian menghentikan paksa process kamera pada percobaan awal, backend Windows MSMF mulai mengembalikan status read error `-1072875772` meskipun device masih berstatus OK. Karena itu sesi gesture interaktif dan protocol durasi panjang tidak dilanjutkan. Hasil probe sukses awal tetap dicatat, tetapi tidak dipakai untuk mengklaim stability, gesture accuracy, atau throughput aplikasi.

## Acceptance matrix

| ID | Status | Catatan |
|---|---|---|
| AC-M01 | PASS | Startup window 769 ms; controlled camera-stream error juga terverifikasi. |
| AC-M02 | NOT RUN | Arah cursor terhadap tangan tidak diamati. |
| AC-M03 | NOT RUN | Alignment 21 landmark tidak diamati secara manual. |
| AC-M04 | NOT RUN | Empat pose tidak dipegang dan diukur. |
| AC-M05 | NOT RUN | Jitter visual raw versus EMA tidak dibandingkan. |
| AC-M06 | NOT RUN | Blur drag empat arah tidak dilakukan dengan tangan. |
| AC-M07 | NOT RUN | Selection fisik 10×10 tidak dilakukan. |
| AC-M08 | NOT RUN | Cube tidak dibuat dengan tangan. |
| AC-M09 | NOT RUN | Cube tidak digerakkan dengan tangan. |
| AC-M10 | NOT RUN | Pinch di luar cube tidak dilakukan. |
| AC-M11 | NOT RUN | Fist fisik tidak diuji. |
| AC-M12 | NOT RUN | Hand occlusion >250 ms tidak dilakukan. |
| AC-M13 | NOT RUN | Mode switch saat interaction fisik tidak dilakukan. |
| AC-M14 | NOT RUN | Protocol 60 detik dan median FPS tidak dijalankan; tidak ada angka performa yang diklaim. |
| AC-M15 | NOT RUN | Sesi mixed-use 10 menit tidak dijalankan. |
| AC-M16 | NOT RUN | `Q`/`Esc`/window close dengan stream hardware stabil belum selesai diuji end-to-end. Cleanup path sudah dicakup tes otomatis. |

Untuk menyelesaikan item `NOT RUN`, pulihkan/reconnect kamera atau reboot backend kamera, lalu jalankan `python -m gesturecam` dan ikuti matrix hardware di `PRD.md` Section 16.3. Catat resolusi aktual, median FPS setelah warm-up, durasi, dan hasil tanpa memperkirakan angka.
