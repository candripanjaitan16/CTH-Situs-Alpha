# Chanthecno Training Hub

Dashboard lokal untuk dataset proyek, fine-tuning LoRA di Google Colab T4, cadangan Google Drive, pemulihan model, dan pengujian chat. Aplikasi memakai React/Vite, FastAPI, dan SQLite. Model dasar tetap `Qwen/Qwen2.5-0.5B-Instruct`; nama model proyek adalah nama adapter hasil fine-tuning, bukan model yang dilatih dari nol.

## Instalasi dari GitHub (Linux, tanpa sudo)

Prasyarat: Git, Python **3.12+** dengan modul `venv`/pip, dan Node.js **22.12+ atau 24 LTS** beserta npm. Validasi cloud memakai Python 3.12.14, Node 24.19.0, npm 11.9.0. Pada Linux Mint, pastikan paket Python menyediakan venv sebelum mulai. Installer tidak menjalankan sudo atau memasang paket sistem. Gunakan versi Node yang memenuhi batas Vite; Node bawaan Mint yang lebih tua mungkin perlu diperbarui oleh pengguna.

```bash
git clone https://github.com/candripanjaitan16/Chanthecno-Training-Hub.git
cd Chanthecno-Training-Hub
python3 tools/install.py
```

Installer menyalin sumber **yang terlacak Git**, membuat virtualenv backend pada rilis terpisah, memasang `backend/requirements.txt`, menjalankan `npm ci` dengan lockfile, membangun frontend produksi, lalu memasang perintah untuk pengguna saat ini. Perubahan sumber yang belum terlacak tidak ikut; pengembang perlu menambahkannya ke Git terlebih dahulu. Kegagalan pemasangan/build tidak mengganti rilis aktif. Sumber autentikasi tidak ikut disalin; jika nama berkas rahasia terlacak ditemukan, instalasi ditolak tanpa membaca isinya.

Distribusi aplikasi melalui GitHub. npm hanya dipakai untuk membangun frontend saat instalasi; **tidak ada paket npm/npx aplikasi ini yang diterbitkan atau perlu dipasang**. Runtime lokal tidak menjalankan Vite, Node, PyTorch, atau model besar. Beban model tetap di Colab; build frontend memerlukan memori sementara, sedangkan dashboard memakai satu proses server lokal. Kinerja pada laptop RAM 4 GB belum diukur langsung.

Jika `chanthecno-hub` belum ditemukan, tambahkan baris berikut ke `~/.profile`, kemudian buka terminal baru. Untuk terminal saat ini, jalankan baris yang sama:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Installer memberikan petunjuk ini bila direktori bin belum ada dalam PATH dan tidak mengubah file shell pengguna secara otomatis.

## Menjalankan dan keluar

```bash
chanthecno-hub
```

Launcher menjalankan backend dan menyajikan frontend produksi melalui **http://127.0.0.1:8000**, lalu membuka browser. Swagger tersedia pada `/docs`. Jika browser tidak tersedia, launcher menampilkan alamat untuk dibuka manual. `chanthecno-hub --no-browser` menonaktifkan pembukaan browser. Menutup tab browser tidak menghentikan server; tekan **Ctrl+C di terminal** untuk keluar. SIGTERM juga ditangani. Launcher hanya menghentikan grup proses yang dibuatnya sendiri, menolak port yang sudah terpakai, dan tidak menghentikan runtime Colab ketika keluar.

Server mengikat loopback, memeriksa host/origin dan akses lokal. Ini aplikasi satu pengguna lokal; jangan mengeksposnya melalui reverse proxy publik. Menghentikan server lokal tidak membuktikan pekerjaan Colab berhenti. Setelah koneksi terputus, periksa status sebelum memulai pekerjaan baru.

## Lokasi program, data, dan konfigurasi

| Isi | Lokasi default |
| --- | --- |
| Perintah | `~/.local/bin/chanthecno-hub` |
| Rilis dan virtualenv | `~/.local/share/chanthecno-hub/program/releases/` |
| Rilis aktif | `~/.local/share/chanthecno-hub/program/current` |
| SQLite, dataset, status, workspace, salinan model | `~/.local/share/chanthecno-hub/data/` |
| Konfigurasi OAuth dan token akun pengguna | `~/.config/chanthecno-hub/` |
| Pengunci proses dan cadangan reset lokal | `~/.local/state/chanthecno-hub/` |

