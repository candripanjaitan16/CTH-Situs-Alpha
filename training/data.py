import hashlib
import json
import sqlite3
from pathlib import Path

from .common import REFUSAL, SYSTEM, file_hash


def dataset_manifest(directory):
    directory = Path(directory).resolve()
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink tidak diperbolehkan pada direktori dataset.")
        if path.is_file() and path.suffix.lower() in {".txt", ".jsonl"}:
            if directory not in path.resolve().parents:
                raise ValueError("Berkas berada di luar direktori dataset.")
            if path.stat().st_size == 0:
                raise ValueError(f"Berkas kosong: {path.name}")
            files.append({"name": str(path.relative_to(directory)), "sha256": file_hash(path), "size": path.stat().st_size})
    if not files:
        raise ValueError("Tidak ada TXT atau JSONL dalam direktori dataset.")
    return files


def validate_qa(record):
    if not isinstance(record, dict):
        raise ValueError("Setiap baris JSONL harus berupa objek.")
    for key in ("context", "question", "answer"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"Kolom {key} harus berisi teks.")
        if "\x00" in record[key]:
            raise ValueError("Data mengandung karakter biner NUL.")
    answer = record["answer"].strip()
    context = record["context"].strip()
    if answer != REFUSAL and answer not in context:
        raise ValueError("Jawaban JSONL harus kutipan persis dari context, atau kalimat penolakan resmi. Jangan mengarang pasangan QA.")
    return {key: record[key].strip() for key in ("context", "question", "answer")}


def encode_qa(tokenizer, record, max_length):
    record = validate_qa(record)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"SUMBER:\n{record['context']}\n\nPERTANYAAN:\n{record['question']}"},
    ]
    prompt_ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    answer_ids = tokenizer.encode(record["answer"], add_special_tokens=False) + [tokenizer.eos_token_id]
    input_ids = prompt_ids + answer_ids
    if len(input_ids) > max_length:
        raise ValueError("Contoh QA melebihi max-length. Pecah context atau naikkan max-length; jawaban tidak dipotong diam-diam.")
    labels = [-100] * len(prompt_ids) + answer_ids
    return input_ids, labels, record["context"]


def create_store(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE samples (id INTEGER PRIMARY KEY, digest TEXT UNIQUE, group_id TEXT, input_ids TEXT, labels TEXT, split TEXT)")
    conn.execute("CREATE TABLE passages (id INTEGER PRIMARY KEY, source TEXT, content TEXT, digest TEXT UNIQUE)")
    return conn


def add_passage(conn, source, content):
    for start in range(0, len(content), 1200):
        passage = content[start:start + 1200].strip()
        if passage:
            digest = hashlib.sha256(passage.encode()).hexdigest()
            conn.execute("INSERT OR IGNORE INTO passages(source,content,digest) VALUES(?,?,?)", (source, passage, digest))


def add_sample(conn, input_ids, labels, group):
    encoded = json.dumps(input_ids, separators=(",", ":"))
    digest = hashlib.sha256((encoded + json.dumps(labels)).encode()).hexdigest()
    conn.execute("INSERT OR IGNORE INTO samples(digest,group_id,input_ids,labels) VALUES(?,?,?,?)", (digest, group, encoded, json.dumps(labels)))


def prepare_data(directory, manifest, tokenizer, max_length, database, seed):
    conn = create_store(database)
    modes = set()
    try:
        for item in manifest:
            path = Path(directory) / item["name"]
            if path.suffix.lower() == ".jsonl":
                modes.add("supervised_qa")
                with path.open(encoding="utf-8") as handle:
                    for number, line in enumerate(handle, 1):
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            ids, labels, context = encode_qa(tokenizer, record, max_length)
                        except (ValueError, TypeError) as error:
                            raise ValueError(f"{item['name']} baris {number}: {error}") from None
                        group = hashlib.sha256(context.encode()).hexdigest()
                        add_sample(conn, ids, labels, group)
                        add_passage(conn, item["name"], context)
            else:
                modes.add("text_adaptation")
                with path.open(encoding="utf-8", errors="strict") as handle:
                    while True:
                        text = handle.read(16000)
                        if not text:
                            break
                        if "\x00" in text:
                            raise ValueError(f"Data biner ditemukan: {item['name']}")
                        if not text.strip():
                            continue
                        add_passage(conn, item["name"], text)
                        tokens = tokenizer.encode(text, add_special_tokens=False)
                        for start in range(0, len(tokens), max_length - 1):
                            ids = tokens[start:start + max_length - 1] + [tokenizer.eos_token_id]
                            if len(ids) >= 2:
                                group = hashlib.sha256(json.dumps(ids).encode()).hexdigest()
                                add_sample(conn, ids, ids.copy(), group)
            conn.commit()
        groups = [row[0] for row in conn.execute("SELECT DISTINCT group_id FROM samples")]
        if len(groups) < 10:
            raise ValueError("Butuh minimal 10 kelompok teks/context berbeda untuk train dan validasi. Contoh kecil hanya untuk uji kode, bukan jaminan kualitas.")
        groups.sort(key=lambda group: hashlib.sha256(f"{seed}:{group}".encode()).hexdigest())
        eval_groups = set(groups[:max(1, len(groups) // 10)])
        for group in groups:
            conn.execute("UPDATE samples SET split=? WHERE group_id=?", ("eval" if group in eval_groups else "train", group))
        conn.commit()
        counts = dict(conn.execute("SELECT split,COUNT(*) FROM samples GROUP BY split"))
        return {"counts": counts, "modes": sorted(modes), "passages": conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]}
    finally:
        conn.close()


class StoredDataset:
    def __init__(self, database, split):
        self.database = str(database)
        with sqlite3.connect(self.database) as conn:
            self.ids = [row[0] for row in conn.execute("SELECT id FROM samples WHERE split=? ORDER BY id", (split,))]
        self.conn = None

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, index):
        if self.conn is None:
            self.conn = sqlite3.connect(self.database)
        ids, labels = self.conn.execute("SELECT input_ids,labels FROM samples WHERE id=?", (self.ids[index],)).fetchone()
        ids = json.loads(ids)
        return {"input_ids": ids, "attention_mask": [1] * len(ids), "labels": json.loads(labels)}


def collate_examples(examples, pad_token_id):
    import torch
    length = max(len(row["input_ids"]) for row in examples)
    return {
        "input_ids": torch.tensor([row["input_ids"] + [pad_token_id] * (length - len(row["input_ids"])) for row in examples]),
        "attention_mask": torch.tensor([row["attention_mask"] + [0] * (length - len(row["attention_mask"])) for row in examples]),
        "labels": torch.tensor([row["labels"] + [-100] * (length - len(row["labels"])) for row in examples]),
    }
