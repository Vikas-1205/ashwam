# Language Detection Logic

A deterministic, lightweight language and script detector for short journaling snippets (English, Hindi, Hinglish, Mixed) designed for messy, code-switched text.

## Usage

### Run Language Detection
```bash
# Using the convenience script
./run.sh

# Or manually
python3 src/lang_detect.py --in_file texts.jsonl --out_file lang.jsonl
```

### Run Tests
```bash
python3 -m unittest discover tests
```

## Approach

This tool handles short, noisy text (3-30 words) by using a multi-stage deterministic approach that prioritizes signal over strict grammar:

1.  **Script Detection**:
    - Scans Unicode ranges to classify text as `latin`, `devanagari`, `mixed` (if both are present > 2 chars), or `other`.
    - Short/numeric texts fall into `other` or `latin` based on character composition.

2.  **Language Detection** (for Latin script):
    - Uses curated stopword lists for English (`EN_STOPWORDS`) and Hinglish (`HI_LATIN_STOPWORDS`).
    - **Fuzzy Matching**: Uses Levenshtein distance (edit distance <= 1 or 2) to catch spelling variations (e.g., `muje` for `mujhe`, `nhi` for `nahi`).
    - **N-gram Analysis**: Detects common Hinglish bigrams (e.g., `ki wajah`, `ho gaya`) to identify language even if individual words are ambiguous.
    - **Scoring**: Counts "hits" (exact + fuzzy) and pattern matches.
    - **Decision Rules**:
        - **Hinglish**: High presence of Hindi markers (lexicon matches + n-gram patterns).
        - **English**: Dominance of English stopwords with minimal Hindi markers.
        - **Mixed**: Significant distinct signals from both languages.
        - **Unknown**: Very short text or texts with no recognizable stopwords.

3.  **Ambiguity Handling**:
    - Common short words that overlap (e.g., `me`, `the`) are excluded from the Hindi Latin list.
    - Levenshtein checks are length-thresholded to avoid false positives on very short words.

## Tradeoffs & Design Decisions

-   **Deterministic Lists vs. ML**: Used specific lexicons + fuzzy logic.
    -   *Why?* Fast, predictable, zero-dependency (standard lib only).
    -   *Tradeoff*: Harder to generalize to unseen vocab, but Levenshtein mitigates typo issues.

## Confidence Score

-   **1.0**: Strong signal (high ratio of known tokens).
-   **0.9-0.95**: Clear script signal (Devanagari) or strong Mixed signal.
-   **0.5-0.8**: Weaker signal (few hits, short text).
-   **0.0-0.3**: Unknown or very short text (< 3 tokens) with no hits.
