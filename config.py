"""
config.py

Single place to set your group name and shared paths. Every script
(preprocess.py, index.py, search.py) imports GROUP_NAME from here, so
renaming your group only requires editing this one line before submission.
"""

import os

# ---- CHANGE THIS to your actual group name before submitting ----
GROUP_NAME = "IR67"

# ---- Input files ----
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CRAN_ALL_PATH = os.path.join(DATA_DIR, "cran.all.1400")
STOPWORDS_PATH = os.path.join(DATA_DIR, "stopwords.txt")

# ---- Output files (auto-prefixed with GROUP_NAME) ----
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
PROCESSED_PATH = os.path.join(OUTPUT_DIR, f"{GROUP_NAME}_processed.all")
INDEX_PATH = os.path.join(OUTPUT_DIR, f"{GROUP_NAME}_cran.index")
RESULTS_PATH = os.path.join(OUTPUT_DIR, f"{GROUP_NAME}_results.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)
