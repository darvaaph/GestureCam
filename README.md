# GestureCam

GestureCam adalah prototipe desktop lokal untuk Windows yang melacak satu tangan dari webcam. Aplikasi mengenali `OPEN_PALM`, `FIST`, `POINTING`, dan `PINCH`, lalu memakai pinch-drag-release untuk membuat area blur atau wireframe kubus pseudo-3D. Semua inferensi dan rendering berjalan lokal.

## Persyaratan

- Windows 10/11 64-bit.
- CPython 3.12.x. Versi major/minor lain ditolak saat startup.
- Webcam yang diizinkan untuk desktop applications pada Windows Privacy settings.
- Internet hanya untuk instalasi awal dan pengunduhan model.

Jangan menghapus instalasi Python lain, memasang dependency project secara global, atau mencampur `opencv-python`/`opencv-python-headless` dengan `opencv-contrib-python`. Semua distribusi itu menyediakan namespace `cv2` yang sama dan dapat berkonflik.

## Setup PowerShell

Jalankan dari root repository:

```powershell
py --list
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
New-Item -ItemType Directory -Force assets | Out-Null
Invoke-WebRequest `
  -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" `
  -OutFile "assets\hand_landmarker.task"
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe -m gesturecam
```

Kamera default memakai index `0`. Untuk memilih kamera lain, berikan index OpenCV saat startup:

```powershell
& .\.venv\Scripts\python.exe -m gesturecam --camera 1
```

Coba `0`, `1`, `2`, dan seterusnya sampai nama/index perangkat yang diinginkan berhasil terbuka. Index aktif ditampilkan pada overlay sebagai `Camera: N`.

Aktivasi virtual environment bersifat opsional:

```powershell
.\.venv\Scripts\Activate.ps1
python --version
python -m gesturecam
```

`python --version` harus menampilkan Python 3.12.x. Model berasal dari [official MediaPipe Hand Landmarker bundle](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task) dan tidak diunduh diam-diam saat aplikasi berjalan.

## Kontrol

| Input | Perilaku |
|---|---|
| `B` | Pilih Blur saat state `READY`. |
| `C` | Pilih Cube saat state `READY`. |
| Pinch + drag + release | Membuat atau mengganti effect mode aktif. |
| Pinch di dalam muka depan cube | Mengambil dan memindahkan cube tanpa snapping. |
| Open Palm (5 jari) | Memburamkan seluruh feed selama gesture terdeteksi stabil. Overlay tetap terlihat. |
| Fist | Membatalkan interaksi aktif; saat idle menghapus effect mode aktif sekali per fist entry. |
| `Esc` | Membatalkan interaksi aktif; saat idle keluar. |
| `Q` | Keluar dari state apa pun dan melepas webcam. |

Feed dibalik horizontal sebelum inferensi, sehingga frame yang ditampilkan, landmark, cursor, dan koordinat interaction memakai sistem koordinat mirrored yang sama. Perhitungan pixel selalu memakai ukuran frame aktual, bukan asumsi 1280×720.

## Batas MVP

Aplikasi memproses paling banyak satu tangan dan menyimpan paling banyak satu blur region serta satu cube. Cube adalah dua rectangle OpenCV dengan perspective offset tetap, bukan objek 3D. Effect tidak disimpan setelah process selesai. Tidak ada recording, network runtime, database, custom gesture model, atau GUI selain satu window OpenCV.

## Verifikasi

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m compileall gesturecam tests
```

Tes otomatis tidak membutuhkan webcam, window, network, atau manusia. Implementasi diverifikasi dengan Python 3.12.10: 72 tes lulus; model membuka, memproses frame RGB sintetis, dan menutup; environment hanya berisi `opencv-contrib-python` sebagai distribusi OpenCV. Hasil hardware yang benar-benar dijalankan dicatat di [MANUAL_TESTS.md](MANUAL_TESTS.md).

## Troubleshooting

- **Wrong Python version:** buat ulang environment dengan `py -3.12 -m venv .venv`, lalu gunakan interpreter `.venv` secara eksplisit.
- **Model missing/empty:** jalankan kembali blok `Invoke-WebRequest` di atas dan pastikan `assets\hand_landmarker.task` tidak kosong.
- **Camera cannot be opened:** tes kamera di Windows Camera, aktifkan camera access untuk desktop apps, tutup aplikasi lain yang memakai webcam, lalu coba index lain seperti `--camera 1`.
- **30 consecutive frame failures:** reconnect webcam atau tutup process yang memegang kamera, lalu jalankan ulang. Satu frame gagal tetap ditoleransi.
- **MediaPipe initialization failure:** unduh ulang model, hapus virtual environment yang rusak, lalu ulangi setup dengan pin yang tersedia di repository.
- **`cv2` conflict:** periksa `& .\.venv\Scripts\python.exe -m pip list | Select-String opencv`; hanya `opencv-contrib-python` yang boleh terpasang.
- **PowerShell memblokir activation:** activation tidak wajib; gunakan `& .\.venv\Scripts\python.exe ...` seperti pada perintah setup.

## Dependency dan calibration notes

Direct dependency pins tetap persis seperti PRD: MediaPipe 0.10.35, OpenCV contrib 4.12.0.88, NumPy 2.2.6, dan pytest 9.1.1 untuk development. Smoke test tidak menemukan incompatibility sehingga tidak ada pin yang diubah.

Semua gesture threshold tetap pada nilai PRD. Perbandingan pinch di boundary memakai toleransi floating-point `1e-9` agar nilai hasil pembagian yang secara matematis tepat 0.35/0.50 tidak bergeser akibat representasi biner; nilai threshold dan perilaku hysteresis tidak diubah.
