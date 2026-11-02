import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import requests
import websocket
from google.auth.transport.requests import AuthorizedSession

from app.colab import API_URL, RUNTIME_NAME, T4_SPEC
from app.drive_auth import get_colab_credentials


GPU_TEST_CODE = """
import json
import subprocess

try:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )

    devices = []

    for line in result.stdout.strip().splitlines():
        name, memory = line.rsplit(",", 1)

        devices.append({
            "name": name.strip(),
            "memory_mib": int(memory.strip()),
        })

    print("CTH_GPU_RESULT:" + json.dumps({
        "ok": bool(devices),
        "devices": devices,
    }))

except Exception as error:
    print("CTH_GPU_RESULT:" + json.dumps({
        "ok": False,
        "error_type": type(error).__name__,
    }))
"""


def runtime_url(
    base_url,
    path,
    websocket_url=False,
    session_id=None,
    proxy_token=None,
):
    parts = urlsplit(base_url)

    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.fragment
    ):
        raise RuntimeError("Alamat runtime dari Google tidak valid.")

    query = dict(
        parse_qsl(parts.query, keep_blank_values=True)
    )

    if session_id:
        query["session_id"] = session_id

    if proxy_token:
        query["colab-runtime-proxy-token"] = proxy_token

    return urlunsplit((
        "wss" if websocket_url else "https",
        parts.netloc,
        parts.path.rstrip("/") + "/" + path.lstrip("/"),
        urlencode(query),
        "",
    ))


def get_runtime_connection():
    credentials = get_colab_credentials()

    with AuthorizedSession(credentials) as session:
        response = session.get(
            f"{API_URL}/{RUNTIME_NAME}",
            timeout=30,
        )

    if response.status_code == 404:
        raise RuntimeError(
            "Runtime tidak ditemukan. "
            "Hubungkan Colab dari halaman CTH."
        )

    if not response.ok:
        raise RuntimeError(
            f"Pemeriksaan runtime gagal: HTTP {response.status_code}."
        )

    runtime = response.json()

    if runtime.get("runtimeSpec") != T4_SPEC:
        raise RuntimeError(
            "Runtime bukan T4 Standard. Tidak beralih ke CPU."
        )

    connection = runtime.get("connectionInfo", {})

    if not connection.get("url") or not connection.get("token"):
        raise RuntimeError(
            "Informasi koneksi belum tersedia. Tunggu dan coba lagi."
        )

    return connection


def execute_gpu_test(socket_connection, session_id):
    message_id = uuid4().hex

    socket_connection.send(json.dumps({
        "header": {
            "msg_id": message_id,
            "username": "cth",
            "session": session_id,
            "date": datetime.now(timezone.utc).isoformat(),
            "msg_type": "execute_request",
            "version": "5.3",
        },
        "parent_header": {},
        "metadata": {},
        "channel": "shell",
        "content": {
            "code": GPU_TEST_CODE,
            "silent": False,
            "store_history": False,
            "user_expressions": {},
            "allow_stdin": False,
            "stop_on_error": True,
        },
        "buffers": [],
    }))

    output = ""
    received_reply = False
    received_idle = False
    deadline = time.monotonic() + 90

    while time.monotonic() < deadline:
        socket_connection.settimeout(
            min(5, max(0.1, deadline - time.monotonic()))
        )

        try:
            raw = socket_connection.recv()
        except websocket.WebSocketTimeoutException:
            continue
        except websocket.WebSocketConnectionClosedException:
            raise RuntimeError(
                "WebSocket terputus sebelum pengujian selesai."
            ) from None

        if not raw:
            raise RuntimeError(
                "WebSocket ditutup sebelum pengujian selesai."
            )

        try:
            message = json.loads(raw)
        except (ValueError, UnicodeError):
            raise RuntimeError(
                "Format pesan runtime belum didukung pengujian ini."
            ) from None

        if not isinstance(message, dict):
            continue

        parent_id = message.get(
            "parent_header", {}
        ).get("msg_id")

        if parent_id != message_id:
            continue

        message_type = message.get("msg_type") or message.get(
            "header", {}
        ).get("msg_type")

        content = message.get("content", {})

        if message_type == "stream":
            output += content.get("text", "")

            if len(output) > 100000:
                raise RuntimeError(
                    "Keluaran pengujian melebihi batas yang diharapkan."
                )

        elif message_type == "error":
            raise RuntimeError(
                "Kode pengujian gagal di dalam runtime."
            )

        elif message_type == "execute_reply":
            if content.get("status") != "ok":
                raise RuntimeError(
                    "Runtime menolak eksekusi pengujian."
                )

            received_reply = True

        elif (
            message_type == "status"
            and content.get("execution_state") == "idle"
        ):
            received_idle = True

        if received_reply and received_idle:
            break
    else:
        raise RuntimeError(
            "Pengujian GPU melewati batas waktu."
        )

    for line in output.splitlines():
        if line.startswith("CTH_GPU_RESULT:"):
            return json.loads(
                line.removeprefix("CTH_GPU_RESULT:")
            )

    raise RuntimeError(
        "Hasil pengujian GPU tidak diterima."
    )


