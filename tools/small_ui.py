"""First native Galmuri7 integration in the seven field-menu headings.

Only originally blank small-font slots are changed. The existing
Latin/digit/icon slots remain byte-identical.
"""
import json
from PIL import Image
from korean_codec import raster
from textcodec import ROOT,decode
from pac import compress,decompress

LABELS=[(0x631c0,'アイテム','도구'),(0x631c8,'とくしゅ','특수'),
        (0x631d0,'そうび','장비'),(0x631d8,'アクセサリ','액세서리'),
        (0x631e0,'ステータス','상태'),(0x631e8,'コンフィグ','설정'),
        (0x631f0,'セーブ','저장')]

def patch():
    menu=bytearray((ROOT/'work/extracted/HAR/MENUMENU.BIN').read_bytes())
    overlay=bytearray((ROOT/'work/decompressed/HAR/HARATA.PAC').read_bytes())
    chars=list(dict.fromkeys(''.join(x[2] for x in LABELS)))
    assert len(chars)==15
    slots=list(range(0xd8,0xe0))+[0xe1,0xe2,0xee,0xef,0xf8,0xf9,0xfa]
    mapping=dict(zip(chars,slots))
    for c,index in mapping.items():
        at=0xa400+index*16
        if any(menu[at:at+16]):raise ValueError('Small-font slot is occupied')
        glyph=raster(c,small=True)
        for y in range(8):
            fg=sum(1<<(7-x) for x in range(8) if glyph.getpixel((x,y)))
            prev=sum(1<<(7-x) for x in range(8) if y and glyph.getpixel((x,y-1)))
            shadow=(fg>>1)|prev|(prev>>1)
            menu[at+y*2]=fg|shadow
            menu[at+y*2+1]=fg
    for at,jp,ko in LABELS:
        source=bytes(overlay[at+2:at+8]).split(b'\0',1)[0]
        if decode(source,'smallText',stop=True)!=jp:raise ValueError(('Menu label guard',hex(at)))
        encoded=bytes(mapping[c] for c in ko)
        assert len(encoded)+1<=6
        overlay[at+2:at+8]=encoded+bytes(6-len(encoded))
    # Static title text can use precomposed 8-pixel tiles. This represents
    # the 4-pixel space exactly without altering the grid used by the menus.
    # The next glyph begins at x=12 after an 8-pixel character and 4-pixel gap.
    title='새 게임';canvas=Image.new('1',(32,8));x=0
    for c in title:
        if c==' ':x+=4
        else:canvas.paste(raster(c,small=True),(x,0));x+=8
    assert x==28
    title_codes=list(range(0xfb,0xff))
    for tile,index in enumerate(title_codes):
        at=0xa400+index*16
        if any(menu[at:at+16]):raise ValueError('Title font slot is occupied')
        for y in range(8):
            fg=sum(1<<(31-i) for i in range(32) if canvas.getpixel((i,y)))
            prev=sum(1<<(31-i) for i in range(32) if y and canvas.getpixel((i,y-1)))
            shadow=(fg>>1)|prev|(prev>>1)
            shift=(3-tile)*8
            menu[at+y*2]=((fg|shadow)>>shift)&255
            menu[at+y*2+1]=(fg>>shift)&255
    if decode(bytes(overlay[0x651d6:0x651dd]),'smallText',stop=True)!='ニューゲーム':raise ValueError('New-game label guard')
    overlay[0x651d6:0x651dd]=bytes(title_codes)+bytes(3)
    packed=compress(bytes(overlay))
    assert decompress(packed)[0]==overlay
    capacity=len((ROOT/'work/extracted/HAR/HARATA.PAC').read_bytes())
    if len(packed)>capacity:raise ValueError('Menu PAC capacity exceeded')
    report={'font':'Galmuri7','native_size':8,'cell':[8,8],'labels':len(LABELS)+1,'glyphs':len(mapping),'mapping':{k:hex(v) for k,v in mapping.items()},'small_spacing':{'advance':4,'method':'precomposed tiles for static text','verified_example':'새 게임','example_glyph_origins':[0,12,20]},'general_variable_width_small_renderer':'pending'}
    (ROOT/'analysis/small-ui-integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return {'HAR/MENUMENU.BIN':bytes(menu),'HAR/HARATA.PAC':packed+bytes(capacity-len(packed))}

if __name__=='__main__':
    changes=patch()
    print({k:len(v) for k,v in changes.items()})
