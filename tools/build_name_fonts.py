"""Build independently decompressible Galmuri name-font blocks.

Each modern Hangul syllable has its large 12x11 glyph and Galmuri7 8x8
glyph together. Native name-entry integration can load one 7680-byte block
instead of keeping all 11172 syllables decompressed in PSX RAM.
"""
from pathlib import Path
import json,struct
from PIL import Image,ImageDraw,ImageFont
from textcodec import ROOT
from pac import compress,decompress

def glyph_record(c,large,small):
    a=Image.new('1',(12,11));ImageDraw.Draw(a).text((1,-1),c,font=large,fill=1)
    b=Image.new('1',(8,8));ImageDraw.Draw(b).text((0,0),c,font=small,fill=1)
    raw=bytearray()
    for y in range(11):raw+=struct.pack('<H',sum(1<<(11-x) for x in range(12) if a.getpixel((x,y))))
    for y in range(8):raw.append(sum(1<<(7-x) for x in range(8) if b.getpixel((x,y))))
    return bytes(raw)

def main():
    large=ImageFont.truetype(str(ROOT/'assets/fonts/Galmuri9.ttf'),10)
    small=ImageFont.truetype(str(ROOT/'assets/fonts/Galmuri7.ttf'),8)
    blocks=[];index=[];cursor=24+44*8
    for block in range(44):
        first=block*256;count=min(256,11172-first)
        raw=b''.join(glyph_record(chr(0xac00+i),large,small) for i in range(first,first+count))
        packed=compress(raw)
        assert decompress(packed)[0]==raw
        index.append({'first_syllable_index':first,'count':count,'offset':cursor,'compressed_bytes':len(packed),'decompressed_bytes':len(raw)})
        blocks.append(packed);cursor+=len(packed)
    header=b'KRNAMEF1'+struct.pack('<4I',0xac00,11172,256,30)
    offsets=b''.join(struct.pack('<2I',x['offset'],x['compressed_bytes']) for x in index)
    out=ROOT/'work/korean-name-fonts.bin';out.write_bytes(header+offsets+b''.join(blocks))
    jamo=list(dict.fromkeys('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣㄳㄵㄶㄺㄻㄼㄽㄾㄿㅀㅄ'))
    (ROOT/'work/korean-name-jamo.bin').write_bytes(b''.join(glyph_record(c,large,small) for c in jamo))
    (ROOT/'work/korean-name-ascii.bin').write_bytes(b''.join(glyph_record(chr(c),large,small) for c in range(32,127)))
    report={'status':'font resources prepared; not yet integrated into native editor','syllables':11172,'record_bytes':30,'maximum_scratch_bytes':7680,'total_bytes':out.stat().st_size,'large_font':'Galmuri9','small_font':'Galmuri7','jamo':jamo,'blocks':index}
    (ROOT/'analysis/name-font-blocks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print({k:v for k,v in report.items() if k not in ('blocks','jamo')},flush=True)

if __name__=='__main__':main()