Mengikuti `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, dan `XDG_STATE_HOME`. Untuk pengujian/konfigurasi khusus, `CTH_DATA_DIR`, `CTH_CONFIG_DIR`, `CTH_STATE_DIR` harus berupa path absolut dan konsisten pada setiap pemanggilan. `CTH_BIN_DIR` dapat mengganti direktori perintah untuk pengujian; default tetap `~/.local/bin`. Jangan menempatkan data di dalam source, direktori konfigurasi, atau direktori cadangan.

Database dan token versi lama di folder backend **tidak dibaca, dipindahkan, atau dihapus otomatis**. Instalasi baru dimulai dengan lokasi data per pengguna. Simpan checkout lama bila masih berisi data yang dibutuhkan; sambungkan ulang akun Google sendiri. Tidak ada token pengembang yang didistribusikan. Menghapus checkout unduhan setelah instalasi tidak menghapus data atau merusak rilis yang terpasang.

## Google OAuth: akun milik setiap pengguna

Buat konfigurasi OAuth **Desktop app** milik sendiri dengan akses Drive API dan izin Colab yang tersedia bagi akun tersebut. Letakkan file konfigurasi pengguna sendiri bernama `credentials.json` di `~/.config/chanthecno-hub/`. Jangan menaruhnya dalam checkout, frontend, `VITE_*`, dataset, atau lampiran publik. Direktori konfigurasi harus privat (0700); file konfigurasi/token sebaiknya 0600. File yang dibuat aplikasi ditulis secara atomik dengan izin privat.

```bash
chanthecno-hub connect-drive
chanthecno-hub connect-colab
```

Jalankan dari sesi desktop pengguna: OAuth membuka browser dan memakai callback loopback sementara. Drive menggunakan scope `https://www.googleapis.com/auth/drive.file`; Colab menggunakan `https://www.googleapis.com/auth/colaboratory`. Keduanya terpisah. Token disimpan hanya untuk pengguna tersebut setelah pemeriksaan akses terkait. Pemeriksaan Colab melakukan **GET daftar runtime**, bukan alokasi GPU/training. Respons ditolak/tidak valid tidak dinyatakan sebagai akses siap. Aplikasi API tidak memulai login interaktif otomatis ketika token belum tersedia.

Akses Colab API, kuota, sesi, dan GPU tetap bergantung pada akun serta layanan Google. Otentikasi berhasil bukan bukti GPU atau training berjalan. Untuk jaringan terbatas, konfigurasi akses ke OAuth Google, Drive API, Colab API, dan hostname runtime yang benar melalui pengaturan jaringan yang didukung; jangan menonaktifkan TLS atau mempublikasikan token. Jangan mengirim nilai token ke chat atau issue.

## Pembaruan dan uninstall

Tutup launcher sebelum pembaruan atau uninstall. Dari checkout GitHub yang sama:

```bash
git pull --ff-only
python3 tools/install.py
```

Rilis baru dipasang terpisah; virtualenv tidak dipindah setelah dibuat. Rilis aktif baru diganti setelah pemasangan/build sukses. Rilis lama dipertahankan. Installer tidak menghapus database, dataset, model lokal, konfigurasi, atau token, dan tidak menjalankan reset/migrasi data lama secara diam-diam. Perubahan lokal yang membuat `git pull --ff-only` gagal perlu diselesaikan sendiri tanpa force/reset.

```bash
chanthecno-hub uninstall
# Alternatif dari checkout:
python3 tools/install.py --uninstall
```

Uninstall menghapus rilis program dan tautan perintah milik installer, **mempertahankan seluruh data, konfigurasi/token, dan cadangan pengguna secara default**. Tidak ada operasi Google Drive/Colab. Tidak ada opsi penghapusan rahasia/data otomatis. Checkout GitHub yang diunduh juga dipertahankan.

## Dataset, status training, dan cadangan

