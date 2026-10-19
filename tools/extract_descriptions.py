"""Extract descriptions through validated 16-bit pointer tables."""
import json,struct
from textcodec import ROOT,decode
TABLES=[
 ('item_description',256,0x1000,[('HAR/MENUMENU.BIN',0xe8bb,0x6400),('BTL/FF6_BTL.BIN',0x2c648,0x2d878)]),
 ('spell_description',54,0x400,[('HAR/MENUMENU.BIN',0xc14b,0xeebb),('BTL/FF6_BTL.BIN',0x2cf08,0x2c848)]),
 ('esper_description',27,0x18a,[('HAR/MENUMENU.BIN',0xecfb,0xf2bb),('BTL/FF6_BTL.BIN',0x1ed40,0x2cc48)])
]
def string_end(data,offset):
    p=offset
    while p<len(data):
        c=data[p];p+=1
        if c in [2,0x12,0x1c,0x1d,0x1e,0x1f]:p+=1
        if c==0:return p
    raise ValueError('Missing terminator')
def main():
    rows=[]
    for category,count,capacity,copies in TABLES:
        file,table,base=copies[0];data=(ROOT/'work/extracted'/file).read_bytes()
        for i,relative in enumerate(struct.unpack_from('<'+'H'*count,data,table)):
            if relative>=capacity:raise ValueError((category,i,relative))
            offset=base+relative;end=string_end(data,offset);raw=data[offset:end];occ=[]
            if end>base+capacity:raise ValueError('Description exceeds table extent')
            for f,t,b in copies:
                other=(ROOT/'work/extracted'/f).read_bytes();rel=struct.unpack_from('<H',other,t+i*2)[0]
                if rel!=relative or other[b+rel:b+rel+len(raw)]!=raw:raise ValueError('Description copy differs')
                occ.append({'file':f,'offset':b+rel,'length':len(raw),'pointer_offset':t+i*2,'base':b,'capacity':capacity})
            rows.append({'id':len(rows),'category':category,'index':i,'encoding':'nullTerminated','offset':offset,'source':decode(raw,'nullTerminated',stop=True),'original_hex':raw.hex(),'occurrences':occ})
    (ROOT/'analysis/descriptions-original.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')
    print('Extracted and cross-checked',len(rows),'descriptions')
if __name__=='__main__':main()
