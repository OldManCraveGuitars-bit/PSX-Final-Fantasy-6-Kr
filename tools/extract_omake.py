"""Extract all 578 bonus-menu strings using the original texture and font."""
import json,struct
from textcodec import ROOT,table
from korean_codec import font_index
from extract_psx_ui import CHARACTERS
from bytelz import decompress

def texture(folder):
    raw=decompress((ROOT/'work/extracted'/folder/'ALLTIM.BIN').read_bytes())[0]
    p=8+struct.unpack_from('<I',raw,8)[0];size,x,y,w,h=struct.unpack_from('<I4H',raw,p)
    return bytes(c for b in raw[p+12:p+size] for c in (b&15,b>>4)),w*4

def bitmap(pixels,stride,x,y):
    return tuple(sum(1<<(11-i) for i in range(12) if pixels[(y+j)*stride+x+i]==3) for j in range(11))

def main():
    pixels,stride=texture('OMAKEDIR');deo,dstride=texture('DEODIR')
    known={bitmap(deo,dstride,256+i%21*12,i//21*12):c for i,c in enumerate(CHARACTERS)}
    font=(ROOT/'work/extracted/NAR/NAR_BIN.BIN').read_bytes()[0x64bd0:0x6b710]
    for code,c in table('dialog').items():
        if c.startswith('\\') and len(code)==2:c=c[1:]
        index=font_index(code)
        if len(c)==1 and 0<=index<1248:known.setdefault(struct.unpack_from('<11H',font,index*22),c)
    mapping={}
    for i in range(882):
        n=i%441;k=bitmap(pixels,stride,256+i//441*256+n%21*12,n//21*12)
        if k in known:mapping[i]=known[k]
    exact=len(mapping)
    mapping.update({int(k):v for k,v in json.loads((ROOT/'translations/omake-font-overrides.json').read_text('utf8')).items()})
    data=(ROOT/'work/decompressed/OMAKEDIR/OMAKE.PAC').read_bytes();rows=[]
    for identifier in range(578):
        pointer=0x2b930+identifier*4;start=struct.unpack_from('<I',data,pointer)[0]-0x800c8000
        if not 0x21648<=start<0x2b930:raise ValueError('Bonus text pointer outside original pool')
        p=start;glyphs=[];source=[]
        while True:
            c=struct.unpack_from('<H',data,p)[0];p+=2
            if c==0xffff:break
            glyphs.append(c)
            source.append('\n' if c==0x8000 else mapping[c])
        rows.append({'id':identifier,'source':''.join(source).rstrip('\n'),'offset':start,'pointer_offset':pointer,
            'length':p-start,'original_hex':data[start:p].hex(),'glyphs':glyphs})
    (ROOT/'analysis/omake-original.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'analysis/omake-font.json').write_text(json.dumps({'mapping':mapping,'exact_bitmap_matches':exact,
        'manually_labeled_glyphs':882-exact,'glyph_size':[12,12],'pages':2,'glyphs_per_page':441,
        'text_pool':[0x21648,0x2b930],'records':578},ensure_ascii=False,indent=2)+'\n','utf8')
    print('Extracted',len(rows),'bonus-menu records; all glyphs resolved.')
if __name__=='__main__':main()
