# Language Detection Logic

A deterministic, lightweight language and script detector for short journaling snippets (English, Hindi, Hinglish, Mixed) designed for messy, code-switched text.

## Usage

### Run Language Detection
```bash
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
    - **Counts "hits"**: Matches tokens against these lists.
    - **Calculates ratios**: Relative frequency of language markers.
    - **Decision Rules**:
        - **Hinglish**: High presence of Hindi markers (e.g., `hai`, `mein`, `ka`, `ki`) even if English words are present. Since Hinglish code-switching often uses English nouns/adj with Hindi grammar, Hindi stopwords are strong predictors.
        - **English**: Dominance of English stopwords (`the`, `is`, `and`) with minimal Hindi markers.
        - **Mixed**: Significant distinct signals from both languages (e.g., full sentences of each).
        - **Unknown**: Very short text or texts with no recognizable stopwords.

3.  **Ambiguity Handling**:
    - Common short words that overlap (e.g., `me`, `the`) are excluded from the Hindi Latin list to prevent false positives for Hinglish in purely English text.

## Tradeoffs & Design Decisions

-   **Deterministic Lists vs. ML**: Used specific lexicons instead of statistical n-grams or ML models.
    -   *Why?* Fast, predictable, easy to debug, and requires no large dependencies. Ideal for "lightweight routing".
    -   *Tradeoff*: Requires manual maintenance of stopword lists. Might miss creative spellings not in the list (though common variations like `nahi`/`nahin` are included).
-   **"Hinglish" vs "English"**:
    -   The system favors `Hinglish` if Hindi grammatical markers are found, as "English vocabulary in Hindi grammar" is the definition of Hinglish here.
    -   Pure English requires a lack of strong Hindi signals.

## Confidence Score

-   **1.0**: Strong signal (high ratio of known tokens).
-   **0.9-0.95**: Clear script signal (Devanagari) or strong Mixed signal.
-   **0.5-0.8**: Weaker signal (few hits, short text).
-   **0.0-0.3**: Unknown or very short text (< 3 tokens) with no hits.

## Known Limitations

-   **Ambiguous short words**: Words like `to`, `is`, `on` are treated as English. If used in a Hindi context (rare spelling), they might trigger English detection.
-   **Spelling variations**: Extremely non-standard spellings of Hindi words might be missed if not in the list.
-   **Other Scripts**: Korean/Kanji etc. are detected as "other" script but `unknown` language unless English tokens are also present.
-   **Context**: Does not use sentence context (POS tagging), so "Headache hai" relies entirely on the tokens `headache` (En) vs `hai` (Hi).

## Future Improvements

-   **Levenshtein Distance**: Fuzzy matching for Hinglish words to handle more spelling variations (e.g., `mjhe`, `mujhey`).
-   **2-gram/3-gram analysis**: To detect common phrases (`ki wajah se`, `out of characters`) for better routing.
-   **Expanded Lexicons**: Add specialized domain terms (medical terms like 'gyno', 'period' as generally neutral or English).
