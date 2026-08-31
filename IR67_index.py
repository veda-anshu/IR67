from collections import defaultdict
import IR67_config as config

def parse_processed_file(path):
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
    index = defaultdict(set)
    max_docid = 0
    
    for doc_id, tokens in docs:
        max_docid = max(max_docid, doc_id)
        for tok in tokens:
            index[tok].add(doc_id)

    # Convert sets to sorted lists for the postings
    index = {term: sorted(postings) for term, postings in index.items()}
    return index, max_docid

def write_index(index, max_docid, path):
    vocab_size = len(index)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{vocab_size}, {max_docid}\n")
        for term in sorted(index.keys()):
            postings = ",".join(str(d) for d in index[term])
            f.write(f"{term} {postings}\n")

def main():
    docs = parse_processed_file(config.PROCESSED_PATH)
    print(f"Loaded {len(docs)} documents from {config.PROCESSED_PATH}")

    index, max_docid = build_index(docs)
    write_index(index, max_docid, config.INDEX_PATH)

    print(f"Wrote index to {config.INDEX_PATH}")
    print(f"Vocabulary size: {len(index)}")
    print(f"Max docid: {max_docid}")
    
    total_postings = sum(len(v) for v in index.values())
    print(f"Total postings: {total_postings}")

if __name__ == "__main__":
    main()
