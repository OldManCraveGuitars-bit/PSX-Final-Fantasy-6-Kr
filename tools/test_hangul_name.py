"""Interaction checks for the controller composition core."""
import unittest
from hangul_name import HangulName

def compose(keys):
    n=HangulName()
    for k in keys:assert n.feed(k)
    return n

class CompositionTests(unittest.TestCase):
    def test_syllables_and_compounds(self):
        for keys,want in [('ㅎㅏㄴㄱㅡㄹ','한글'),('ㅌㅣㄴㅏ','티나'),('ㄱㅗㅏ','과'),('ㄱㅗㅏㅣㄴ','괜'),('ㄷㅜㅓㅣ','뒈'),('ㄱㅏㅂㅅ','값'),('ㄱㄱㅏ','까'),('ㄷㅏㄹㄱ','닭')]:
            with self.subTest(keys=keys):self.assertEqual(compose(keys).text,want)
    def test_final_moves_to_next_syllable(self):
        for keys,want in [('ㄱㅏㄴㅏ','가나'),('ㄱㅏㅂㅅㅣ','갑시'),('ㄱㅏㄱㄱㅏ','가까')]:
            self.assertEqual(compose(keys).text,want)
    def test_granular_backspace(self):
        n=compose('ㅎㅏㄴㄱㅡㄹ')
        for expected in ['한그','한ㄱ','한','하','ㅎ','']:
            n.backspace();self.assertEqual(n.text,expected)
    def test_compound_backspace(self):
        n=compose('ㄱㅗㅏㅣㄴ')
        for expected in ['괘','과','고','ㄱ','']:
            n.backspace();self.assertEqual(n.text,expected)
    def test_limit_is_atomic(self):
        n=HangulName(limit=1)
        for k in 'ㄱㅏㄴ':self.assertTrue(n.feed(k))
        self.assertFalse(n.feed('ㅏ'));self.assertEqual(n.text,'간')
    def test_space_and_empty_name(self):
        n=compose('ㅅㅐ\u3000ㄱㅔㅇㅣㅁ')
        self.assertEqual(n.confirm(),'새 게임')
        with self.assertRaises(ValueError):HangulName().confirm()

if __name__=='__main__':unittest.main()