- TXT UTF-8 disimpan bertahap ke disk backend dengan metadata SQLite, terisolasi per proyek; refresh/restart tidak menghilangkannya. Batas 64 MiB per TXT. Nama/path, NUL, teks kosong, dan duplikasi per proyek diperiksa.
- Status **salinan lokal** dan **cadangan Drive** berbeda. Kegagalan upload tidak menghapus salinan lokal. URL hanya dicatat; aplikasi tidak mengambil isi situs atau menjalankan fetch URL otomatis.
- Runtime dialokasikan, T4 terverifikasi, heartbeat worker, langkah optimizer, evaluasi/penyimpanan adapter, dan cadangan terverifikasi adalah bukti yang berbeda. `step == max_steps` belum berarti selesai.
- Heartbeat worker harus baru agar progres dianggap aktif. Progres lama atau putus koneksi memberi status perlu diperiksa, tidak memicu worker/training kedua. Worker versi lama tanpa heartbeat perlu diperiksa; jangan memulai ulang training aktif hanya untuk memperbarui worker.
- Pergantian proyek tidak mengambil alih runtime yang masih dipakai pekerjaan aktif/tidak pasti. Polling menjaga respons lama agar tidak menimpa pilihan baru. Kernel kontrol yang eksekusinya belum selesai tidak dihapus saat koneksi ditutup.
- Checkpoint ditulis berkala. Penanda lengkap ditulis setelah penyimpanan dan pemeriksaan state optimizer/scheduler/RNG serta adapter. Resume CLI memerlukan kecocokan konfigurasi/data/kode dan checksum; checkpoint lama tanpa checksum state tidak diklaim sebagai kelanjutan persis.
- Hentikan training meminta stop kooperatif setelah langkah optimizer dan penyimpanan checkpoint. **Stop & Simpan** berbeda: runtime hanya boleh dihentikan setelah cadangan dalam cakupan yang disetujui terverifikasi. Arsip workspace bukan otomatis model selesai atau GGUF.
- Cadangan adapter mencakup tokenizer dan metadata; hasil diperiksa dengan ukuran/checksum. Arsip lokal dipertahankan saat upload gagal. Retry cadangan tidak menjalankan training ulang. Ekstraksi membatasi entri, ukuran, path, symlink dan checksum.

## Memakai model tersimpan tanpa training ulang

1. Pilih proyek dan buka **Model Testing**.
2. Pilih hasil training yang selesai dari **Model tersimpan**. Pekerjaan baru yang gagal tidak menutupi hasil lama; training selesai dengan backup gagal tetap dapat diperiksa.
3. Hubungkan runtime proyek yang sesuai. Bila artefak model belum ada, klik **Pulihkan & jalankan** secara eksplisit. Pemulihan menyiapkan adapter/tokenizer/indeks dan lingkungan inferensi, bukan training baru. Artefak yang sudah cocok di runtime tidak diunggah ulang.
4. Periksa status, lalu kirim pertanyaan. Ganti runtime berarti artefak perlu diperiksa/pulihkan lagi.

Nama utama chat mengikuti `model_name`; identitas model dasar tetap ada dalam metadata. Mode generatif memakai adapter dan model dasar yang sama di Colab. Retrieval memilih passage sumber proyek; jika tidak relevan, jalur generatif tetap dapat memakai pengetahuan umum model tersebut. Keterangan dasar jawaban menyatakan sumber yang tersedia dan kemungkinan campuran pengetahuan umum, bukan jaminan atribusi faktual setiap kalimat. Mode **Kutipan sumber** hanya kutipan pencarian kata, bukan inferensi generatif.

Dataset diperlakukan sebagai data, bukan instruksi sistem. Penanda peran tidak boleh diteruskan sebagai lanjutan chat. Pertanyaan tidak otomatis menjadi data training. Percakapan UI dipisah berdasarkan proyek dan run; setiap pertanyaan saat ini diproses mandiri di model (belum ada memori dialog model lintas pertanyaan). Tombol Percakapan baru membersihkan tampilan. Tidak ada API AI eksternal.

TXT mentah merupakan adaptasi teks, bukan pasangan tanya jawab terawasi. Adapter dapat menghasilkan jawaban pendek/tidak akurat; jawaban terpotong ditolak dengan error, bukan diganti jawaban palsu. Perbaikan retrieval/chat template tidak membuktikan kualitas adapter. Bila diperlukan, evaluasi dataset dan contoh QA terstruktur terlebih dahulu; aplikasi tidak melatih ulang diam-diam. Kualitas model nyata belum diverifikasi pada tugas cloud ini.

## Reset lokal dan pemulihan cadangan

