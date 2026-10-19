"""Shared native fixed-literal size rules, also bundled in the text editor."""
from functools import lru_cache
import unicodedata


@lru_cache(maxsize=1)
def kana_reverse():
    reverse={}
    for c in (bytes((i,)).decode('cp932') for i in range(0xa1,0xe0)):
        reverse[unicodedata.normalize('NFKC',c)]=c.encode('cp932')
        for mark in ['ﾞ','ﾟ']:
            normalized=unicodedata.normalize('NFKC',c+mark)
            if len(normalized)==1:reverse[normalized]=(c+mark).encode('cp932')
    return reverse


def old_kana(text):
    reverse=kana_reverse()
    return b''.join(bytes((ord(c),)) if ord(c)<128 else reverse[c] for c in text)


def label_capacity(source):
    return len(old_kana(source))+1


def encoded_size(text):
    # One native font-bank selector (%k/%K), byte glyph indices, NUL.
    # Visible printf controls such as %p remain in the stored literal.
    return len(text)+3
