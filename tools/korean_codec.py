"""Korean glyph allocation for FF6's existing single/double-byte text decoder."""
from pathlib import Path
import json,re,collections,unicodedata,struct
from PIL import Image,ImageDraw,ImageFont
from textcodec import ROOT,table,DEF
JP=re.compile('[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')
CONTROL=re.compile(r'\{[^{}]+\}')

def normalize(text):
    text=unicodedata.normalize('NFKC',text).replace('\r','')
    text=re.sub(r'[^\S\n]',' ',text)
    return text.replace('–','ー').replace('—','ー').replace('〜','～')

def original_fixed():
    original=table('dialog');fixed={};counts=collections.Counter()
    for code,v in original.items():
        c=v[1:] if v.startswith('\\') and len(code)==2 else v
        if len(c)==1 and not JP.search(c) and c not in '{}\\':
            fixed[unicodedata.normalize('NFKC',c)]=code
    fixed[' ']=b'\xff';fixed['\n']=b'\x01'
    fixed.update({'"':b'\xd0',"'":b'\xd0','～':b'\xc5','ー':b'\xc5','…':b'\xd8'})
    return fixed

def allocate(texts,reserved_indices=()):
    original=table('dialog');fixed=original_fixed();counts=collections.Counter();visible=set()
    for t in texts:
        chars=CONTROL.sub('',normalize(t));visible.update(chars)
        counts.update(c for c in chars if c not in fixed)
    reserved=set(fixed.values())
    singles=[k for k,v in original.items() if len(k)==1 and 0x20<=k[0]<0xd9 and len(v)==1 and JP.search(v) and k not in reserved]
    doubles=[bytes((p,i)) for p in range(0x1c,0x20) for i in range(256) if bytes((p,i)) not in reserved]
    free=[k for k in singles+doubles if font_index(k) not in reserved_indices and font_index(k)<1152]
    if len(counts)>len(free):raise ValueError(f'Font capacity exceeded {len(counts)}>{len(free)}')
    assigned={c:free[i] for i,(c,_) in enumerate(counts.most_common())}
    # The last 96 glyphs hold player names. Move the few original punctuation
    # glyphs used here into free lower slots, preserving their exact pixels.
    replacements=iter(k for k in free[len(assigned):] if font_index(k)<1152)
    for c in sorted(visible):
        if c in fixed and (font_index(fixed[c]) in reserved_indices or len(fixed[c])==2 and font_index(fixed[c])>=1085):
            fixed[c]=next(replacements)
    if any(font_index(v)>=1152 for v in assigned.values()):raise ValueError('Dialogue/name font allocation overflow')
    return fixed|assigned,assigned

def fixed_relocations(mapping,assigned):
    return [(c,old,mapping[c]) for c,old in original_fixed().items()
            if c in mapping and c not in assigned and mapping[c]!=old]

def encode(text,mapping):
    original=table('dialog');ctrl={v[1:]:k for k,v in original.items() if v.startswith('\\') and len(k)==1}
    out=bytearray()
    for part in re.split(r'(\{[^{}]+\})',normalize(text)):
        if not part:continue
        if part.startswith('{'):
            name=part[1:-1]
            if name in ctrl:out+=ctrl[name]
            elif re.fullmatch(r'(pause|key|t)\[[0-9A-F]{2}\]',name):
                cmd,arg=name[:-1].split('[');out+=ctrl[cmd+'[']+bytes.fromhex(arg)
            elif re.fullmatch('[0-9A-F]{2}',name):out+=bytes.fromhex(name)
            else:raise ValueError('Unknown control '+part)
        else:
            for c in part:
                if c not in mapping:raise ValueError(f'Unmapped {c!r}')
                out+=mapping[c]
    return bytes(out)

def font_index(code):
    return code[0]-0x20 if len(code)==1 else 224+((code[0]-0x1c)<<8)+code[1]

def raster(c,small=False):
    font=ImageFont.truetype(str(ROOT/'assets/fonts'/('Galmuri7.ttf' if small else 'Galmuri9.ttf')),8 if small else 10)
    im=Image.new('1',(8,8) if small else (12,11))
    # The small native SPRT starts at texture row +1. Keep row zero blank.
    ImageDraw.Draw(im).text((0,0) if small else (1,-1),c,font=font,fill=1,stroke_width=0)
    return im

def build_large(original,assigned,mapping=None):
    font=bytearray(original)
    for c,code in assigned.items():
        glyph=raster(c);data=bytearray()
        for y in range(11):
            row=sum((1<<(11-x)) for x in range(12) if glyph.getpixel((x,y)))
            data+=struct.pack('<H',row)
        at=font_index(code)*22;font[at:at+22]=data
    if mapping:
        for _,old,new in fixed_relocations(mapping,assigned):
            src=font_index(old)*22;dest=font_index(new)*22
            font[dest:dest+22]=original[src:src+22]
    if len(font)!=len(original):raise ValueError('Font size changed')
    return font

def save_allocation(mapping,assigned):
    p=ROOT/'work/korean_encoding.json'
    p.write_text(json.dumps({'font':'Galmuri9 10px, 12x11 cell','small_font_required':'Galmuri7 8px, 8x8 cell','space':{'character':'U+0020','large_advance':6,'small_advance_required':4},'mapping':{k:v.hex() for k,v in mapping.items()},'replaced':{k:v.hex() for k,v in assigned.items()}},ensure_ascii=False,indent=2)+'\n','utf-8')

if __name__=='__main__':
    d=json.loads((ROOT/'translations/dialogue.ko.json').read_text('utf-8'))
    override=json.loads((ROOT/'translations/manual_dialogue.json').read_text('utf-8'))
    texts=[override.get(k,v['translation']) for k,v in d.items()]
    mapping,assigned=allocate(texts);save_allocation(mapping,assigned)
    print('Allocated',len(assigned),'glyphs; single-byte',sum(len(v)==1 for v in assigned.values()))
    print('Encoded bytes',sum(len(encode(t,mapping))+1 for t in texts))
    original=(ROOT/'work/extracted/NAR/NAR_BIN.BIN').read_bytes()[0x64bd0:0x6b710]
    font=build_large(original,assigned);(ROOT/'work/korean_large_font.bin').write_bytes(font)
    im=Image.new('RGB',(800,200),'#101840');draw=ImageDraw.Draw(im)
    for row,(text,small) in enumerate([('작은 글씨: 갈무리7  전투  마법  도구  저장',True),('마대전 때 얼어붙었다는, 천 년 전의 환수 말이지…',False)]):
        for i,c in enumerate(text):
            gl=raster(c,small).convert('RGB');scale=3
            im.paste(gl.resize((gl.width*scale,gl.height*scale),Image.Resampling.NEAREST),(10+i*gl.width*scale,25+row*90))
    im.save(ROOT/'analysis/korean_font_preview.png')
