"""Create the editor's immutable metrics and package a standalone Windows EXE."""
import json,re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from textcodec import ROOT, table, decode
from korean_codec import original_fixed, font_index


def prepare():
    folder = ROOT/'assets/text-manager'; folder.mkdir(exist_ok=True)
    nar = (ROOT/'work/extracted/NAR/NAR_BIN.BIN').read_bytes()
    widths, bitmaps = {}, {}
    for c, code in original_fixed().items():
        if c in (' ', '\n'): continue
        i = font_index(code)
        widths[c] = nar[0x646d0+i+32]
        bitmaps[c] = list(struct.unpack_from('<11H', nar, 0x64bd0+i*22))
    icons = sorted({v[1:] for code,v in table('smallText').items()
                    if v.startswith('\\') and len(code)==1 and code[0]>=0x20})
    fixed=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    translated=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    variable_pixels={'gp':120,'monster_number':36,'slot2':216,'slot3':216,'slot4':216}
    for category in ['item','spell','monster','attack','command']:
        strings=[re.sub(r'\{[^{}]+\}','',translated[str(row['id'])]['translation']) for row in fixed if row['category']==category]
        variable_pixels[category]=max((sum(6 if c==' ' else widths.get(c,12) for c in text) for text in strings),default=120)
    payload = {'widths': widths, 'original_bitmaps': bitmaps, 'icons': ['{'+name+'}' for name in icons], 'variable_pixels':variable_pixels,
               'source': 'Original PSX NAR width table and glyph pixels; translated large advances 12, small 8, spaces 6/4.'}
    (folder/'text-metrics.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), 'utf-8')
    for font in ['Galmuri7.ttf', 'Galmuri9.ttf', 'Galmuri-OFL.txt']:
        shutil.copy2(ROOT/'assets/fonts'/font, folder/font)


def main():
    prepare()
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--name', 'FF6KoreanTextManager', '--distpath', str(ROOT),
        '--workpath', str(ROOT/'work/text-manager-pyinstaller'), '--specpath', str(ROOT/'work'),
        '--add-data', str(ROOT/'assets/text-manager')+';.', str(ROOT/'tools/text_manager.py')], check=True)


if __name__ == '__main__': main()
