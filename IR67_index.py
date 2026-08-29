"""
index.py

Builds an inverted index from the preprocessed collection and writes it to IR67_cran.index.

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

import IR67_config as config


def parse_processed_file(path):
    """
    Parse IR67_processed.all file (as produced by preprocess.py)
    into a list of (doc_id, [tokens]) tuples.
    """
    docs = []
    with open(path, encoding="utf-8") as f:
        iterator = iter(f)
        for line in iterator:
            line = line.strip()
            if line.startswith(".I "):
                doc_id = int(line.split()[1])
                try:
                    next_line = next(iterator).strip()
                    if next_line == ".S":
                        tok_line = next(iterator).strip()
                        tokens = tok_line.split() if tok_line else []
                        docs.append((doc_id, tokens))
                    else:
                        docs.append((doc_id, []))
                except StopIteration:
                    docs.append((doc_id, []))
    return docs


def build_index(docs):
    """
    Build an inverted index: term -> sorted list of unique docids.

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
