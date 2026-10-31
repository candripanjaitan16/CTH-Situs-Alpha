import argparse
import re
import sqlite3
from pathlib import Path
from .common import REFUSAL, child

STOPWORDS = {"apa", "apakah", "itu", "yang", "di", "ke", "dari", "dan", "atau", "untuk", "dengan", "saya", "aku", "kamu", "tolong", "jelaskan", "siapa", "bagaimana", "berapa", "kapan", "dimana", "adalah", "tentang", "sebutkan"}


def words(text):
    return set(re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)) - STOPWORDS


def answer_from_sources(database, question):
    keys = words(question)
    if not keys:
        return {"answer": REFUSAL, "sources": [], "mode": "extractive"}
    matches = []
    with sqlite3.connect(database) as conn:
        for source, content in conn.execute("SELECT source,content FROM passages"):
            # Keluaran selalu kutipan; pencocokan kata bukan jaminan relevansi semantik.
            content_words = words(content)
            if keys <= content_words:
                matches.append((len(content), source, content))
    matches.sort(key=lambda item: (item[0], item[1]))
    if not matches:
        return {"answer": REFUSAL, "sources": [], "mode": "extractive"}
    _, source, content = matches[0]
    return {"answer": content, "sources": [source], "mode": "extractive"}



def answer_with_qwen(run_dir, question, evidence):
    if not evidence["sources"]:
        return evidence
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from .common import MODEL_ID, MODEL_REVISION, SYSTEM, read_json, require_t4
    require_t4()
    if not (run_dir / "complete.json").exists():
        raise ValueError("Model run belum selesai dilatih.")
    settings = read_json(run_dir / "run.json")["settings"]
    if settings["model_id"] != MODEL_ID or settings["model_revision"] != MODEL_REVISION:
        raise ValueError("Model dasar tidak cocok dengan kode pengujian.")
    adapter = run_dir / "adapter"
    tokenizer = AutoTokenizer.from_pretrained(str(adapter), trust_remote_code=False)
    base = AutoModelForCausalLM.from_pretrained(MODEL_ID, revision=MODEL_REVISION,
        torch_dtype=torch.float16, device_map={"": 0}, trust_remote_code=False, use_safetensors=True)
    model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
    model.eval()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"SUMBER:\n{evidence['answer']}\n\nPERTANYAAN:\n{question}"},
    ]
    inputs = tokenizer.apply_chat_template(messages, tokenize=True,
        add_generation_prompt=True, return_dict=True, return_tensors="pt")
    if inputs["input_ids"].shape[-1] > 2048:
        raise ValueError("Pertanyaan dan sumber terlalu panjang untuk batas pengujian ini.")
    inputs = {key: value.to("cuda:0") for key, value in inputs.items()}
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=160, do_sample=False,
            repetition_penalty=1.1, pad_token_id=tokenizer.eos_token_id)
    text = tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
    return {"answer": text or REFUSAL, "sources": evidence["sources"],
        "mode": "qwen", "notice": "Jawaban generatif; kesetiaan terhadap sumber belum dijamin. Gunakan mode extractive untuk kutipan persis."}


def main():
    import json
    parser = argparse.ArgumentParser(description="Jawaban kutipan sumber, tanpa model AI kedua.")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--mode", choices=["extractive", "qwen"], default="extractive")
    args = parser.parse_args()
    database = child(Path(args.project_dir).resolve() / "training_results", args.run_id) / "dataset.sqlite"
    if not database.is_file():
        raise FileNotFoundError("Indeks sumber belum tersedia.")
    result = answer_from_sources(database, args.question)
    if args.mode == "qwen":
        result = answer_with_qwen(database.parent, args.question, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
