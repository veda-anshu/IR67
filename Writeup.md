# Cranfield Boolean IR System — Writeup

**Programming Assignment I: Preprocessing, Indexing, Boolean Search**  
**Group:** IR67 *(Note: You can easily rename the group in `IR67_config.py`, and all output filenames will update automatically).*

**Language:** Python 3. We stuck strictly to the standard library so there’s absolutely nothing you need to `pip install`. We also vendored the Porter stemmer directly into `IR67_porter_stemmer.py` to keep things self-contained.

---

### 1. Project Structure

Here is a quick rundown of how we organized the code:

*   **`IR67_config.py`**: This holds the group name and all the shared paths for inputs and outputs.
*   **`IR67_porter_stemmer.py`**: A standalone implementation of the classic 1980 Porter stemming algorithm. 
*   **`IR67_preprocess.py`**: Handles all the tokenization, normalization, stopword removal, and stemming. It outputs everything into `IR67_processed.all`.
*   **`IR67_index.py`**: Takes the processed file and builds the inverted index, saving it as `IR67_cran.index`.
*   **`IR67_search.py`**: Runs our two-term Boolean AND/OR searches over the index.
*   **`queries.txt`**: A few sample queries we used for batch testing.
*   **`data/`**: The folder containing the supplied corpus (`cran.all`) and stopword list.
*   **`output/`**: Where all the generated files get dumped.

### 2. How to run the code

Since we didn't use a shared server or background process, you can run each script independently whenever you want, as long as the previous stage's output file is there. 

First, make sure your group name is set in `IR67_config.py`. Then, you can run the pipeline like this:

```bash
# 1. Run preprocessing (generates output/IR67_processed.all)
python IR67_preprocess.py

# 2. Build the index (generates output/IR67_cran.index)
python IR67_index.py

# 3. Try out the Boolean search
python IR67_search.py "aerodynamic AND experimental"          # For a single query
python IR67_search.py "flow OR pressure" -o results.txt        # To save to a custom file
python IR67_search.py --batch queries.txt -o output/IR67_results.txt   # To run our batch tests
```

### 3. Preprocessing Approach

**Parsing the Corpus:**  
Each document in `cran.all` starts with a `.I <docid>` tag, followed by title (`.T`), author (`.A`), bibliography (`.B`), and abstract (`.W`) sections. As requested, we only care about the titles and abstracts, so we use the author and bibliography tags just to know where sections begin and end, and then discard them. We then mash the title and abstract text together into one string per document before running it through the pipeline.

*A quick note on the dataset:* While parsing, we noticed a weird quirk in the corpus. Three documents (doc IDs 240, 576, and 578) have lines directly inside their abstracts that look exactly like section tags (like a stray `.A`). Because we built a strict tag-boundary parser (which is generally the safest way to do this), it treats these as actual section breaks. This means the abstracts for those 3 documents (which is about 0.2% of the collection) get very slightly truncated. We figured it was better to document this pre-existing noise rather than writing hacky, hardcoded workarounds to swallow it.

**The Four Required Functions:**  
We implemented the steps as four separate functions inside `IR67_preprocess.py`, managed by a main `apply_pipeline()` function. They run in this specific order:

1.  **Tokenization**: We used a simple regex (`[A-Za-z0-9]+`) to define a token as any continuous run of letters or digits. Everything else—punctuation, spaces, hyphens, and those `/italic/` markers in the text—acts as a separator. So, `"boundary-layer-control"` cleanly splits into `boundary`, `layer`, and `control`.
2.  **Normalization**: We push everything to lowercase and strip out accents and diacritics using Unicode NFKD. If a token becomes completely empty after this, we just drop it.
3.  **Stopword Removal**: We filter out any tokens that match the `stopwords.txt` file. Interestingly, we noticed four words in the supplied file (`herself`, `himself`, `itself`, `myself`) were corrupted by an encoding issue (a weird quote character replaced the "lf"). We patched those specific typos on load so the words actually get removed as intended!
4.  **Stemming**: Finally, we run the remaining tokens through our Porter stemmer.

*Why this order?* We intentionally placed stopword removal *before* stemming purely to save processing time. Running the stemmer on thousands of "the"s and "and"s just to throw them away immediately after seemed like a waste of CPU cycles. This doesn't affect the accuracy at all, since we use the exact same pipeline for both documents and search queries.

**The Porter Stemmer:**  
Our `IR67_porter_stemmer.py` is a faithful implementation of Porter's original 1980 paper. We ran it against 75 canonical input/output test cases provided by Porter himself to make sure it was bulletproof before wiring it into the pipeline, and it passed all of them.

### 4. Indexing Strategy

Our `build_index()` function makes a single, linear pass over the processed text. It builds a mapping of terms to a `set` of doc IDs. We used a set because this is a Boolean index—we only care *if* a word appears in a document, not how many times it appears. Once the pass is done, we sort the sets into ascending lists and write the whole dictionary out to `IR67_cran.index` in alphabetical order, formatted exactly as requested.

### 5. Boolean Search & Optimization

When you feed a query like `"term1 AND term2"` to `IR67_search.py`, it parses the terms and runs them through the exact same preprocessing pipeline used for the documents. This ensures that a query for "Aerodynamics" perfectly matches the indexed stem "aerodynam".

**Efficiency tweaks:** For the actual search, we wanted to make it as efficient as possible. Since our index already stores postings lists in ascending order, we implemented a standard two-pointer linear merge algorithm for both AND and OR operations. Instead of converting them to Python sets, we just walk both lists simultaneously. This gives us a time complexity of `O(len(list1) + len(list2))` and requires barely any extra memory. 

We heavily tested these merge functions against standard brute-force Python set intersections using thousands of random term pairs from the index to guarantee they were flawless. Also, if you search for a term that isn't in the vocabulary (or search for a stopword), the script handles it gracefully by treating it as an empty list rather than crashing.

### 6. Results and Corpus Stats

We tested the pipeline end-to-end using the sample queries in `queries.txt`. You can find the full lists of matching document IDs in `output/IR67_results.txt`. Here’s a quick summary of the matches we got:

*   **aerodynamic AND experimental** (49 matches)
*   **flow OR pressure** (931 matches)
*   **boundary AND layer** (370 matches)
*   **shock AND wave** (149 matches)
*   **heat AND transfer** (190 matches)
*   **supersonic OR subsonic** (318 matches)
*   **wing AND flow** (121 matches)
*   **turbulent OR laminar** (304 matches)

**Some quick stats on the processed corpus:**
*   **Documents indexed:** 1400 
*   **Final vocabulary size:** 4,616 unique terms
*   **Total tokens:** 136,218 (averaging about 97 tokens per doc)
*   **Total postings:** 80,393

Performance-wise, it's pretty snappy. On a single core, preprocessing takes about 2.3 seconds, indexing takes 0.1 seconds, and a search query resolves in roughly 0.05 seconds.
