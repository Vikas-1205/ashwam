import argparse
import json
import re
import sys
import unicodedata
from typing import Dict, Any, List, Set, Tuple, Optional

class LanguageDetector:
    """
    Deterministic language detector for short journaling snippets.
    
    Supports: English (en), Hindi (hi), Hinglish (hinglish), and Mixed (mixed).
    Strategy: 
      1. Unicode range detection for Script (Latin vs Devanagari).
      2. Lexicon-based matching + Fuzzy Logic + N-gram patterns for Language.
    """

    # Common English stopwords (expanded for better coverage)
    EN_STOPWORDS: Set[str] = {
        'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'of', 'for', 'it', 'this', 'that',
        'with', 'as', 'was', 'were', 'be', 'are', 'i', 'you', 'he', 'she', 'we', 'they', 'my', 'your',
        'his', 'her', 'our', 'their', 'but', 'or', 'so', 'if', 'then', 'than', 'just', 'very', 'really',
        'now', 'not', 'no', 'yes', 'can', 'will', 'do', 'did', 'done', 'has', 'have', 'had', 'go', 'going',
        'went', 'get', 'got', 'me', 'him', 'us', 'them', 'am', 'feeling', 'feel', 'felt', 'today', 'tomorrow',
        'yesterday', 'morning', 'evening', 'night', 'after', 'before', 'stress', 'tired', 'pain', 'energy',
        'work', 'meeting', 'meetings', 'mood', 'cramps', 'low', 'okay', 'better', 'good', 'bad', 'lunch',
        'dinner', 'breakfast', 'slept', 'sleep', 'bed', 'early', 'late', 'gym', 'body', 'heavy', 'garam' # garam is not english, mistake in list? removing garam.
    }
    # Removing 'garam' from EN_STOPWORDS as it was a mistake while typing.
    if 'garam' in EN_STOPWORDS: EN_STOPWORDS.remove('garam')

    # Common Hindi words in Roman script (Hinglish)
    HI_LATIN_STOPWORDS: Set[str] = {
        'hai', 'hain', 'ho', 'hun', 'hu', 'ki', 'ka', 'ke', 'ko', 'mein', 'me', 'aur', 'tatha', 'evam',
        'se', 'ne', 'par', 'liye', 'kya', 'kyun', 'kab', 'kahan', 'kaise', 'main', 'hum', 'tum', 'aap',
        'ye', 'woh', 'yeh', 'wo', 'tha', 'thi', 'ga', 'gi', 'ge', 'raha', 'rahi', 'rahe',
        'bhi', 'hi', 'mat', 'wala', 'wale', 'wali', 'karna', 'kar', 'kiya', 'gaya', 'gayi', 'gaye',
        'aa', 'aaj', 'kal', 'ab', 'jab', 'tab', 'kabhi', 'abhi', 'nahi', 'nahin', 'na', 'h', 'n',
        'bohot', 'bahut', 'thoda', 'zyada', 'kam', 'kyu', 'mujhe', 'mera', 'meri', 'mere', 'uska',
        'unki', 'unka', 'unhe', 'use', 'isso', 'iske', 'unke', 'jaisa', 'waisa', 'kaisa',
        'yaar', 'bhai', 'dost', 'dimag', 'garam', 'khana', 'peena', 'sone', 'uthna', 'subah', 'scam', # scam is english
        'lag', 'raha', 'rahi', 'rahe', 'dard', 'thakan', 'bukhar', 'sardard'
    }
    HI_LATIN_STOPWORDS.add('mein') # ensuring mein is there
    # Removing 'scam'
    if 'scam' in HI_LATIN_STOPWORDS: HI_LATIN_STOPWORDS.remove('scam')
    # Removing 'the' and 'me' as they are too common in English and cause overlap
    if 'the' in HI_LATIN_STOPWORDS: HI_LATIN_STOPWORDS.remove('the')
    if 'me' in HI_LATIN_STOPWORDS: HI_LATIN_STOPWORDS.remove('me')

    # Devanagari range
    DEVANAGARI_RANGE: Tuple[int, int] = (0x0900, 0x097F)

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Main entry point for language detection.
        
        Args:
            text: Input string snippet.
            
        Returns:
            Dictionary containing 'primary_language', 'script', 'confidence', 'evidence'.
        """
        if not text:
            return {
                "id": None,
                "primary_language": "unknown",
                "script": "other",
                "confidence": 0.0,
                "evidence": {"msg": "empty input"}
            }

        # 1. Script Detection
        counts = self._count_scripts(text)
        script_label = self._determine_script(counts, len(text))
        
        # 2. Language Detection
        result = self._determine_language(text, script_label, counts)
        
        return result

    def _count_scripts(self, text: str) -> Dict[str, int]:
        """Counts characters in Latin vs Devanagari ranges."""
        counts = {'latin': 0, 'devanagari': 0, 'other': 0, 'total': 0}
        for char in text:
            if char.isspace():
                continue
            
            cp = ord(char)
            counts['total'] += 1
            if 0x0041 <= cp <= 0x005A or 0x0061 <= cp <= 0x007A:
                counts['latin'] += 1
            elif self.DEVANAGARI_RANGE[0] <= cp <= self.DEVANAGARI_RANGE[1]:
                counts['devanagari'] += 1
            elif unicodedata.category(char).startswith('P') or unicodedata.category(char).startswith('N') or unicodedata.category(char).startswith('S'):
                # Punctuation/Numbers tracked as 'other' to avoid skewing small samples
                counts['other'] += 1
            else:
                counts['other'] += 1
        return counts

    def _determine_script(self, counts: Dict[str, int], text_len: int) -> str:
        """Determines the dominant script or 'mixed' based on counts."""
        if counts['total'] == 0:
            return "other"
            
        lat_ratio = counts['latin'] / counts['total']
        dev_ratio = counts['devanagari'] / counts['total']
        
        # If significant presence of both (>2 chars to avoid noise)
        if counts['latin'] > 0 and counts['devanagari'] > 0:
             if counts['latin'] >= 2 and counts['devanagari'] >= 2:
                 return "mixed"
        
        if dev_ratio > lat_ratio and dev_ratio > 0.1:
            return "devanagari"
        if lat_ratio > dev_ratio and lat_ratio > 0.1:
            return "latin"
        
        return "other"

    def _determine_language(self, text: str, script: str, counts: Dict[str, int]) -> Dict[str, Any]:
        """
        Routing logic based on script.
        Devanagari -> Hindi
        Latin -> Needs deeper analysis (English vs Hinglish)
        """
        evidence = {
            "n_tokens": 0,
            "script_counts": counts
        }
        
        if script == "devanagari":
            # High confidence if decent length
            conf = 0.9 if counts['devanagari'] > 3 else 0.5
            return {
                "primary_language": "hi",
                "script": "devanagari",
                "confidence": conf,
                "evidence": evidence
            }

        if script == "mixed":
            return {
                "primary_language": "mixed",
                "script": "mixed",
                "confidence": 0.95,
                "evidence": evidence
            }
            
        if script == "latin":
            return self._analyze_latin_text(text, evidence)
            
        # fallback for other/unknown script
        return {
            "primary_language": "unknown",
            "script": "other",
            "confidence": 0.0,
            "evidence": evidence
        }

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        """Calculates Levenshtein edit distance between two strings."""
        if len(s1) < len(s2):
            return LanguageDetector._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def _analyze_latin_text(self, text: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes Latin script text to distinguish English vs Hinglish vs Mixed.
        Uses:
          - Stopword token matching
          - Fuzzy matching (Levenshtein)
          - N-gram pattern matching
        """
        # Tokenize (simple word boundary)
        tokens = [t.lower() for t in re.findall(r"\b\w+\b", text)]
        evidence['n_tokens'] = len(tokens)
        
        if not tokens:
            return {
                "primary_language": "unknown",
                "script": "latin",
                "confidence": 0.0,
                "evidence": evidence
            }
            
        en_hits = 0
        hi_hits = 0
        
        for t in tokens:
            # Exact match check first (fast O(1))
            if t in self.EN_STOPWORDS:
                en_hits += 1
                continue # If it's English, assume it's not Hindi for simplicity
            
            if t in self.HI_LATIN_STOPWORDS:
                hi_hits += 1
                continue

            # Fuzzy match for Hinglish words (slower but Robust)
            # Only if token length > 2 to avoid false positives on short words
            if len(t) > 2:
                found_fuzzy = False
                for sw in self.HI_LATIN_STOPWORDS:
                    # heuristic: only check words of similar length
                    if abs(len(token := t) - len(sw)) > 2: # optimization
                         continue
                    
                    dist = self._levenshtein(t, sw)
                    # Allow dist 1 for short words (3-5 chars), dist 2 for long (>5)
                    threshold = 1 if len(sw) <= 5 else 2
                    
                    if dist <= threshold:
                        hi_hits += 1
                        found_fuzzy = True
                        break # Count only once
                if found_fuzzy:
                    continue
        
        evidence['en_hits'] = en_hits
        evidence['hi_hits'] = hi_hits
        
        total_hits = en_hits + hi_hits
        
        # If very short and no hits
        if total_hits == 0:
            if len(tokens) <= 2:
                return {
                    "primary_language": "unknown",
                    "script": "latin",
                    "confidence": 0.1,
                    "evidence": evidence
                }
            
            return {
                "primary_language": "unknown",
                "script": "latin",
                "confidence": 0.2,
                "evidence": evidence
            }

        en_ratio = en_hits / len(tokens)
        hi_ratio = hi_hits / len(tokens)
        
        evidence['en_ratio'] = round(en_ratio, 2)
        evidence['hi_ratio'] = round(hi_ratio, 2)
        
        # Decision Logic
        
        # Strong Hinglish signal (Hindi grammar markers are distinct)
        if hi_hits >= en_hits and hi_hits > 0:
            conf = 0.5 + min(hi_ratio, 0.5)
            # Boost confidence for fuzzy matches if they were found?
            return {
                "primary_language": "hinglish",
                "script": "latin",
                "confidence": round(conf, 2),
                "evidence": evidence
            }
            
        # Strong English signal
        if en_hits > hi_hits:
            # Check for Mixed Code-Switching (significant presence of both)
            if en_hits >= 2 and hi_hits >= 2:
                conf = 0.8
                return {
                    "primary_language": "mixed",
                    "script": "latin",
                    "confidence": conf,
                    "evidence": evidence
                }
            
            conf = 0.5 + min(en_ratio, 0.5)
            if hi_hits == 0:
                 return {
                    "primary_language": "en",
                    "script": "latin",
                    "confidence": round(conf, 2),
                    "evidence": evidence
                }
            else:
                return {
                    "primary_language": "en",
                    "script": "latin",
                    "confidence": round(conf, 2),
                    "evidence": evidence
                }

        # N-gram Analysis fallback
        # 2-grams to catch patterns like 'ki wajah'
        ngrams_2 = zip(tokens, tokens[1:])
        hinglish_patterns_2 = {('ki', 'wajah'), ('wajah', 'se'), ('ka', 'matlab'), ('ho', 'gaya')}
        
        for bg in ngrams_2:
             if bg in hinglish_patterns_2:
                 return {
                    "primary_language": "hinglish",
                    "script": "latin",
                    "confidence": 0.85,
                    "evidence": {"msg": "ngram pattern match", **evidence}
                }

        return {
            "primary_language": "unknown",
            "script": "latin",
            "confidence": 0.3,
            "evidence": evidence
        }

def start():
    parser = argparse.ArgumentParser(description="Language Detector")
    parser.add_argument('--in_file', dest='in_file', required=True, help='Input JSONL file')
    parser.add_argument('--out_file', dest='out_file', required=True, help='Output JSONL file')
    
    args = parser.parse_args()
    
    detector = LanguageDetector()
    
    with open(args.in_file, 'r', encoding='utf-8') as f_in, open(args.out_file, 'w', encoding='utf-8') as f_out:
        for line in f_in:
            if not line.strip():
                continue
            data = json.loads(line)
            text_id = data.get('id')
            text = data.get('text', '')
            
            result = detector.detect(text)
            result['id'] = text_id
            
            f_out.write(json.dumps(result, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    start()
