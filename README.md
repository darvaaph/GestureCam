# GestureCam — Instant Webcam Privacy Blur via Peace Sign

GestureCam adalah aplikasi *real-time computer vision* yang menampilkan feed webcam yang dicerminkan (*mirrored*), melacak hingga dua tangan secara simultan menggunakan MediaPipe, dan secara instan memburamkan (*full-frame Gaussian blur*) seluruh feed kamera saat gestur damai/peace (`PEACE` / simbol V) terdeteksi stabil pada salah satu tangan. 

Overlay status HUD dan visualisasi landmark tangan tetap tajam di atas lapisan blur agar feedback status sistem selalu terbaca dengan jelas.

```text
[Webcam Feed] ──▶ [MediaPipe Landmarker] ──▶ [Heuristic Peace Detection]
                                                       │
                                            (Debounce 3 Frames)
                                                       ▼
[Normal Video] ◀──── (Gesture Release) ──── [Full-Frame 81x81 Blur]
```

---

## Fitur Utama

- **Real-Time Hand Tracking:** Melacak 21 titik sendi 3D hingga dua tangan secara bersamaan menggunakan Google MediaPipe Hand Landmarker Task (model TFLite float16).
- **Scale-Invariant Geometric Heuristics:** Klasifikasi gestur berdasarkan sudut vektor fleksi jari dan rasio radial terhadap skala telapak tangan, sehingga akurat pada berbagai jarak tangan ke kamera.
- **Anti-Flicker Debounce:** Memerlukan konfirmasi 3 frame berturut-turut sebelum mengaktifkan atau menonaktifkan blur, mencegah *flickering* akibat noise gerakan tangan sekilas.
- **Layered In-Place Blur:** Menggunakan Gaussian Blur $81 \times 81$ in-place untuk privasi maksimal pada resolusi 720p, dengan OSD HUD (FPS, Camera Index, Status) yang tetap tajam di lapisan paling atas.
- **Clean Architecture & 100% Testable:** Logika matematika dan stabilisasi terpisah dari hardware I/O, memungkinkan automated testing tanpa memerlukan perangkat webcam fisik.

---

## Struktur Repositori

```text
GestureCam/
├── .gitignore               # Mengabaikan venv, cache, dan model binary (*.task)
├── LICENSE                  # MIT License
├── README.md                # Dokumentasi & panduan penggunaan
├── requirements.txt         # OpenCV, MediaPipe, NumPy
├── requirements-dev.txt     # Pytest
├── assets/
│   └── (hand_landmarker.task diunduh saat setup)
├── gesturecam/
│   ├── __init__.py
│   ├── __main__.py          # Entrypoint, loop OpenCV, dan event handler
│   ├── camera.py            # Wrapper VideoCapture dengan fault-tolerance
│   ├── config.py            # Konfigurasi frame, model path, & parameter threshold
│   ├── effects.py           # Gaussian blur & overlay visualizer
│   ├── geometry.py          # Kalkulasi vektor, sudut fleksi, & normalisasi
│   ├── gestures.py          # Klasifikasi Peace sign & debounce stabilizer
│   └── hand_tracking.py     # Wrapper MediaPipe Tasks Vision
└── tests/
    ├── test_effects.py      # Tes blur, OSD, dan toleransi hardware kamera
    ├── test_geometry.py     # Tes fungsi trigonometri & normalisasi koordinat
    └── test_gestures.py     # Tes klasifikasi peace, rejection, & stabilizer
```

---

## Setup & Instalasi

Pastikan Anda menggunakan **Python 3.12.x**.

### 1. Buat dan Aktifkan Virtual Environment

```powershell
# Buat virtual environment
py -3.12 -m venv .venv

# Aktifkan di PowerShell
.\.venv\Scripts\Activate.ps1
```

> **Catatan (PowerShell):** Jika muncul pesan error *running scripts is disabled on this system*, izinkan eksekusi script untuk sesi terminal saat ini:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

### 2. Install Dependency & Unduh Model

Setelah virtual environment aktif (tanda `(.venv)` muncul di terminal):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

# Download model MediaPipe Hand Landmarker ke folder assets
New-Item -ItemType Directory -Force assets | Out-Null
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" `
  -OutFile "assets\hand_landmarker.task"
```

### 3. Menjalankan Aplikasi

```powershell
python -m gesturecam --camera 0
```

*Ganti `0` dengan `1`, `2`, dan seterusnya jika Anda menggunakan kamera eksternal.*

---

## Cara Penggunaan

1. **Aktifkan Blur:** Angkat satu atau kedua tangan ke arah kamera dan tunjukkan gestur **Peace / V** (jari telunjuk dan jari tengah lurus terangkat, jari manis dan kelingking terlipat ke telapak). Posisi ibu jari bebas.
2. **Tahan Gestur:** Tahan posisi tangan selama minimal 3 frame pemrosesan sampai teks status menampilkan `Blur: ACTIVE`.
3. **Nonaktifkan Blur:** Turunkan tangan atau ubah gestur jari Anda untuk seketika mematikan blur.
4. **Keluar:** Tekan tombol `Esc` atau `Q` pada keyboard untuk menutup aplikasi dan melepas webcam secara bersih.

---

## Pengujian & Verifikasi

Seluruh pengujian unit berjalan secara otomatis tanpa membutuhkan webcam fisik:

```powershell
# Menjalankan test suite
python -m pytest -v

# Memeriksa kompilasi bytecode
python -m compileall gesturecam tests
```

---

## Troubleshooting

- **Gestur Peace tidak terbaca:** Pastikan jari telunjuk dan tengah benar-benar tegak dan terbuka membentuk huruf V, serta jari manis dan kelingking terlipat jelas.
- **Pencahayaan:** Hindari backlight yang terlalu silau di belakang Anda atau tangan terlalu dekat hingga keluar dari frame kamera.
- **Kamera tidak terbuka:** Pastikan tidak ada aplikasi lain (Zoom, Teams, Google Meet, OBS) yang sedang mengunci webcam, atau coba parameter index kamera lain: `python -m gesturecam --camera 1`.

---

## Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).
