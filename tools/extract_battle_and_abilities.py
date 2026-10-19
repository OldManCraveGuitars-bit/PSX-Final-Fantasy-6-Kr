"""Export additional strings only from verified pointer tables."""
import json,struct
from textcodec import ROOT,decode
from extract_descriptions import string_end

TABLES=[
 ('monster_dialogue',256,0x1000,0xe400,[('BTL/FF6_BTL.BIN',0x1cf00,0x1d300)]),
 ('blitz_description',8,0x84,0,[('BTL/FF6_BTL.BIN',0x1ee9e,0x1eb00),('HAR/MENUMENU.BIN',0xee59,0xeabb)]),
 ('swdtech_description',8,0x7f,0,[('BTL/FF6_BTL.BIN',0x1eeae,0x1ec00),('HAR/MENUMENU.BIN',0xee69,0xebbb)]),
 ('lore_description',24,0x170,0,[('BTL/FF6_BTL.BIN',0x1ee3e,0x2e878),('HAR/MENUMENU.BIN',0xedf9,0x19cdb)])
]

def main():
    rows=[]
    for category,count,capacity,bias,copies in TABLES:
        file,table,base=copies[0];data=(ROOT/'work/extracted'/file).read_bytes()
        for i,pointer in enumerate(struct.unpack_from('<'+'H'*count,data,table)):
            relative=pointer-bias
            if not 0<=relative<capacity:raise ValueError((category,i,pointer))
            start=base+relative;end=string_end(data,start);raw=data[start:end]
            if end>base+capacity:raise ValueError('String crosses verified block')
            occurrences=[]
            for f,t,b in copies:
                other=(ROOT/'work/extracted'/f).read_bytes()
                if struct.unpack_from('<H',other,t+i*2)[0]!=pointer or other[b+relative:b+relative+len(raw)]!=raw:raise ValueError('Copy mismatch')
                occurrences.append({'file':f,'pointer_offset':t+i*2,'pointer_bias':bias,'base':b,'capacity':capacity,'offset':b+relative,'length':len(raw)})
            rows.append({'id':len(rows),'category':category,'index':i,'encoding':'nullTerminated','offset':start,'source':decode(raw,'nullTerminated',stop=True),'original_hex':raw.hex(),'occurrences':occurrences})
    (ROOT/'analysis/battle-abilities-original.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Validated',len(rows),'additional strings')

if __name__=='__main__':main()
