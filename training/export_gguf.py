import argparse
import gc
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from .common import LLAMA_COMMIT, MODEL_ID, MODEL_REVISION, child, file_hash, now, project_lock, read_json, require_t4, validate_name, write_json


def command(*args, cwd=None):
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def verify_gguf(path):
    with Path(path).open("rb") as handle:
        if handle.read(4) != b"GGUF":
            raise ValueError("Berkas keluaran bukan GGUF yang valid.")
    if Path(path).stat().st_size < 1024:
        raise ValueError("Berkas GGUF terlalu kecil atau tidak lengkap.")


def main():
    parser = argparse.ArgumentParser(description="CTH: merge adapter dan ekspor GGUF, tanpa melatih ulang.")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--quantization", choices=["Q4_K_M", "Q8_0", "F16"], default="Q4_K_M")
    args = parser.parse_args()
    require_t4()
    project = Path(args.project_dir).resolve()
    with project_lock(project):
        run_dir = child(project / "training_results", args.run_id)
        manifest = read_json(run_dir / "run.json")
        settings = manifest["settings"]
        if settings["model_id"] != MODEL_ID or settings["model_revision"] != MODEL_REVISION:
            raise ValueError("Model dasar/revisi tidak cocok dengan versi skrip ekspor ini.")
        if not (run_dir / "complete.json").exists():
            raise ValueError("Run training belum selesai; tidak mengekspor checkpoint parsial.")
        if read_json(run_dir / "status.json").get("status") != "completed":
            raise ValueError("Status run bukan completed.")
        model_name = validate_name(settings["model_name"])
        adapter = run_dir / "adapter"
        adapter_config = read_json(adapter / "adapter_config.json")
        if adapter_config.get("base_model_name_or_path") != MODEL_ID:
            raise ValueError("Adapter tidak merujuk model dasar yang diizinkan.")
        export_id = args.run_id + "-" + uuid4().hex[:8]
        export_dir = child(project / "models", export_id)
        export_dir.mkdir(parents=True, exist_ok=False)
        status_file = export_dir / "status.json"
        write_json(status_file, {"status": "preparing", "updated_at": now()})
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
            with tempfile.TemporaryDirectory(prefix="cth-export-") as temp:
                work = Path(temp)
                merged = work / "merged"
                print("1/4 Menggabungkan adapter dengan model dasar...", flush=True)
                base = AutoModelForCausalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION,
                    torch_dtype=torch.float16, device_map={"": 0}, trust_remote_code=False, use_safetensors=True)
                model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
                merged_model = model.merge_and_unload(safe_merge=True)
                merged_model.config.use_cache = True
                merged_model.save_pretrained(str(merged), safe_serialization=True)
                tokenizer = AutoTokenizer.from_pretrained(str(adapter), trust_remote_code=False)
                tokenizer.save_pretrained(str(merged))
                del merged_model, model, base
                gc.collect()
                torch.cuda.empty_cache()
                print("2/4 Menyiapkan llama.cpp pada commit tetap...", flush=True)
                repo = work / "llama.cpp"
                command("git", "init", str(repo))
                command("git", "-C", repo, "remote", "add", "origin", "https://github.com/ggml-org/llama.cpp.git")
                command("git", "-C", repo, "fetch", "--depth", "1", "origin", LLAMA_COMMIT)
                command("git", "-C", repo, "checkout", "--detach", "FETCH_HEAD")
                actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
                if actual != LLAMA_COMMIT:
                    raise ValueError("Commit alat konversi tidak cocok.")
                converter_python = work / "converter-env" / "bin" / "python"
                command(sys.executable, "-m", "venv", str(work / "converter-env"))
                command(converter_python, "-m", "pip", "install", "-r", repo / "requirements" / "requirements-convert_hf_to_gguf.txt")
                print("3/4 Mengubah model menjadi GGUF F16...", flush=True)
                f16 = work / f"{model_name}-F16.gguf"
                command(converter_python, repo / "convert_hf_to_gguf.py", merged, "--outfile", f16, "--outtype", "f16")
                verify_gguf(f16)
                destination = export_dir / f"{model_name}-{args.quantization}.gguf"
                partial = destination.with_suffix(".gguf.partial")
                if args.quantization == "F16":
                    import shutil
                    shutil.copyfile(f16, partial)
                else:
                    print(f"4/4 Kuantisasi {args.quantization}...", flush=True)
                    build = repo / "build"
                    command("cmake", "-S", repo, "-B", build, "-DGGML_CUDA=OFF", "-DGGML_NATIVE=OFF", "-DLLAMA_CURL=OFF", "-DLLAMA_BUILD_TESTS=OFF")
                    command("cmake", "--build", build, "--target", "llama-quantize", "-j", "2")
                    command(build / "bin" / "llama-quantize", f16, partial, args.quantization)
                verify_gguf(partial)
                os.replace(partial, destination)
                write_json(export_dir / "export.json", {"created_at": now(), "source_run": args.run_id,
                    "base_model": MODEL_ID, "base_revision": MODEL_REVISION, "llama_cpp_commit": LLAMA_COMMIT,
                    "quantization": args.quantization, "file": destination.name,
                    "size_bytes": destination.stat().st_size, "sha256": file_hash(destination),
                    "notice": "GGUF berisi model hasil fine-tuning, bukan database sumber proyek."})
                write_json(status_file, {"status": "completed", "updated_at": now(), "file": destination.name})
                print(f"Ekspor selesai: {destination}", flush=True)
                print("Sumber dan aturan pencarian tetap diperlukan jika jawaban wajib hanya dari data proyek.", flush=True)
        except BaseException as error:
            write_json(status_file, {"status": "failed", "updated_at": now(), "error_type": type(error).__name__})
            raise

if __name__ == "__main__":
    main()
