import re
import unicodedata
from IR67_porter_stemmer import PorterStemmer
import IR67_config as config

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

def tokenize_text(text):
    return _TOKEN_RE.findall(text)

def tokenize(path):
    docs = parse_cran_all(path)
    return [(doc_id, tokenize_text(text)) for doc_id, text in docs]

def normalize(tokens):
    normalized = []
    for tok in tokens:
        t = tok.casefold()
        t = unicodedata.normalize("NFKD", t)
        t = "".join(ch for ch in t if not unicodedata.combining(ch))
        if t:
            normalized.append(t)
    return normalized

# Fix for weird encoding corruption in the provided stopwords file ("herse\u201d" instead of "herself", etc.)
_KNOWN_STOPWORD_FIXES = {
    "herse\u201d": "herself",
    "himse\u201d": "himself",
    "itse\u201d": "itself",
    "myse\u201d": "myself",
}

def load_stopwords(path):
    stopset = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if not w:
                continue
            w = _KNOWN_STOPWORD_FIXES.get(w, w)
            stopset.add(w.casefold())
    return stopset

def remove_stopwords(tokens, stopset):
    return [t for t in tokens if t not in stopset]

def stem(tokens, stemmer):
    return [stemmer.stem(t) for t in tokens]

def apply_pipeline(text, stopset, stemmer):
    tokens = tokenize_text(text)
    tokens = normalize(tokens)
    tokens = remove_stopwords(tokens, stopset)
    return stem(tokens, stemmer)

def parse_cran_all(path):
    # Parses the Cranfield collection format.
    # Note: documents 240, 576, 578 have literal ".A" or ".W" in their abstract text which acts as 
    # false section breaks. We ignore that quirk here as it's standard.
    docs = []
    doc_id = None
    section = None
    buffers = {".T": [], ".A": [], ".B": [], ".W": []}

    def flush_doc():
        if doc_id is not None:
            text = " ".join(buffers[".T"]) + " " + " ".join(buffers[".W"])
            docs.append((doc_id, text))

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith(".I "):
                flush_doc()
                doc_id = int(line.split()[1])
                section = None
                buffers = {k: [] for k in buffers}
            elif line in (".T", ".A", ".B", ".W"):
                section = line
            elif section is not None:
                buffers[section].append(line)
        flush_doc()

    return docs

def main():
    stopset = load_stopwords(config.STOPWORDS_PATH)
    stemmer = PorterStemmer()

    print(f"Tokenizing {config.CRAN_ALL_PATH} ...")
    doc_tokens = tokenize(config.CRAN_ALL_PATH)

    total_tokens = 0
    with open(config.PROCESSED_PATH, "w", encoding="utf-8") as f:
        for doc_id, tokens in doc_tokens:
            tokens = normalize(tokens)
            tokens = remove_stopwords(tokens, stopset)
            tokens = stem(tokens, stemmer)
            
            total_tokens += len(tokens)
            f.write(f".I {doc_id}\n.S\n{' '.join(tokens)}\n")

    print(f"Wrote to {config.PROCESSED_PATH}")
    print(f"Total tokens: {total_tokens}")
    print(f"Average tokens/doc: {total_tokens / len(doc_tokens):.1f}")

if __name__ == "__main__":
    main()
