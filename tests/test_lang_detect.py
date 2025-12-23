import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from lang_detect import LanguageDetector

class TestLanguageDetector(unittest.TestCase):
    def setUp(self):
        self.detector = LanguageDetector()

    def test_english_simple(self):
        text = "The quick brown fox jumps over the lazy dog."
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'en')
        self.assertEqual(result['script'], 'latin')

    def test_hindi_devanagari(self):
        text = "नमस्ते दुनिया"
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'hi')
        self.assertEqual(result['script'], 'devanagari')

    def test_hinglish(self):
        text = "Aaj mausam bahut accha hai."
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'hinglish')
        self.assertEqual(result['script'], 'latin')

    def test_mixed_script(self):
        text = "Hello duniya नमस्ते"
        result = self.detector.detect(text)
        self.assertEqual(result['script'], 'mixed')
        self.assertEqual(result['primary_language'], 'mixed')

    def test_short_english(self):
        text = "No cramps today"
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'en')

    def test_short_hinglish(self):
        text = "haan yaar"
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'hinglish')

    def test_unknown_numeric(self):
        text = "12345 !!!"
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'unknown')

    def test_code_switching_hinglish(self):
        # "Aaj headache hai" -> Hinglish
        text = "Aaj headache hai"
        result = self.detector.detect(text)
        # Expect hinglish because 'Aaj' (Hi) and 'hai' (Hi) are 2 hits, 'headache' (En) is 1 hit (if in list, or just ratio)
        # Actually 'headache' is not in my EN_STOPWORDS list, so it won't count as En hit.
        # But 'Aaj' and 'hai' are there. So mostly Hi logic.
        self.assertEqual(result['primary_language'], 'hinglish')

    def test_code_switching_mixed(self):
        # "Work was intense. Aaj dimag garam hai."
        text = "Work was intense. Aaj dimag garam hai."
        result = self.detector.detect(text)
        self.assertIn(result['primary_language'], ['hinglish', 'mixed'])

    def test_fuzzy_hinglish(self):
        # "Muje" instead of "Mujhe" -> should be detected as Hinglish via fuzzy match
        text = "Muje bahut anxiety ho rahi hai"
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'hinglish')
        # Check evidence to ensure it was counted as a hit
        self.assertTrue(result['evidence']['hi_hits'] >= 2) # Muje, hai

    def test_fuzzy_variation(self):
        # "ni" -> "na" or "nahi"? "ni" is short, might need threshold 1.
        # "ni" is length 2. The code skips fuzzy for len <= 2.
        # Let's try "nhi" (len 3), match with "nahi" (len 4). Dist 1.
        text = "Wo aayega nhi"
        result = self.detector.detect(text)
        self.assertEqual(result['primary_language'], 'hinglish')


if __name__ == '__main__':
    unittest.main()
