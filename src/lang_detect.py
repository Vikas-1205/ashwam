import argparse
import json
import re
import sys
import unicodedata

class LanguageDetector:
    # Common English stopwords (expanded for better coverage)
    EN_STOPWORDS = {
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
    EN_STOPWORDS.remove('garam') if 'garam' in EN_STOPWORDS else None

    # Common Hindi words in Roman script (Hinglish)
    HI_LATIN_STOPWORDS = {
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
    DEVANAGARI_RANGE = (0x0900, 0x097F)

    def detect(self, text):
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

    def _count_scripts(self, text):
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
                # Punctuation, Numbers, Symbols - treat as neutral or track separately if needed
                # For now, adding to 'other' but we might exclude them from script decision if they dominate?
                # Actually, let's track them but not let them sway 'latin' vs 'devanagari' too much.
                # Let's count them as other for now.
                counts['other'] += 1
            else:
                counts['other'] += 1
        return counts

    def _determine_script(self, counts, text_len):
        if counts['total'] == 0:
            return "other"
            
        lat_ratio = counts['latin'] / counts['total']
        dev_ratio = counts['devanagari'] / counts['total']
        
        # If significant presence of both
        if counts['latin'] > 0 and counts['devanagari'] > 0:
             # Just presence of one char shouldn't trigger mixed script if it's noise?
             # Prompt: "Don’t rely only on presence of one Devanagari character"
             # Let's say if we have at least 2 chars of each or > 5%?
             if counts['latin'] >= 2 and counts['devanagari'] >= 2:
                 return "mixed"
        
        if dev_ratio > lat_ratio and dev_ratio > 0.1:
            return "devanagari"
        if lat_ratio > dev_ratio and lat_ratio > 0.1:
            return "latin"
        
        return "other"

    def _determine_language(self, text, script, counts):
        evidence = {
            "n_tokens": 0,
            "script_counts": counts
        }
        
        if script == "devanagari":
            # Almost certainly Hindi for this dataset
            # Determine confidence based on length/noise
            conf = 0.9 if counts['devanagari'] > 3 else 0.5
            return {
                "primary_language": "hi",
                "script": "devanagari",
                "confidence": conf,
                "evidence": evidence
            }

        if script == "mixed":
            # If script is mixed (Latin + Devanagari), language is 'mixed' by definition in prompt requirements?
            # Prompt: "mixed — meaningful mixture of English + Hindi OR mixture of Latin + Devanagari"
            return {
                "primary_language": "mixed",
                "script": "mixed",
                "confidence": 0.95,
                "evidence": evidence
            }
            
        if script == "latin":
            # Could be en, hinglish, mixed, or unknown
            return self._analyze_latin_text(text, evidence)
            
        # fallback for other/unknown script
        return {
            "primary_language": "unknown",
            "script": "other",
            "confidence": 0.0,
            "evidence": evidence
        }

    def _analyze_latin_text(self, text, evidence):
        # Tokenize
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
            if t in self.EN_STOPWORDS:
                en_hits += 1
            if t in self.HI_LATIN_STOPWORDS:
                hi_hits += 1
        
        evidence['en_hits'] = en_hits
        evidence['hi_hits'] = hi_hits
        
        total_hits = en_hits + hi_hits
        
        # If very short and no hits
        if total_hits == 0:
            # Check for generic English words that might not be in stopwords but are English
            # Hard to do without huge dict. 
            # If it's just "ok" or "123", might be unknown.
            # "ok" is often english. "haan" is hindi.
            # Let's add specific short text overrides or heuristic
            if len(tokens) <= 2:
                # Naive guess?
                return {
                    "primary_language": "unknown",
                    "script": "latin",
                    "confidence": 0.1,
                    "evidence": evidence
                }
            
            # If length is decent but no hits, low confidence unknown or default to En?
            # Prompt says "Don’t label everything unknown".
            # Synthetic dataset is English/Hindi context.
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
        
        # Strong Hinglish signal
        if hi_hits >= en_hits and hi_hits > 0:
            conf = 0.5 + min(hi_ratio, 0.5)
            return {
                "primary_language": "hinglish",
                "script": "latin",
                "confidence": round(conf, 2),
                "evidence": evidence
            }
            
        # Strong English signal
        if en_hits > hi_hits:
            # If we have some Hindi hits, might be mixed?
            # "Work was intense. Aaj dimag garam hai."
            # en_hits: Work(1), was(1), intense(0). Aaj(1_hi), dimag(1_hi), garam(1_hi), hai(1_hi). 
            # Oh, wait. My stopwords list for En doesn't have 'intense'.
            # My logic is: if hi_hits >= en_hits -> hinglish.
            # In "Work was intense...", hits might be En: [was]. Hi: [aaj, dimag, garam, hai]. 
            # So Hi count (4) > En count (1). -> Hinglish.
            # This seems correct for code-switching which flows into Hinglish.
            
            # What about mixed? "meaningful mixture of English + Hindi". 
            # Maybe if both counts are significant?
            # e.g. En hits > 2 AND Hi hits > 2?
            if en_hits >= 2 and hi_hits >= 2:
                conf = 0.8
                return {
                    "primary_language": "mixed",
                    "script": "latin",
                    "confidence": conf,
                    "evidence": evidence
                }
            
            conf = 0.5 + min(en_ratio, 0.5)
            # Check if it was purely English (hi_hits == 0)
            if hi_hits == 0:
                 return {
                    "primary_language": "en",
                    "script": "latin",
                    "confidence": round(conf, 2),
                    "evidence": evidence
                }
            else:
                # Mostly English but some Hindi?
                # "Lunch: dal chawal." -> En: [lunch]. Hi: [dal, chawal] (if in dict). 
                # If 'dal', 'chawal' not in dict, then Hi hits = 0.
                # If Hi hits > 0 but En is dominant?
                # "I ate dal." -> En: [i, ate]. Hi: [dal].
                # Maybe stick to 'en' if Hi signal is weak, or 'hinglish' if grammar is Hindi?
                # The class 'hinglish' usually implies Hindi grammar.
                # The class 'mixed' implies sentences of both.
                
                return {
                    "primary_language": "en",
                    "script": "latin",
                    "confidence": round(conf, 2),
                    "evidence": evidence
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
