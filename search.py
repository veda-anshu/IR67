"""
search.py

Boolean retrieval over the index built by index.py. Supports exactly the
two-term queries the assignment asks for:

    <term1> AND <term2>
    <term1> OR  <term2>

The query is run through the *exact same* tokenize -> normalize ->
remove_stopwords -> stem pipeline used on the documents (imported
directly from preprocess.py) so that, e.g., "Aerodynamics" in a query
matches "aerodynamic" in the index.

Postings lists in the index file are already sorted ascending, so AND
(intersection) and OR (union) are computed with the standard linear
merge-based algorithm (Manning/Raghavan/Schütze, "Introduction to
Information Retrieval", ch. 1) rather than converting to Python sets:
each is a single left-to-right pass over both lists, O(len(p1)+len(p2))
comparisons, using no more memory than the two input lists plus the
output.

Usage:
    Single query, result written to config.RESULTS_PATH:
        python3 search.py "aerodynamic AND experimental"

    Single query, custom output file:
        python3 search.py "flow OR pressure" -o myresults.txt

    Batch mode - one query per line in a file, all results appended to
    one output file:
        python3 search.py --batch queries.txt -o results.txt
"""

import argparse
import sys

import config
from preprocess import apply_pipeline, load_stopwords
from porter_stemmer import PorterStemmer


# ---------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------
def load_index(path):
    """
    Load a <GROUP>_cran.index file into memory.
    Returns (index_dict, vocab_size, max_docid) where index_dict maps
    term -> sorted list of docids.
    """
    index = {}
    with open(path, encoding="utf-8") as f:
        header = f.readline().strip()
        vocab_size, max_docid = (int(x.strip()) for x in header.split(","))
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            term, postings_str = line.split(" ", 1)
            postings = [int(d) for d in postings_str.split(",") if d]
            index[term] = postings
    return index, vocab_size, max_docid


# ---------------------------------------------------------------------
# Merge-based set operations on sorted postings lists -- O(len(p1)+len(p2))
# ---------------------------------------------------------------------
def merge_and(p1, p2):
    """Sorted-list intersection via linear merge (two-pointer walk)."""
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
    """Sorted-list union via linear merge (two-pointer walk)."""
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


# ---------------------------------------------------------------------
# Query parsing + execution
# ---------------------------------------------------------------------
class QueryError(ValueError):
    pass


def parse_query(raw_query):
    """
    Parse "term1 AND term2" / "term1 OR term2" (case-insensitive
    connective) into (term1_raw, connective, term2_raw).
    """
    parts = raw_query.strip().split()
    if len(parts) != 3:
        raise QueryError(
            f"Expected exactly 'term1 AND|OR term2', got: {raw_query!r}"
        )
    term1, conn, term2 = parts
    conn_upper = conn.upper()
    if conn_upper not in ("AND", "OR"):
        raise QueryError(f"Connective must be AND or OR, got: {conn!r}")
    return term1, conn_upper, term2


def run_query(raw_query, index, stopset, stemmer):
    """
    Execute a single two-term Boolean query against the index.
    Returns (processed_term1, connective, processed_term2, sorted_docid_list).
    """
    term1_raw, conn, term2_raw = parse_query(raw_query)

    t1_list = apply_pipeline(term1_raw, stopset, stemmer)
    t2_list = apply_pipeline(term2_raw, stopset, stemmer)
    # A query word may itself be a stopword or stem to nothing (rare, but
    # handle gracefully rather than crashing on IndexError).
    t1 = t1_list[0] if t1_list else ""
    t2 = t2_list[0] if t2_list else ""

    p1 = index.get(t1, [])
    p2 = index.get(t2, [])

    docids = merge_and(p1, p2) if conn == "AND" else merge_or(p1, p2)
    return t1, conn, t2, docids


# ---------------------------------------------------------------------
# Main / CLI
# ---------------------------------------------------------------------
def format_result_line(raw_query, t1, conn, t2, docids):
    ids_str = ",".join(str(d) for d in docids) if docids else "(none)"
    return (
        f"QUERY: {raw_query}\n"
        f"  processed: {t1} {conn} {t2}\n"
        f"  matches ({len(docids)}): {ids_str}\n"
    )


def main():
    ap = argparse.ArgumentParser(description="Boolean search over the Cranfield index.")
    ap.add_argument("query", nargs="?", help="e.g. \"aerodynamic AND experimental\"")
    ap.add_argument("--batch", metavar="FILE", help="file with one query per line")
    ap.add_argument("-o", "--output", metavar="FILE", default=config.RESULTS_PATH,
                     help=f"output file (default: {config.RESULTS_PATH})")
    ap.add_argument("--index", metavar="FILE", default=config.INDEX_PATH,
                     help=f"index file to search (default: {config.INDEX_PATH})")
    args = ap.parse_args()

    if not args.query and not args.batch:
        ap.error("provide a query string or --batch FILE")

    index, vocab_size, max_docid = load_index(args.index)
    stopset = load_stopwords(config.STOPWORDS_PATH)
    stemmer = PorterStemmer()

    queries = []
    if args.batch:
        with open(args.batch, encoding="utf-8") as f:
            queries = [line.strip() for line in f if line.strip()]
    else:
        queries = [args.query]

    lines = []
    for q in queries:
        try:
            t1, conn, t2, docids = run_query(q, index, stopset, stemmer)
            lines.append(format_result_line(q, t1, conn, t2, docids))
            print(format_result_line(q, t1, conn, t2, docids), end="")
        except QueryError as e:
            msg = f"QUERY: {q}\n  ERROR: {e}\n"
            lines.append(msg)
            print(msg, end="")

    with open(args.output, "w", encoding="utf-8") as out:
        out.writelines(lines)
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    sys.exit(main())
