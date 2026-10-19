"""Extract the two remaining, validated native battle message pointer tables."""
import json,struct
from textcodec import ROOT
from battle_textcodec import decode,string_end

TABLES=[('battle_dialogue',0x14400,0x11a00,0x2a00,0xd200),
        ('attack_message',0x3940,0x1f628,0x513,0xf000)]

def main():
    data=(ROOT/'work/extracted/BTL/FF6_BTL.BIN').read_bytes();rows=[]
    for category,table,base,capacity,bias in TABLES:
        for i in range(256):
            relative=struct.unpack_from('<H',data,table+i*2)[0]-bias
            if not 0<=relative<capacity:raise ValueError((category,i,relative))
            start=base+relative;end=string_end(data,start)
            if end>base+capacity:raise ValueError('Battle message crosses verified pool')
            raw=data[start:end]
            rows.append({'id':len(rows),'category':category,'index':i,'encoding':'nullTerminated','offset':start,
                'source':decode(raw),'original_hex':raw.hex(),
                'occurrences':[{'file':'BTL/FF6_BTL.BIN','pointer_offset':table+i*2,'pointer_bias':bias,
                    'base':base,'capacity':capacity,'offset':start,'length':len(raw)}]})
    target=ROOT/'analysis/battle-messages-original.json'
    target.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf8')
    print('Validated',len(rows),'battle messages')

if __name__=='__main__':main()
