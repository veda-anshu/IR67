# Cranfield Boolean IR System — Writeup

Programming Assignment I: Preprocessing, Indexing, Boolean Search
Group: **IR67** *(rename in `IR67_config.py` — every output filename is auto-prefixed from there)*

Language: **Python 3** (standard library only — no external packages required
to run; the Porter stemmer is vendored in `IR67_porter_stemmer.py` so there is
nothing to `pip install`).

---

## 1. Files

| File | Purpose |
|---|---|
| `IR67_config.py` | Group name + shared input/output paths. Edit `GROUP_NAME` here. |
| `IR67_porter_stemmer.py` | Standalone Porter (1980) stemming algorithm implementation. |
| `IR67_preprocess.py` | Tokenization, normalization, stopword removal, stemming; writes `GROUP_processed.all`. |
| `IR67_index.py` | Builds the inverted index; writes `GROUP_cran.index`. |
| `IR67_search.py` | Two-term Boolean AND/OR search over the index. |
| `queries.txt` | Sample demo queries (batch-mode input for `IR67_search.py`). |
| `data/cran.all`, `data/stopwords.txt` | Input corpus and stopword list (as supplied). |
| `output/` | All generated files land here. |

## 2. How to run

```bash
# 1) edit IR67_config.py: set GROUP_NAME = "<your actual group name>"

# 2) preprocessing -> output/GROUP_processed.all
python3 IR67_preprocess.py

# 3) indexing -> output/GROUP_cran.index
python3 IR67_index.py

# 4) Boolean search
python3 IR67_search.py "aerodynamic AND experimental"          # single query
python3 IR67_search.py "flow OR pressure" -o results.txt        # custom output file
python3 IR67_search.py --batch queries.txt -o output/GROUP_results.txt   # batch mode
```

Each script only depends on the previous stage's output file plus
`IR67_config.py` — there is no shared server/process, so stages can be re-run
independently at any time.

## 3. Preprocessing methodology

### 3.1 Parsing `cran.all`
Each document begins with a `.I <docid>` line and contains `.T` (title),
`.A` (author), `.B` (bibliography) and `.W` (abstract) sections. As
instructed, only `.T` and `.W` are processed; `.A`/`.B` are parsed (to
find section boundaries) and discarded. Title and abstract text are
concatenated into one string per document before preprocessing.



### 3.2 The four required functions

Implemented as four separate functions in `IR67_preprocess.py`, run in this
order by the shared `apply_pipeline()` entry point:

1. **`tokenize(text)`** — regex `[A-Za-z0-9]+`: a token is a maximal run of
   letters/digits. Punctuation, whitespace, hyphens, slashes and the
   `/italic/` markers used in the corpus all act as separators (e.g.
   `"boundary-layer-control"` → `boundary`, `layer`, `control`).
2. **`normalize(tokens)`** — case-folds to lowercase and strips
   accents/diacritics (Unicode NFKD, drop combining marks), dropping any
   token that becomes empty.
3. **`remove_stopwords(tokens, stopset)`** — drops any token present in `stopwords.txt`.
4. **`stem(tokens, stemmer)`** — Porter stemming via `IR67_porter_stemmer.py`.

**Pipeline order:** `tokenize → normalize → remove_stopwords → stem`.
Stopword removal is done *before* stemming purely for efficiency — running
the stemmer on ~40% of raw tokens that are common function words
(`the`, `of`, `and`, ...) which will be discarded anyway is wasted work.
This does not change correctness: the same `apply_pipeline()` function is
used for both documents (in `IR67_preprocess.py`) and queries (in `IR67_search.py`),
so document terms and query terms are guaranteed to be stemmed/normalized
identically regardless of ordering choice.

### 3.3 Porter stemmer
`IR67_porter_stemmer.py` implements Porter's 1980 algorithm ("An algorithm for
suffix stripping", *Program* 14.3: 130–137), run in `ORIGINAL_ALGORITHM`
mode (faithful to the original paper, as opposed to later community
extensions). It was validated against 75 canonical input/output pairs from
Porter's own published test vocabulary before being wired into the
pipeline — see the validation script output below.

