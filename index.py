"""
index.py

Builds an inverted index from the preprocessed collection
(<GROUP>_processed.all) and writes it to <GROUP>_cran.index.

Index file format:
    line 1:  <vocab_size>, <max_docid>
    line 2+: <term> <docid1>,<docid2>,...,<docidN>      (docids ascending)
    ... one line per term, terms sorted lexicographically ...

Usage:
    python3 index.py
Reads config.PROCESSED_PATH, writes config.INDEX_PATH.
"""

import sys
from collections import defaultdict

import config


def parse_processed_file(path):
    """
    Parse a <GROUP>_processed.all file (as produced by preprocess.py)
    into a list of (doc_id, [tokens]) tuples.
    """
    docs = []
    doc_id = None
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith(".I "):
            doc_id = int(line.split()[1])
            i += 1
            if i < len(lines) and lines[i] == ".S":
                i += 1
                tokens = lines[i].split() if i < len(lines) else []
                docs.append((doc_id, tokens))
                i += 1
            else:
                docs.append((doc_id, []))
        else:
            i += 1
    return docs


def build_index(docs):
    """
    Build an inverted index: term -> sorted list of unique docids in
    which the term occurs. A postings list records a docid at most once
    even if the term occurs multiple times in that document, since this
    index only needs to support Boolean (presence/absence) retrieval.

    Returns (index_dict, max_docid).
    """
    index = defaultdict(set)
    max_docid = 0
    for doc_id, tokens in docs:
        max_docid = max(max_docid, doc_id)
        for tok in tokens:
            index[tok].add(doc_id)

    # freeze postings lists into sorted lists
    index = {term: sorted(postings) for term, postings in index.items()}
    return index, max_docid


def write_index(index, max_docid, path):
    """Write the index to disk in the required format."""
    vocab_size = len(index)
    with open(path, "w", encoding="utf-8") as out:
        out.write(f"{vocab_size}, {max_docid}\n")
        for term in sorted(index.keys()):
            postings = ",".join(str(d) for d in index[term])
            out.write(f"{term} {postings}\n")


def main():
    docs = parse_processed_file(config.PROCESSED_PATH)
    print(f"Loaded {len(docs)} documents from {config.PROCESSED_PATH}")

    index, max_docid = build_index(docs)
    write_index(index, max_docid, config.INDEX_PATH)

    print(f"Wrote {config.INDEX_PATH}")
    print(f"Vocabulary size: {len(index)}")
    print(f"Max docid: {max_docid}")
    total_postings = sum(len(v) for v in index.values())
    print(f"Total postings (sum of postings-list lengths): {total_postings}")


if __name__ == "__main__":
    sys.exit(main())
