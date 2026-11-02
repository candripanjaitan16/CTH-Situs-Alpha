#!/usr/bin/env python3
"""Build a tracked Git checkout into an isolated, per-user release."""
import argparse
import fcntl
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
from uuid import uuid4

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / 'backend'))
from app.paths import STATE_HOME, prepare
from app.storage import authentication_name


def run(*command, cwd=None, env=None):
    subprocess.run(command, cwd=cwd, env=env, check=True)


def install_home():
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')).expanduser().resolve() / 'chanthecno-hub/program'


def tracked_sources():
    result = subprocess.check_output(['git', 'ls-files', '-z'], cwd=SOURCE)
    names = []
    for raw in result.split(b'\0'):
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = PurePosixPath(name)
        if path.parts[0] not in {'backend', 'frontend', 'training', 'tools', 'chanthecno-hub', 'requirements-training.txt'}:
            continue
        if authentication_name(path.name) or path.suffix.lower() in {'.db', '.sqlite'}:
            raise RuntimeError(f'Berkas sensitif terlacak Git: {name}. Instalasi dibatalkan.')
        actual = SOURCE / name
        if actual.is_symlink() or not actual.is_file() or actual.resolve() != actual:
            raise RuntimeError(f'Berkas sumber tidak aman: {name}')
        names.append(name)
    if not names:
        raise RuntimeError('Jalankan installer dari checkout GitHub yang valid.')
    return names


def main():
    parser = argparse.ArgumentParser(description='Install CTH untuk pengguna saat ini, tanpa sudo')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        raise RuntimeError('Jalankan sebagai pengguna biasa, tanpa sudo.')
    root = install_home()
    prepare()
    bindir = Path(os.environ.get('CTH_BIN_DIR', Path.home() / '.local/bin')).expanduser()
    if not bindir.is_absolute():
        raise RuntimeError('CTH_BIN_DIR harus path absolut.')
    binary = bindir / 'chanthecno-hub'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / 'install.lock').open('a') as lock, (STATE_HOME / 'application.lock').open('a') as application, (STATE_HOME / 'api.lock').open('a') as api:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            fcntl.flock(application, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(api, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Tutup CTH dan pemeliharaan lokal sebelum instalasi atau uninstall.') from None
        if args.uninstall:
            if binary.is_symlink() and binary.readlink() == root / 'current/chanthecno-hub':
                binary.unlink()
            for item in ('current', 'releases'):
                target = root / item
                if target.is_symlink():
                    target.unlink()
                elif target.is_dir():
                    shutil.rmtree(target)
            print('Program dihapus. Data, konfigurasi, token, dan cadangan pengguna dipertahankan.')
            return
        if sys.version_info < (3, 12):
            raise RuntimeError('Python 3.12+ dengan modul venv diperlukan.')
        for tool in ('git', 'node', 'npm'):
            if not shutil.which(tool):
                raise RuntimeError(f'{tool} belum tersedia. Lihat README untuk prasyarat.')
        node = subprocess.check_output(['node', '-p', 'process.versions.node'], text=True).strip()
        major, minor = map(int, node.split('.')[:2])
        if major < 22 or (major == 22 and minor < 12):
            raise RuntimeError('Gunakan Node.js 22.12+ atau 24 LTS.')
        if binary.exists() or binary.is_symlink():
            if not binary.is_symlink() or binary.readlink() != root / 'current/chanthecno-hub':
                raise RuntimeError(f'{binary} sudah ada dan bukan milik installer ini.')
        names = tracked_sources()
        releases = root / 'releases'
        releases.mkdir(exist_ok=True)
        release = releases / uuid4().hex
        release.mkdir(mode=0o700)
        switched = False
        try:
            for name in names:
                target = release / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE / name, target)
            run(sys.executable, '-m', 'venv', str(release / 'backend/.venv'))
            python = release / 'backend/.venv/bin/python'
            run(str(python), '-m', 'pip', 'install', '-r', str(release / 'backend/requirements.txt'))
            run(str(python), '-m', 'pip', 'check')
            run('npm', 'ci', '--no-audit', '--no-fund', cwd=release / 'frontend')
            environment = os.environ.copy()
            environment['VITE_API_BASE_URL'] = ''
            run('npm', 'run', 'build', cwd=release / 'frontend', env=environment)
            if not (release / 'frontend/dist/index.html').is_file():
                raise RuntimeError('Build frontend tidak menghasilkan index.html.')
            shutil.rmtree(release / 'frontend/node_modules')
            (release / 'chanthecno-hub').chmod(0o755)
            binary.parent.mkdir(parents=True, exist_ok=True)
            temporary = root / ('current-' + uuid4().hex)
            temporary.symlink_to(release, target_is_directory=True)
            os.replace(temporary, root / 'current')
            switched = True
            if not binary.is_symlink():
                binary.symlink_to(root / 'current/chanthecno-hub')
        finally:
            if not switched:
                shutil.rmtree(release)
        print('Instalasi selesai. Jalankan: chanthecno-hub')
        print('Rilis sebelumnya dipertahankan; pembaruan tidak menyentuh data pengguna.')
        if str(binary.parent) not in os.environ.get('PATH', '').split(os.pathsep):
            print('Tambahkan ~/.local/bin ke PATH di ~/.profile, lalu buka terminal baru:')
            print('export PATH="$HOME/.local/bin:$PATH"')
            if bindir != Path.home() / '.local/bin':
                print(f'Direktori bin kustom yang harus masuk PATH: {bindir}')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f'Instalasi gagal: {error}', file=sys.stderr)
        raise SystemExit(1)