```
75/75 canonical Porter test vectors passed (ORIGINAL_ALGORITHM mode)
```

### 3.4 Output format (`GROUP_processed.all`)
```
.I 1
.S
experiment investig aerodynam wing slipstream ...
.I 2
.S
...
```

## 4. Indexing methodology (`IR67_index.py`)

`build_index()` does a single linear pass over the processed file,
accumulating `term -> set(docid)` (a `set` per term so repeated
occurrences of a term within one document only record that docid once —
this is a Boolean index, so only presence/absence matters). Postings sets
are then sorted into ascending lists and the whole index is written with
terms in lexicographic order:

```
<vocab_size>, <max_docid>
aerodynamic 1,10,11
experimental 1,7,9,21,27
...
```

## 5. Boolean search methodology (`IR67_search.py`)

* The raw query (`"term1 AND term2"` / `"term1 OR term2"`, connective
  case-insensitive) is parsed, and **each query term is run through the
  identical `apply_pipeline()`** used on documents, so `"Aerodynamics"` in
  a query correctly matches the indexed stem `aerodynam`.
* **Efficient set operations (bonus):** postings lists in the index are
  already sorted ascending, so AND/OR are computed with the standard
  linear merge algorithm (two pointers walking both lists once) rather
  than, e.g., converting to Python sets — `O(len(p1) + len(p2))` time,
  `O(1)` extra space beyond the output list. Implemented as `merge_and()`
  / `merge_or()`.
* Correctness of `merge_and`/`merge_or` was checked against Python's
  brute-force `set` intersection/union over 2000 randomly sampled term
  pairs from the real index (0 mismatches), plus explicit edge cases
  (empty postings list, identical lists, disjoint lists).
* A query term absent from the vocabulary (or a query word that is itself
  a stopword, e.g. `"the"`) resolves to an empty postings list rather than
  raising an error — the search simply returns no matches for that side.
* Both single-query and `--batch <file>` (one query per line) modes are
  supported; results are written to a file and also echoed to stdout.

## 6. Sample results (demo queries, `queries.txt`)

Official test queries will be substituted in when released; the pipeline
already runs end-to-end correctly on these representative queries:

| Query | Processed | # matches |
|---|---|---|
| aerodynamic AND experimental | aerodynam AND experiment | 49 |
| flow OR pressure | flow OR pressur | 931 |
| boundary AND layer | boundari AND layer | 370 |
| shock AND wave | shock AND wave | 149 |
| heat AND transfer | heat AND transfer | 190 |
| supersonic OR subsonic | superson OR subson | 318 |
| wing AND flow | wing AND flow | 121 |
| turbulent OR laminar | turbul OR laminar | 304 |

Full docid lists for each are in `output/GROUP_results.txt`.

## 7. Corpus statistics

* Documents: 1400 (docids 1–1400, contiguous)
* Vocabulary size after preprocessing: 4616 terms
* Total token occurrences across corpus: 136218 (avg ~97.3 tokens/doc)
* Total postings (Σ postings-list length): 80393
* End-to-end runtime on the full collection: preprocessing ≈ 2.3s,
  indexing ≈ 0.1s, a single search ≈ 0.05s (single core, no external
  dependencies).

## 8. Complexity summary

| Stage | Time complexity |
|---|---|
| Tokenization + normalization | O(total characters in corpus) |
| Stopword removal | O(total tokens), O(1) average lookup per token (hash set) |
| Stemming | O(total tokens × avg word length) |
| Indexing | O(total tokens) to build, O(V log V) to sort terms for output (V = vocab size) |
| Boolean search (AND/OR) | O(len(postings₁) + len(postings₂)) via merge, after O(1) average-case hash lookup of each term |
