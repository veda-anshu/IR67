"""
preprocess.py

Preprocessing program for the Cranfield collection.

Implements the four required steps as four separate functions:
    1. tokenize(text)                    -> raw tokens
    2. normalize(tokens)                 -> case-folded / cleaned tokens
    3. remove_stopwords(tokens, stopset) -> tokens with stopwords dropped
    4. stem(tokens, stemmer)             -> Porter-stemmed tokens

and integrates them into a single pipeline, process_text(), which is run
over every document's Title + Abstract in cran.all.

Pipeline order: tokenize -> normalize -> remove_stopwords -> stem

Usage:
    python3 preprocess.py
Reads config.CRAN_ALL_PATH and config.STOPWORDS_PATH, writes
config.PROCESSED_PATH (IR67_processed.all).
"""

import re
import sys
import unicodedata

from porter_stemmer import PorterStemmer
import config

# Step 1: Tokenization

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

def tokenize(text):
    """
    Convert a raw text string into a list of token strings.

    A token is a maximal run of ASCII letters/digits. This means
    punctuation, whitespace, and symbols (hyphens, slashes, apostrophes,
    parentheses, the '/emphasis/' markers used in cran.all, etc.) act as
    token separators. E.g. "boundary-layer-control" -> ["boundary",
    "layer", "control"], "wing's" -> ["wing", "s"].
    """
    return _TOKEN_RE.findall(text)

# Step 2: Normalization

def normalize(tokens):
    """
    Normalize a list of raw tokens:
      - case-fold to lowercase
      - strip accents/diacritics (Unicode NFKD + drop combining marks)
      - drop any token that becomes empty as a result

    Tokenize() already restricts tokens to [A-Za-z0-9], so on this
    (mostly ASCII scientific-English) corpus the accent-stripping is a
    defensive no-op most of the time, but it keeps the function correct
    and general rather than corpus-specific.
    """
    out = []
    for tok in tokens:
        t = tok.casefold()
        t = unicodedata.normalize("NFKD", t)
        t = "".join(ch for ch in t if not unicodedata.combining(ch))
        if t:
            out.append(t)
    return out

# Step 3: Stop word removal

_KNOWN_STOPWORD_FIXES = {
    "herse\u201d": "herself",
    "himse\u201d": "himself",
    "itse\u201d": "itself",
    "myse\u201d": "myself",
}

def load_stopwords(path):
    """Load a stopword list (one word per line) into a set."""
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
    """Return tokens with any word present in stopset removed."""
    return [t for t in tokens if t not in stopset]

# Step 4: Stemming

def stem(tokens, stemmer):
    """Apply the Porter stemmer to every token."""
    return [stemmer.stem(t) for t in tokens]

# Pipeline integration

def apply_pipeline(text, stopset, stemmer):
    """
    Run the full preprocessing pipeline on a raw text string and return
    the final list of index-ready tokens. This exact function is reused
    for both document text (in preprocess.py) and query text (in
    search.py) so that documents and queries are guaranteed to be
    processed identically.
    """
    tokens = tokenize(text)
    tokens = normalize(tokens)
    tokens = remove_stopwords(tokens, stopset)
    tokens = stem(tokens, stemmer)
    return tokens

# cran.all.1400 parsing

def parse_cran_all(path):
    """
    Parse the SMART/Cranfield-format cran.all file into a list of
    (doc_id, title_and_abstract_text) tuples, in doc_id order.

    File format: a document starts with a ".I <docid>" line and contains
    ".T" (title), ".A" (author), ".B" (bibliographic info) and ".W"
    (abstract) sections. Per the assignment, only .T and .W are used;
    .A and .B are parsed (to know where they end) but discarded.
    """
    docs = []
    doc_id = None
    section = None
    buffers = {".T": [], ".A": [], ".B": [], ".W": []}

    def flush():
        if doc_id is not None:
            text = " ".join(buffers[".T"]) + " " + " ".join(buffers[".W"])
            docs.append((doc_id, text))

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if line.startswith(".I "):
                flush()
                doc_id = int(line.split()[1])
                section = None
                buffers = {".T": [], ".A": [], ".B": [], ".W": []}
            elif line in (".T", ".A", ".B", ".W"):
                section = line
            elif section is not None:
                buffers[section].append(line)
            # lines before the first .I (there are none in this file) are ignored
        flush()

    return docs

def main():
    stopset = load_stopwords(config.STOPWORDS_PATH)
    stemmer = PorterStemmer()

    docs = parse_cran_all(config.CRAN_ALL_PATH)
    print(f"Parsed {len(docs)} documents from {config.CRAN_ALL_PATH}")

    total_tokens = 0
    with open(config.PROCESSED_PATH, "w", encoding="utf-8") as out:
        for doc_id, text in docs:
            tokens = apply_pipeline(text, stopset, stemmer)
            total_tokens += len(tokens)
            out.write(f".I {doc_id}\n")
            out.write(".S\n")
            out.write(" ".join(tokens) + "\n")

    print(f"Wrote {config.PROCESSED_PATH}")
    print(f"Total tokens (with repetition) across corpus: {total_tokens}")
    print(f"Average tokens/doc: {total_tokens / len(docs):.1f}")


if __name__ == "__main__":
    sys.exit(main())
