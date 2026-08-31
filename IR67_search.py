import argparse
import sys

import IR67_config as config
from IR67_preprocess import apply_pipeline, load_stopwords
from IR67_porter_stemmer import PorterStemmer

def load_index(path):
    index = {}
    with open(path, encoding="utf-8") as f:
        header = f.readline().strip()
        vocab_size, max_docid = (int(x.strip()) for x in header.split(","))
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            term, postings_str = line.split(" ", 1)
            index[term] = [int(d) for d in postings_str.split(",") if d]
    return index, vocab_size, max_docid

def merge_and(p1, p2):
    # Two-pointer walk for O(N+M) list intersection
    result = []
    i = j = 0
    while i < len(p1) and j < len(p2):
        if p1[i] == p2[j]:
            result.append(p1[i])
            i += 1
            j += 1
        elif p1[i] < p2[j]:
            i += 1
        else:
            j += 1
    return result

def merge_or(p1, p2):
    # Two-pointer walk for O(N+M) list union
    result = []
    i = j = 0
    while i < len(p1) and j < len(p2):
        if p1[i] == p2[j]:
            result.append(p1[i])
            i += 1
            j += 1
        elif p1[i] < p2[j]:
            result.append(p1[i])
            i += 1
        else:
            result.append(p2[j])
            j += 1
    result.extend(p1[i:])
    result.extend(p2[j:])
    return result

class QueryError(ValueError):
    pass

def parse_query(raw_query):
    parts = raw_query.strip().split()
    if len(parts) != 3:
        raise QueryError(f"Expected 'term1 AND|OR term2', got: {raw_query!r}")
    term1, conn, term2 = parts
    conn = conn.upper()
    if conn not in ("AND", "OR"):
        raise QueryError(f"Connective must be AND or OR, got: {conn!r}")
    return term1, conn, term2

def run_query(raw_query, index, stopset, stemmer):
    term1_raw, conn, term2_raw = parse_query(raw_query)

    t1_list = apply_pipeline(term1_raw, stopset, stemmer)
    t2_list = apply_pipeline(term2_raw, stopset, stemmer)

    if len(t1_list) > 1 or len(t2_list) > 1:
        raise QueryError("Query terms must tokenize into single words (no hyphens).")

    t1 = t1_list[0] if t1_list else ""
    t2 = t2_list[0] if t2_list else ""

    p1 = index.get(t1, [])
    p2 = index.get(t2, [])

    docids = merge_and(p1, p2) if conn == "AND" else merge_or(p1, p2)
    return t1, conn, t2, docids

def format_result_line(docids):
    # Requirements specify we just write a file containing the docid list
    return ",".join(str(d) for d in docids) + "\n" if docids else "\n"

def main():
    parser = argparse.ArgumentParser(description="Boolean search for IR67 index.")
    parser.add_argument("query", nargs="?", help="e.g. 'aerodynamic AND experimental'")
    parser.add_argument("--batch", metavar="FILE", help="batch file, one query per line")
    parser.add_argument("-o", "--output", metavar="FILE", default=config.RESULTS_PATH)
    parser.add_argument("--index", metavar="FILE", default=config.INDEX_PATH)
    args = parser.parse_args()

    if not args.query and not args.batch:
        parser.error("provide a query string or --batch FILE")

    index, vocab_size, max_docid = load_index(args.index)
    stopset = load_stopwords(config.STOPWORDS_PATH)
    stemmer = PorterStemmer()

    if args.batch:
        with open(args.batch, encoding="utf-8") as f:
            queries = [line.strip() for line in f if line.strip()]
    else:
        queries = [args.query]

    lines = []
    for q in queries:
        try:
            _, _, _, docids = run_query(q, index, stopset, stemmer)
            result = format_result_line(docids)
            lines.append(result)
            print(result, end="")
        except QueryError as e:
            err_msg = f"QUERY ERROR: {e}\n"
            lines.append(err_msg)
            print(err_msg, end="")

    with open(args.output, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Results written to {args.output}")

if __name__ == "__main__":
    main()
