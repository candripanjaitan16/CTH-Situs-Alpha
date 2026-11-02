import hashlib
import re
from pathlib import Path
from uuid import uuid4

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.database import get_db
from app.drive_auth import SCOPES, TOKEN_FILE, save_credentials


def storage_connection():
    if not TOKEN_FILE.exists():
        raise RuntimeError('Hubungkan Google Drive terlebih dahulu.')
    credentials = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_credentials(credentials)
    if not credentials.valid:
        raise RuntimeError('Otorisasi Google Drive perlu diperbarui.')
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)


def project_folder_id(project_id):
    conn = get_db()
    try:
        row = conn.execute('SELECT drive_folder_id FROM projects WHERE id=?', (project_id,)).fetchone()
    finally:
        conn.close()
    if not row or not re.fullmatch(r'[A-Za-z0-9_-]+', row['drive_folder_id'] or ''):
        raise RuntimeError('Folder Drive proyek belum valid.')
    return row['drive_folder_id']


def require_writable_folder(drive, folder_id):
    folder = drive.files().get(fileId=folder_id, fields='mimeType,trashed,capabilities(canAddChildren)').execute()
    if folder.get('trashed') or folder.get('mimeType') != 'application/vnd.google-apps.folder' or not folder.get('capabilities', {}).get('canAddChildren'):
        raise RuntimeError('Folder tidak tersedia atau tidak dapat ditulis.')


def find_subfolder(drive, parent_id, folder_name):
    if folder_name not in {'datasets', 'notebooks', 'training_results', 'models'}:
        raise ValueError('Kategori tidak diizinkan.')
    require_writable_folder(drive, parent_id)
    matches = []
    token = None
    while True:
        response = drive.files().list(q=f"'{parent_id}' in parents and trashed=false and name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                                      fields='nextPageToken,files(id)', pageSize=100, pageToken=token).execute()
        matches.extend(response.get('files', []))
        token = response.get('nextPageToken')
        if not token:
            break
    if len(matches) != 1:
        raise RuntimeError('Subfolder tidak ditemukan atau ada duplikat. Periksa folder proyek.')
    folder_id = matches[0]['id']
    require_writable_folder(drive, folder_id)
    return folder_id


def file_checksums(path):
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    size = 0
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            md5.update(chunk)
            sha256.update(chunk)
            size += len(chunk)
    return size, md5.hexdigest(), sha256.hexdigest()


def upload_project_file(project_id, local_path, category):
    path = Path(local_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Berkas upload tidak valid.')
    before = file_checksums(path)
    if not before[0]:
        raise ValueError('Berkas kosong.')
    drive = storage_connection()
    folder = find_subfolder(drive, project_folder_id(project_id), category)
    name = uuid4().hex[:12] + '-' + path.name
    media = MediaFileUpload(str(path), resumable=True, chunksize=8 * 1024 * 1024)
    try:
        request = drive.files().create(body={'name': name, 'parents': [folder],
             'appProperties': {'cth_sha256': before[2], 'cth_project_id': str(project_id)}},
             media_body=media, fields='id')
        response = None
        while response is None:
            _, response = request.next_chunk(num_retries=2)
    finally:
        media.stream().close()
    remote = drive.files().get(fileId=response['id'], fields='id,name,size,md5Checksum,parents,trashed').execute()
    if file_checksums(path) != before or remote.get('trashed') or int(remote.get('size', -1)) != before[0] or remote.get('md5Checksum') != before[1] or folder not in remote.get('parents', []):
        raise RuntimeError('Upload belum terverifikasi. Berkas sumber tetap dipertahankan.')
    return {'status': 'saved', 'verified': True, 'project_id': project_id, 'category': category,
            'file_id': remote['id'], 'name': remote['name'], 'size': before[0], 'sha256': before[2]}
