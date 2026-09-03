# GestureCam — Open Palm Blur

GestureCam menampilkan feed webcam yang telah dicerminkan, melacak hingga dua tangan, dan memburamkan seluruh feed ketika gesture peace/V (`PEACE`) terdeteksi stabil pada salah satu tangan. Overlay dan landmark tetap tajam agar status deteksi mudah dilihat.

Runtime sekarang sengaja difokuskan pada satu interaksi:

```text
peace/V pada salah satu tangan -> debounce 3 observasi -> blur seluruh feed
gesture berubah/tangan hilang -> blur mati
```

Face tracking, trigger meme, Cube, pinch selection, dan mode keyboard tidak dijalankan.

## Setup

Gunakan CPython 3.12.x dan virtual environment project. Jangan memasang dependency secara global atau mencampur distribusi OpenCV lain dengan `opencv-contrib-python`.

### 1. Buat dan Aktifkan Virtual Environment

```powershell
# Buat virtual environment
py -3.12 -m venv .venv

# Aktifkan di PowerShell
.\.venv\Scripts\Activate.ps1
```

> **Catatan (PowerShell):** Jika muncul error *running scripts is disabled on this system*, izinkan eksekusi script untuk sesi terminal saat ini:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

### 2. Install Dependency & Download Model

Setelah virtual environment aktif (terdapat tanda `(.venv)` di terminal):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

# Download model MediaPipe Hand Landmarker
New-Item -ItemType Directory -Force assets | Out-Null
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" `
  -OutFile "assets\hand_landmarker.task"
```

### 3. Menjalankan Aplikasi

```powershell
python -m gesturecam --camera 0
```

Ganti `0` dengan `1`, `2`, dan seterusnya untuk memilih input kamera lain. Index aktif ditampilkan pada overlay.

## Penggunaan

- Tunjukkan gesture peace/V: telunjuk dan jari tengah terbuka, jari manis dan kelingking terlipat. Ibu jari boleh berada pada posisi apa pun.
- Satu atau dua tangan dapat muncul bersamaan; peace pada salah satu tangan sudah mengaktifkan blur.
- Tahan selama minimal tiga frame pemrosesan sampai `Gestures: PEACE` dan `Blur: ACTIVE` tampil.
- Turunkan tangan atau ubah gesture untuk mematikan blur.
- Tekan `Esc` atau `Q` untuk keluar dan melepas webcam.

Overlay menampilkan camera index, gesture stabil tiap tangan, jumlah tangan `0/2` sampai `2/2`, status blur, FPS, dan tombol keluar.

## Verifikasi

```powershell
python -m pytest -q
python -m compileall gesturecam tests
```

Tes otomatis tidak membutuhkan webcam, window, network, atau manusia.

## Troubleshooting Peace

- Pastikan telunjuk dan jari tengah terlihat lurus serta terpisah membentuk V.
- Lipat jari manis dan kelingking dengan jelas; posisi ibu jari tidak dinilai.
- Hindari tangan terlalu dekat, motion blur, cahaya belakang, atau latar yang menyatu dengan warna kulit.
- Tunggu sampai overlay menunjukkan `Hand: DETECTED` sebelum mengevaluasi gesture.
- Gesture harus stabil selama tiga observasi; satu frame tidak langsung mengaktifkan blur.
- Bila kamera gagal, tutup aplikasi lain yang memakainya dan coba `--camera 1` atau index lain.

Peace memakai geometry yang sama dengan classifier lain: index dan middle harus `EXTENDED`, ring dan pinky harus `FOLDED`, serta pinch harus tidak aktif. Blur penuh memakai kernel Gaussian 81×81 agar detail wajah dan latar jauh lebih tersamarkan pada feed 720p.
