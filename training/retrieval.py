"""Conservative, bounded extraction of documentary evidence, never chat turns."""
import hashlib
import re
import sqlite3

STOPWORDS = set('apa apakah itu yang di ke dari dan atau untuk dengan saya aku kamu tolong jelaskan siapa bagaimana berapa kapan dimana adalah tentang sebutkan manfaat informasi proyek utama'.split())
ROLE = re.compile(r'(?:\b(?:user|assistant|system|human|pengguna|asisten)\s*:|<\|(?:im_start|im_end|endoftext)\|>)', re.I)
HEADING = re.compile(r'^\s*(?:#{1,6}\s*)?(?:fakta|sumber|dokumentasi|catatan proyek)\s*:\s*', re.I)
EXERCISE = re.compile(r'^\s*(?:(?:soal|pertanyaan|jawaban|question|answer|latihan)\b|[A-D][.)]\s|\d+[.)]\s*(?:hitung|berapa|siapa|pilih))', re.I)
DIRECTIVE = re.compile(r'^\s*(?:abaikan|ikuti|jawablah|jawab|instruksi|anggap|ignore|you are|saya|aku|kamu|anda)\b', re.I)
IDENTITY = re.compile(r'\b(?:pencipta|pembuat|pendiri|dikembangkan|dibuat|didirikan|diciptakan)\b', re.I)


def words(text):
    return set(re.findall(r'[^\W_]+', text.lower(), flags=re.UNICODE)) - STOPWORDS


def documentary_spans(content, state=None):
    state = state if state is not None else {'blocked': False}
    offset = 0
    for line in content.splitlines(keepends=True):
        heading = HEADING.match(line)
        if heading:
            state['blocked'] = False
        if ROLE.search(line) or EXERCISE.match(line):
            state['blocked'] = True
            offset += len(line)
            continue
        if state['blocked']:
            offset += len(line)
            continue
        start = heading.end() if heading else 0
        for match in re.finditer(r'[^.!?\n]+(?:[.!?](?=\s|$)|$)', line[start:]):
            raw = match.group()
            quote = raw.strip().lstrip('-* ').strip()
            if (not quote or quote.endswith('?') or len(quote) < 15 or len(quote) > 800
                    or DIRECTIVE.match(quote) or ROLE.search(quote)
                    or len(words(quote)) < 2):
                continue
            position = offset + start + match.start() + raw.index(quote)
            yield quote, position, position + len(quote)
        offset += len(line)


def create_index(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS passages (id INTEGER PRIMARY KEY, source TEXT, content TEXT, digest TEXT UNIQUE)')
    conn.execute('CREATE TABLE IF NOT EXISTS retrieval_meta (version INTEGER NOT NULL)')
    if conn.execute('SELECT COUNT(*) FROM retrieval_meta').fetchone()[0] == 0:
        conn.execute('INSERT INTO retrieval_meta VALUES (2)')


def store_quote(conn, source, quote):
    digest = hashlib.sha256((source + '\0' + quote).encode()).hexdigest()
    conn.execute('INSERT OR IGNORE INTO passages(source,content,digest) VALUES(?,?,?)', (source, quote, digest))


def index_source(conn, source, handle):
    state = {'blocked': False}
    while True:
        line = handle.readline(8193)
        if not line:
            return
        if '\x00' in line:
            raise ValueError('Sumber teks mengandung NUL biner.')
        if len(line) > 8192:
            # Discard the whole oversized line and keep its unknown continuation out of evidence.
            state['blocked'] = True
            while line and not line.endswith('\n'):
                line = handle.readline(8193)
            continue
        for quote, _, _ in documentary_spans(line, state):
            store_quote(conn, source, quote)


def retrieve(database, question, limit=3):
    keys = words(question)
    if not keys:
        return []
    identity_question = bool(re.search(r'\b(?:pencipta|pembuat|pendiri|dikembangkan|dibuat|diciptakan)\b', question, re.I))
    if identity_question:
        keys -= {'pencipta', 'pembuat', 'pendiri', 'dikembangkan', 'dibuat', 'diciptakan', 'oleh'}
    if not keys:
        return []
    matches = []
    with sqlite3.connect(database) as conn:
        try:
            version = conn.execute('SELECT version FROM retrieval_meta').fetchone()
        except sqlite3.OperationalError:
            return []
        if version != (2,):
            return []
        for passage_id, source, content in conn.execute('SELECT id,source,content FROM passages'):
            for quote, start, end in documentary_spans(content):
                tokens = words(quote)
                overlap = keys & tokens
                coverage = len(overlap) / len(keys)
                if coverage < 1:
                    continue
                if identity_question and not IDENTITY.search(quote):
                    continue
                # Prefer concise sentences covering the question rather than large keyword dumps.
                score = coverage + len(overlap) / max(len(tokens), 1)
                record = {'source': source, 'quote': quote, 'passage_id': passage_id,
                          'start': start, 'end': end, 'offset_scope': 'passage'}
                matches.append((score, record))
                matches.sort(key=lambda item: (-item[0], len(item[1]['quote']), item[1]['source']))
                del matches[limit:]
    unique = []
    seen = set()
    for _, record in matches:
        if record['quote'] not in seen:
            seen.add(record['quote'])
            unique.append(record)
    return unique
