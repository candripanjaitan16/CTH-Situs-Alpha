import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import AuthorizedSession
from requests.exceptions import RequestException

from app.colab import API_URL, T4_SPEC, read_api
from app.drive_auth import get_colab_credentials


BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "colab_runtime_state.json"

RUNTIME_ID = "cth-training-t4"
RUNTIME_NAME = f"runtimes/{RUNTIME_ID}"


def save_state(state):
    temporary_file = STATE_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )

    temporary_file.replace(STATE_FILE)


def start_t4():
    credentials = get_colab_credentials()

    with AuthorizedSession(credentials) as session:
        data = read_api(session, "runtimes")
        runtimes = data.get("runtimes", [])

        existing = next(
            (
                runtime
                for runtime in runtimes
                if runtime.get("name") == RUNTIME_NAME
            ),
            None,
        )

        if existing:
            if existing.get("runtimeSpec") != T4_SPEC:
                print(
                    "Runtime CTH sudah ada tetapi bukan T4 Standard. "
                    "Tidak ada perubahan yang dilakukan."
                )
                return

            print("Runtime T4 CTH sudah ada.")
            print("Nama:", existing["name"])
            print("Tidak membuat atau mengganti runtime.")
            print("GPU di dalam runtime belum diverifikasi.")
            return

        if runtimes:
            print("Ada runtime lain pada akun ini.")
            print("Pembuatan dihentikan agar tidak mengganggunya.")

            for runtime in runtimes:
                print("Runtime:", runtime.get("name"))

            return

        # Cegah pengiriman ulang setelah hasil tidak pasti
        if STATE_FILE.exists():
            print("Catatan permintaan sebelumnya sudah ada.")
            print("Tidak membuat runtime baru secara otomatis.")
            print("Kirim output ini untuk pemeriksaan berikutnya.")
            return

        specs = read_api(session, "runtimespecs")

        eligible = any(
            item.get("key") == T4_SPEC
            and item.get("eligible") is True
            for item in specs.get("runtimeSpecs", [])
        )

        if not eligible:
            print("T4 Standard saat ini tidak diizinkan.")
            print("Tidak beralih ke CPU.")
            return

        state = {
            "runtime_name": RUNTIME_NAME,
            "request_id": str(uuid4()),
            "status": "requesting",
        }

        save_state(state)

        print("Meminta runtime GPU T4 Standard...", flush=True)

        response = session.post(
            f"{API_URL}/runtimes",
            params={
                "runtimeId": RUNTIME_ID,
                "requestId": state["request_id"],
            },
            json={
                "runtimeSpec": T4_SPEC,
            },
            timeout=60,
        )

        print("HTTP:", response.status_code)

        if not response.ok:
            state["status"] = "request_failed"
            state["http_status"] = response.status_code
            save_state(state)

            print("Google belum menerima permintaan runtime.")
            print("Tidak beralih ke CPU atau menghapus runtime.")

            error = response.json().get("error", {})
            print("Status:", error.get("status", "Tidak diketahui"))
            print("Pesan:", error.get("message", "Permintaan gagal"))
            return

        operation = response.json()

        state["operation_name"] = operation.get("name")
        state["status"] = (
            "operation_finished"
            if operation.get("done")
            else "provisioning"
        )

        if operation.get("error"):
            state["status"] = "operation_failed"

        save_state(state)

        print("Operation:", state["operation_name"])
        print("Status:", state["status"])

        if operation.get("error"):
            error = operation["error"]
            print("Kode:", error.get("code"))
            print("Pesan:", error.get("message"))
        else:
            print("Permintaan tercatat. Training belum dijalankan.")
            print("Kesiapan GPU perlu diperiksa berikutnya.")


def main():
    try:
        start_t4()

    except HTTPException as error:
        print(f"HTTP {error.status_code}: {error.detail}")

    except RefreshError:
        print("Otorisasi Colab perlu diperbarui.")

    except (TransportError, RequestException):
        print("Koneksi ke Google terputus atau melewati batas waktu.")
        print("Hasil permintaan belum pasti; periksa status dahulu.")

    except (ValueError, KeyError, OSError):
        print("Token, respons, atau catatan runtime belum dapat dibaca.")
        print("Jangan hapus token atau catatan runtime.")


if __name__ == "__main__":
    main()