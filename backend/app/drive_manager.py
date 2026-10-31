from app.drive_auth import connect_drive


def create_project_folder(project_name):

    drive = connect_drive()

    # Membuat folder utama
    folder_metadata = {
        "name": project_name,
        "mimeType": "application/vnd.google-apps.folder"
    }

    folder = drive.files().create(
        body=folder_metadata,
        fields="id, name"
    ).execute()

    folder_id = folder["id"]

    # Membuat subfolder
    subfolders = [
        "datasets",
        "notebooks",
        "training_results",
        "models"
    ]

    for name in subfolders:
        drive.files().create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [folder_id]
            },
            fields="id"
        ).execute()

    print(f"Folder proyek berhasil dibuat: {project_name}")

    return folder_id