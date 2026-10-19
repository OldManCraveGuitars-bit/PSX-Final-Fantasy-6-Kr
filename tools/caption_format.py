"""Shared, dependency-free bounds for the native movie caption bank."""
import struct
import unicodedata

MOVIES = ('OPERA', 'OPEN', 'END')
BANK_SIZE = 4096
PAYLOAD_LIMIT = 0xfe0  # The last 32 bytes belong to the running callback.


def pack_caption_text(cues):
    if len(cues) > 64:
        raise ValueError('동영상 한 편의 자막은 최대 64개입니다.')
    texts = []
    last_end = -1
    for row in cues:
        start, end = row['start_frame'], row['end_frame']
        if type(start) is not int or type(end) is not int or not 0 <= start < end < 65536:
            raise ValueError('자막 시작·끝 프레임을 확인하세요.')
        if start < last_end:
            raise ValueError('같은 동영상의 자막 시간이 겹칩니다.')
        last_end = end
        text = unicodedata.normalize('NFKC', row['translation']).replace('\r', '')
        lines = text.split('\n')
        if not text or len(lines) > 2 or any(not line for line in lines):
            raise ValueError('자막은 빈 줄 없이 최대 두 줄입니다.')
        for line in lines:
            if len(line) > 43 or sum(6 if c == ' ' else 12 for c in line) > 304:
                raise ValueError('자막 한 줄은 304px/43자를 넘을 수 없습니다.')
        if any(ord(c) < 32 and c != '\n' or c.isspace() and c not in ' \n' for c in text):
            raise ValueError('자막에는 반각 공백과 줄바꿈만 사용할 수 있습니다.')
        texts.append(text)
    chars = sorted(set(''.join(texts)) - {' ', '\n'})
    if len(chars) > 252:
        raise ValueError('자막 글꼴 문자 수를 넘었습니다.')
    mapping = {c: i + 2 for i, c in enumerate(chars)}
    mapping.update({' ': 1, '\n': 254})
    data = bytearray(BANK_SIZE)
    data[:4] = bytes((len(cues), ord('K'), ord('R'), 2))
    cursor = 8 + len(cues) * 6
    for i, (row, text) in enumerate(zip(cues, texts)):
        struct.pack_into('<HHH', data, 8 + i * 6, row['start_frame'], row['end_frame'], cursor)
        encoded = bytes(mapping[c] for c in text) + b'\0'
        data[cursor:cursor + len(encoded)] = encoded
        cursor += len(encoded)
    font_offset = (cursor + 1) & ~1
    if font_offset + len(chars) * 24 > PAYLOAD_LIMIT:
        raise ValueError(f'동영상 자막 글꼴·문장 용량 초과: {font_offset + len(chars)*24}/{PAYLOAD_LIMIT}B')
    struct.pack_into('<HH', data, 4, font_offset, font_offset + len(chars) * 24)
    return data, mapping, font_offset


def validate_caption_rows(rows):
    if not isinstance(rows, list):
        raise ValueError('자막 JSON 목록이 필요합니다.')
    for row in rows:
        if row.get('movie', 'OPERA') not in MOVIES:
            raise ValueError('지원하는 동영상은 OPEN/OPERA입니다.')
        if not isinstance(row.get('source'), str) or not isinstance(row.get('translation'), str):
            raise ValueError('자막 원문과 번역은 문자열이어야 합니다.')
    for movie in MOVIES:
        pack_caption_text([r for r in rows if r.get('movie', 'OPERA') == movie])