def check_gpu():
    print(
        "Mengambil koneksi runtime T4...",
        flush=True,
    )

    connection = get_runtime_connection()

    base_url = connection["url"]
    proxy_token = connection["token"]

    kernel_id = None
    socket_connection = None
    session_id = uuid4().hex

    with requests.Session() as session:
        session.headers.update({
            "X-Colab-Runtime-Proxy-Token": proxy_token,
            "X-Colab-Client-Agent": "colab-cli",
        })

        try:
            specs_response = session.get(
                runtime_url(base_url, "api/kernelspecs"),
                timeout=30,
                allow_redirects=False,
            )

            if specs_response.status_code != 200:
                raise RuntimeError(
                    "Akses Jupyter gagal: "
                    f"HTTP {specs_response.status_code}."
                )

            specs = specs_response.json()
            kernel_name = specs.get("default")

            if not kernel_name:
                raise RuntimeError(
                    "Kernel default tidak ditemukan."
                )

            xsrf = session.cookies.get("_xsrf")

            if xsrf:
                session.headers["X-XSRFToken"] = xsrf

            print(
                "Membuat kernel pengujian terpisah...",
                flush=True,
            )

            response = session.post(
                runtime_url(base_url, "api/kernels"),
                json={"name": kernel_name},
                timeout=30,
                allow_redirects=False,
            )

            if response.status_code != 201:
                raise RuntimeError(
                    "Pembuatan kernel uji gagal: "
                    f"HTTP {response.status_code}."
                )

            kernel_id = response.json().get("id")

            if not isinstance(kernel_id, str) or not re.fullmatch(
                r"[A-Za-z0-9_-]+",
                kernel_id,
            ):
                kernel_id = None
                raise RuntimeError(
                    "ID kernel uji tidak valid."
                )

            address = urlsplit(base_url)

            print(
                "Menghubungkan WebSocket...",
                flush=True,
            )

            socket_connection = websocket.create_connection(
                runtime_url(
                    base_url,
                    f"api/kernels/{kernel_id}/channels",
                    websocket_url=True,
                    session_id=session_id,
                    proxy_token=proxy_token,
                ),
                header=[
                    f"X-Colab-Runtime-Proxy-Token: {proxy_token}",
                    "X-Colab-Client-Agent: colab-cli",
                ],
                origin=f"https://{address.netloc}",
                cookie="; ".join(
                    f"{cookie.name}={cookie.value}"
                    for cookie in session.cookies
                ),
                timeout=30,
            )

            print(
                "Menjalankan nvidia-smi di Colab...",
                flush=True,
            )

            result = execute_gpu_test(
                socket_connection,
                session_id,
            )

            if not result.get("ok"):
                raise RuntimeError(
                    "nvidia-smi gagal mendeteksi GPU. "
                    f"Jenis error: {result.get('error_type', 'Unknown')}"
                )

            devices = result.get("devices", [])

            if not devices or not all(
                "T4" in device.get("name", "").upper()
                for device in devices
            ):
                raise RuntimeError(
                    "GPU yang terdeteksi bukan T4."
                )

            print(json.dumps({
                "status": "success",
                "gpu_verified": True,
                "runtime": RUNTIME_NAME,
                "devices": devices,
                "message": "GPU T4 terdeteksi di dalam runtime.",
            }, indent=2, ensure_ascii=False))

        finally:
            if socket_connection:
                try:
                    socket_connection.close()
                except websocket.WebSocketException:
                    pass

            # Tutup kernel uji saja, bukan runtime GPU
            if kernel_id:
                try:
                    response = session.delete(
                        runtime_url(
                            base_url,
                            f"api/kernels/{kernel_id}",
                        ),
                        timeout=15,
                        allow_redirects=False,
                    )

                    if response.status_code in (204, 404):
                        print(
                            "Kernel uji ditutup. Runtime tetap tersedia.",
                            flush=True,
                        )
                    else:
                        print(
                            "Kernel uji belum terkonfirmasi tertutup. "
                            f"HTTP: {response.status_code}",
                            flush=True,
                        )

                except requests.exceptions.RequestException:
                    print(
                        "Penutupan kernel uji belum dapat dipastikan.",
                        flush=True,
                    )


if __name__ == "__main__":
    try:
        check_gpu()

    except RuntimeError as error:
        print(f"Gagal: {error}", flush=True)

    except Exception as error:
        # Hindari mencetak URL dan token autentikasi
        print(
            "Pengujian gagal pada koneksi atau respons runtime. "
            f"Jenis error: {type(error).__name__}",
            flush=True,
        )