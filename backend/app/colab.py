import json

from fastapi import APIRouter, HTTPException
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import AuthorizedSession
from requests.exceptions import RequestException

from app.drive_auth import get_colab_credentials


router = APIRouter(
    prefix="/api/colab",
    tags=["Google Colab"],
)

API_URL = "https://colaboratory.googleapis.com/v1beta"

T4_SPEC = {
    "variant": "VARIANT_GPU",
    "accelerator": "T4",
    "shape": "SHAPE_STANDARD",
}


def read_api(session, path):
    response = session.get(
        f"{API_URL}/{path}",
        timeout=30,
    )

    if not response.ok:
        raise HTTPException(
            status_code=502,
            detail=(
                "Pemeriksaan Colab gagal. "
                f"Google mengembalikan HTTP {response.status_code}."
            ),
        )

    return response.json()


def check_colab():
    try:
        credentials = get_colab_credentials()

        with AuthorizedSession(credentials) as session:
            specs = read_api(session, "runtimespecs")
            runtime_data = read_api(session, "runtimes")

        t4_eligible = any(
            item.get("key") == T4_SPEC
            and item.get("eligible") is True
            for item in specs.get("runtimeSpecs", [])
        )

        # Jangan kirim token koneksi runtime
        runtimes = []

        for runtime in runtime_data.get("runtimes", []):
            spec = runtime.get("runtimeSpec", {})

            runtimes.append({
                "name": runtime.get("name"),
                "variant": spec.get("variant"),
                "accelerator": spec.get("accelerator"),
                "shape": spec.get("shape"),
                "is_t4_standard": spec == T4_SPEC,
            })

        return {
            "api_status": "connected",
            "t4_eligible": t4_eligible,
            "requested_spec": T4_SPEC,
            "runtimes": runtimes,
            "message": (
                "Pemeriksaan selesai. Tidak ada runtime "
                "yang dibuat, diganti, atau dihapus."
            ),
        }

    except RefreshError:
        raise HTTPException(
            status_code=401,
            detail="Otorisasi Colab perlu diperbarui.",
        ) from None

    except (TransportError, RequestException):
        raise HTTPException(
            status_code=503,
            detail="Tidak dapat menghubungi Google Colab.",
        ) from None

    except (ValueError, KeyError, OSError):
        raise HTTPException(
            status_code=503,
            detail="Token atau respons Colab belum dapat dibaca.",
        ) from None


@router.get("/check")
def colab_check():
    return check_colab()


def main():
    print("Memeriksa akses Colab dan runtime...", flush=True)

    try:
        result = check_colab()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except HTTPException as error:
        print(f"HTTP {error.status_code}: {error.detail}")


if __name__ == "__main__":
    main()