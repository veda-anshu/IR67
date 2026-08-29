import os

GROUP_NAME = "IR67"

# Input files
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CRAN_ALL_PATH = os.path.join(DATA_DIR, "cran.all.1400")
STOPWORDS_PATH = os.path.join(DATA_DIR, "stopwords.txt")

# Output files 
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
PROCESSED_PATH = os.path.join(OUTPUT_DIR, f"{GROUP_NAME}_processed.all")
INDEX_PATH = os.path.join(OUTPUT_DIR, f"{GROUP_NAME}_cran.index")
RESULTS_PATH = os.path.join(OUTPUT_DIR, f"{GROUP_NAME}_results.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)