Reset bersifat **eksplisit**, tidak berjalan pada instalasi, startup, pembaruan, atau uninstall. Tutup server terlebih dahulu. Pekerjaan aktif, runtime masih dialokasikan, status tidak pasti, pengunci API, symlink, atau file autentikasi dalam direktori data membuat reset ditolak. Selesaikan/periksa status pekerjaan melalui aplikasi; jangan menghapus status secara manual untuk melewati pemeriksaan.

```bash
chanthecno-hub reset-local --confirm
```

Cakupan reset: database aplikasi, dataset lokal, status pekerjaan/runtime, cache dan workspace/model lokal dalam direktori data aplikasi. **Tidak mengubah konfigurasi OAuth/token, virtualenv, source, Google Drive, atau runtime Google.** Sebelum reset, aplikasi membuat cadangan terverifikasi di `~/.local/state/chanthecno-hub/backups/<id>/`. Snapshot SQLite memakai API backup agar transaksi WAL yang sudah commit tercakup. Kegagalan snapshot/checksum menghentikan reset; kegagalan inisialisasi schema mengembalikan data sebelumnya.

```bash
chanthecno-hub restore-local --backup "$HOME/.local/state/chanthecno-hub/backups/<id>" --confirm
```

Ganti `<id>` dengan lokasi yang dilaporkan reset. Restore memverifikasi manifest/checksum dan integritas SQLite, menolak symlink, lalu membuat cadangan keadaan saat ini sebelum mengganti data. Ini pemulihan data lokal, berbeda dari **Pulihkan model** di Colab. Cadangan mengandung dataset/model lokal dan perlu diperlakukan sebagai data privat.

Sesudah reset/restore, penanda generasi berubah. Saat UI dibuka ulang, hanya key browser berawalan `cth-` pada origin aplikasi yang dibersihkan; storage situs lain tidak disentuh. Jika masih membuka tab lama, muat ulang. Pilihan browser lama pada origin development berbeda dapat dibersihkan dari developer tools dengan menghapus hanya key `cth-`, bukan seluruh storage browser.

## Pengembangan dan pemeriksaan offline

Gunakan checkout yang ada. Instal dependensi pengujian tanpa mengubah lockfile:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
backend/.venv/bin/python -m unittest discover -s tests -v
npm --prefix frontend run lint
```

Untuk menguji launcher dari checkout setelah build: `python3 chanthecno-hub --no-browser`. Untuk development HMR, jalankan backend secara terpisah dari `backend/` dengan `./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`, kemudian `npm --prefix frontend run dev -- --host localhost`. CORS mengizinkan origin development 5173 dan produksi 8000. Jangan menjalankan launcher kedua pada port yang sama. Jangan memasang dependensi training pada mesin lokal hanya untuk dashboard.

Tes memakai direktori/database sementara dan mock Google, Colab, serta inferensi berat; tidak meminta GPU, training, atau membaca token pribadi. Lihat `docs/validation.md` untuk hasil yang benar-benar dijalankan. Build dan tes mock tidak membuktikan integrasi Google atau kualitas model nyata. UI ekspor GGUF dan deployment tetap belum menyediakan konversi/deployment penuh; skrip training/ekspor CLI memerlukan pengujian terpisah. Resume training masih melalui CLI worker, belum alur pemulihan otomatis dari web.

## Struktur

- `tools/install.py`: instalasi/pembaruan/uninstall GitHub untuk pengguna saat ini.
- `chanthecno-hub`: launcher produksi dan perintah pemeliharaan/OAuth eksplisit.
- `backend/app/paths.py`, `storage.py`, `maintenance.py`: lokasi data, penulisan atomik, reset/restore offline.
- `backend/app/`: API dan layanan dataset, Drive, Colab, training, cadangan, model library/pemulihan/chat.
- `training/`: worker T4, checkpoint, persiapan data, retrieval/inferensi dan ekspor.
- `frontend/src/`: dashboard ringan navy/biru/putih; pilihan model dapat dilipat pada layar kecil. Animasi hanya mengikuti heartbeat training yang terverifikasi, berhenti saat tab tersembunyi/reduced motion.
- `tests/`: validasi offline tanpa kredensial pengguna.

Proyek masih dalam pengembangan aktif. Lisensi proyek perlu ditetapkan melalui berkas LICENSE; model dasar dan dependensi mengikuti ketentuan masing-masing.
