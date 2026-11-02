# Validasi perubahan

Dijalankan pada cloud Linux, Python 3.12.14, Node 24.19.0/npm 11.9.0. Tidak ada akses Google Drive/Colab nyata, alokasi GPU, training, inferensi model berat, atau pembacaan file autentikasi pribadi. Data tes seluruhnya berada di direktori sementara. Tidak ada reset data laptop pengguna.

## Hasil

| Pemeriksaan | Hasil |
| --- | --- |
| `python -m unittest discover -s tests -v` | 32 tes offline lulus |
| `npm --prefix frontend run build` | Lulus, frontend produksi dibangun |
| `npm --prefix frontend run lint` | Exit 0; 18 warning kode React yang masih perlu perbaikan terpisah |
| `python3 tests/smoke_install.py` | Instalasi nyata dua kali, production HTTP/asset, pengunci pembaruan, shutdown SIGTERM, proses lain dipertahankan, uninstall dengan data/konfigurasi tetap ada |
| `python3 tests/browser_smoke.py` | Chromium desktop 1440×1000 dan mobile 390×844 lulus; API mock |
| `python -m compileall -q backend/app training tools tests chanthecno-hub` | Lulus |
| Pemeriksaan whitespace Git | Lulus |

Tes backend mencakup startup/database baru, isolasi/persistensi dataset, duplikasi, UTF-8/NUL/path/batas ukuran, URL tanpa fetch, host/origin lokal, model lama setelah pekerjaan baru gagal, training selesai dengan backup gagal, pemulihan yang tidak melatih ulang, retry upload, ukuran/checksum cadangan, heartbeat kedaluwarsa, pencegahan worker ganda/pergantian proyek, kernel yang masih sibuk, penolakan OAuth, akses Colab read-only, state checkpoint lengkap, retrieval, fallback pengetahuan umum memakai model yang sama (mock), reset/restore SQLite termasuk WAL, kegagalan snapshot, korupsi cadangan dan symlink/path traversal/ukuran arsip.

Uji browser memeriksa nama model dinamis, pengiriman chat, salin jawaban, percakapan baru, panel model yang dapat dilipat, pergantian proyek ketika jawaban lama masih tertunda, tidak ada overflow horizontal, serta judul dan kolom pesan yang tetap terlihat pada mobile. Respons chat dan status model di screenshot adalah **fixture pengujian**, bukan hasil GPU atau akses Drive nyata.

- [Desktop](screenshots/model-testing-desktop.png)
- [Mobile](screenshots/model-testing-mobile.png)

Untuk mengulang browser smoke, gunakan Python dengan Playwright (divalidasi 1.62.0) dan Chromium lokal di `/usr/bin/chromium`. Suite backend hanya membutuhkan `requirements-dev.txt`; smoke installer membutuhkan akses registry paket dan port lokal 8000 kosong. Browser smoke memakai port 8765. Tidak ada dependensi Playwright dalam runtime aplikasi.

Starlette saat ini menampilkan peringatan deprecation kompatibilitas TestClient/httpx; seluruh tes tetap berjalan dan lulus. CI yang ditambahkan menjalankan suite offline, build dan lint; eksekusi CI pada GitHub belum diverifikasi di cloud ini.

## Batas bukti

Belum diverifikasi pada Linux Mint/RAM 4 GB secara langsung. OAuth desktop/browser sistem, izin Google, Colab API, sesi/T4, kualitas adapter, training/resume penuh, cadangan Drive nyata, dan inferensi GPU tetap memerlukan pengujian pengguna dengan akun sendiri. Tes mock tidak membuktikan integrasi itu. Launcher produksi dan HTTP lokal sudah diuji dengan dependensi nyata.

Resume web dan konversi/unduhan GGUF penuh belum ditambahkan. Resume CLI memerlukan checkpoint baru dengan checksum state lengkap serta kecocokan kode/data/config; checkpoint lama tidak otomatis dianggap dapat melanjutkan persis. Percakapan terisolasi di UI, tetapi model masih memproses setiap pertanyaan secara mandiri.
