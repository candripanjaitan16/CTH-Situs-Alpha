import json
import re


# Kode tetap milik backend; frontend tidak boleh mengirim kode atau path.
SNAPSHOT_CODE = r'''
import fcntl
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import time
from pathlib import Path

project_id = __PROJECT_ID__
backup_id = __BACKUP_ID__
drive_sources = json.loads(__DRIVE_SOURCES__)
root = Path("/content/cth/projects") / str(project_id)
transfer = Path("/content/cth-transfer") / backup_id

def emit(data):
    print("CTH_CONTROL:" + json.dumps(data))

def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def inventory():
    if not root.exists():
        return []
    if root.is_symlink() or root.resolve() != root:
        raise RuntimeError("Folder proyek adalah symlink atau lokasinya berubah.")
    items = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("Ada symlink dalam workspace. Cadangan dibatalkan.")
        if path.is_dir():
            continue
        if not path.is_file() or path.stat().st_nlink > 1:
            raise RuntimeError("Ada berkas khusus atau hardlink dalam workspace.")
        relative = str(path.relative_to(root))
        if relative == ".cth-worker.lock":
            continue
        if path.name == "credentials.json" or path.name in {"token.json", "token_colab.json"}:
            raise RuntimeError("Credentials ditemukan dalam workspace. Pindahkan dari folder dataset/model.")
        before = path.stat()
        sha256 = digest_file(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("Berkas berubah saat dibaca. Cadangan dibatalkan.")
        items.append({"path": relative, "size": after.st_size, "mtime_ns": after.st_mtime_ns, "sha256": sha256})
    return items

def require_no_gpu_work():
    query = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True, timeout=20)
    if query.stdout.strip():
        raise RuntimeError("Masih ada proses komputasi GPU. Tunggu worker selesai dan menyimpan checkpoint.")

def managed_runs():
    directory = root / "training_results"
    if not directory.exists():
        return []
    if directory.is_symlink():
        raise RuntimeError("Folder training_results tidak aman.")
    runs = []
    for status_file in sorted(directory.glob("*/status.json")):
        if status_file.is_symlink() or status_file.parent.is_symlink():
            raise RuntimeError("Status training berupa symlink.")
        data = json.loads(status_file.read_text())
        runs.append((status_file, data))
    return runs

try:
    if root.resolve() != root or transfer.parent.resolve() != transfer.parent:
        raise RuntimeError("Lokasi workspace atau transfer berupa symlink.")
    if (root / ".cth-worker.lock").is_symlink():
        raise RuntimeError("Lock proyek berupa symlink.")
    # Worker web bisa masih memasang dependensi sebelum run model dibuat.
    web_jobs = list((root / "jobs").glob("*/job.json"))
    for job_file in web_jobs:
        if json.loads(job_file.read_text()).get("status") not in {"completed", "failed", "stopped"}:
            (job_file.parent / "stop.request").touch(exist_ok=True)
    web_deadline = time.monotonic() + 120
    while any(json.loads(p.read_text()).get("status") not in {"completed", "failed", "stopped"} for p in web_jobs):
        if time.monotonic() >= web_deadline:
            raise RuntimeError("Worker web belum selesai menyimpan. Runtime tetap menyala; periksa ulang nanti.")
        time.sleep(2)
    # Meminta stop kooperatif, bukan membunuh proses model.
    active = [(path, data) for path, data in managed_runs() if data.get("status") in {"preparing", "training", "stopping"}]
    for path, _ in active:
        (path.parent / "stop.request").touch(exist_ok=True)
    deadline = time.monotonic() + 120
    while active:
        if time.monotonic() >= deadline:
            raise RuntimeError("Worker belum mengonfirmasi stop dan checkpoint. Runtime tetap menyala.")
        time.sleep(2)
        active = [(path, data) for path, data in managed_runs() if data.get("status") in {"preparing", "training", "stopping"}]

    require_no_gpu_work()
    # Cegah menghapus data proyek lain atau berkas tak terkelola.
    projects_dir = root.parent
    if projects_dir.exists():
        for other in projects_dir.iterdir():
            if other.name != str(project_id) and (other.is_symlink() or (other.is_dir() and any(other.iterdir())) or other.is_file()):
                raise RuntimeError("Ada workspace proyek lain pada runtime. Stop dibatalkan agar datanya tidak hilang.")
    allowed_content = {"sample_data", ".config", "drive", "cth", "cth-transfer"}
    if any(path.name not in allowed_content for path in Path("/content").iterdir()):
        raise RuntimeError("Ada berkas lain di /content di luar workspace CTH. Stop dibatalkan; pindahkan/simpan berkas tersebut dahulu.")
    cth_dir = Path("/content/cth")
    if cth_dir.exists() and any(path.name != "projects" for path in cth_dir.iterdir()):
        raise RuntimeError("Ada berkas CTH di luar folder projects. Stop dibatalkan agar tidak ada data terlewat.")

    existed = root.exists()
    root.mkdir(parents=True, exist_ok=True)
    cth_snapshot_lock = (root / ".cth-worker.lock").open("a")
    try:
        fcntl.flock(cth_snapshot_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        cth_snapshot_lock.close()
        raise RuntimeError("Worker masih mengunci proyek; runtime tidak dihentikan.")
    cth_inventory = inventory()
    runs = managed_runs()
    for path, data in runs:
        if data.get("status") == "stopped" and not list((path.parent / "checkpoints").glob("checkpoint-*/cth-complete.json")):
            raise RuntimeError("Worker mengaku stopped tetapi checkpoint lengkap belum ditemukan.")
    total = sum(item["size"] for item in cth_inventory)
    if shutil.disk_usage("/content").free < total + len(cth_inventory) * 4096 + 128 * 1024 * 1024:
        raise RuntimeError("Disk runtime tidak cukup untuk membuat cadangan. Runtime tidak dimatikan.")
    transfer.mkdir(parents=True, exist_ok=False)
    archive = transfer / "workspace.tar"
    manifest = {"project_id": project_id, "scope": str(root), "workspace_existed": existed,
        "files": cth_inventory, "file_count": len(cth_inventory), "drive_sources": drive_sources,
        "checkpoint_count": sum(item["path"].endswith("/cth-complete.json") for item in cth_inventory),
        "notice": "Cadangan berkas di disk; tidak menyimpan variabel/RAM, cache HF, sample_data, atau sumber web yang belum dikirim."}
    with tarfile.open(archive, "w") as tar:
        payload = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
        member = tarfile.TarInfo("CTH-SNAPSHOT.json")
        member.size = len(payload)
        member.mode = 0o600
        tar.addfile(member, io.BytesIO(payload))
        for item in cth_inventory:
            path = root / item["path"]
            member = tar.gettarinfo(str(path), arcname="workspace/" + item["path"])
            if not member.isfile():
                raise RuntimeError("Jenis berkas berubah saat diarsipkan.")
            member.uid = member.gid = 0
            member.uname = member.gname = ""
            with path.open("rb") as handle:
                tar.addfile(member, handle)
    if inventory() != cth_inventory:
        raise RuntimeError("Workspace berubah saat dibuat cadangan. Runtime tidak dihentikan.")
    emit({"ok": True, "backup_id": backup_id, "size": archive.stat().st_size,
        "sha256": digest_file(archive), "file_count": len(cth_inventory),
        "checkpoint_count": manifest["checkpoint_count"], "workspace_existed": existed})
except Exception as error:
    emit({"ok": False, "message": str(error) if isinstance(error, RuntimeError) else "Persiapan cadangan gagal; runtime tetap menyala."})
'''

FINAL_CHECK_CODE = r'''
try:
    require_no_gpu_work()
    if inventory() != cth_inventory:
        raise RuntimeError("Workspace berubah setelah upload. Stop dibatalkan.")
    emit({"ok": True})
except Exception as error:
    emit({"ok": False, "message": str(error) if isinstance(error, RuntimeError) else "Pemeriksaan akhir gagal."})
'''


def snapshot_code(project_id, backup_id, drive_sources=None):
    if not isinstance(project_id, int) or isinstance(project_id, bool) or project_id <= 0:
        raise ValueError("ID proyek tidak valid.")
    if not re.fullmatch(r"[a-f0-9]{32}", backup_id):
        raise ValueError("ID cadangan tidak valid.")
    return SNAPSHOT_CODE.replace("__PROJECT_ID__", str(project_id)).replace("__BACKUP_ID__", json.dumps(backup_id)).replace("__DRIVE_SOURCES__", repr(json.dumps(drive_sources or [], ensure_ascii=True)))
