"""Extract verified fixed-size Japanese name tables, recording all identical copies."""
import json,re,hashlib
from textcodec import ROOT,decode

TABLES=[
 ('character',64,6,'smallText',[('NAR/NAR_BIN.BIN',0x71c50),('HAR/MENUMENU.BIN',0x9d00),('BTL/FF6_BTL.BIN',0x2bc28)]),
 ('spell',54,5,'smallText',[('NAR/NAR_BIN.BIN',0x7463c),('HAR/MENUMENU.BIN',0x7400),('BTL/FF6_BTL.BIN',0x2bda8)]),
 ('esper',27,8,'bigText',[('NAR/NAR_BIN.BIN',0x7474a),('HAR/MENUMENU.BIN',0x750e),('BTL/FF6_BTL.BIN',0x2beb6)]),
 ('attack',175,8,'bigText',[('NAR/NAR_BIN.BIN',0x74822),('HAR/MENUMENU.BIN',0x75e6),('BTL/FF6_BTL.BIN',0x2bf8e)]),
 ('esper_attack',27,9,'bigText',[('NAR/NAR_BIN.BIN',0x74d9a),('HAR/MENUMENU.BIN',0x7b5e),('BTL/FF6_BTL.BIN',0x2c506)]),
 ('command',32,6,'smallText',[('HAR/MENUMENU.BIN',0x1041b),('BTL/FF6_BTL.BIN',0x2ce48)]),
 ('item',256,9,'smallText',[('NAR/NAR_BIN.BIN',0x73cfc),('HAR/MENUMENU.BIN',0xc1bb),('BTL/FF6_BTL.BIN',0x2cf78)]),
 ('monster',384,8,'smallText',[('BTL/FF6_BTL.BIN',0x1b700),('HAR/MENUMENU.BIN',0x112db)]),
 ('monster_attack',384,8,'bigText',[('BTL/FF6_BTL.BIN',0x1c300),('HAR/MENUMENU.BIN',0x11edb)])
]
def main():
    cache={p:(ROOT/'work/extracted'/p).read_bytes() for _,_,_,_,copies in TABLES for p,_ in copies}
    rows=[];issues=[]
    for group,count,size,kind,copies in TABLES:
        for i in range(count):
            primary,base=copies[0];data=cache[primary][base+i*size:base+(i+1)*size]
            source=decode(data.rstrip(b'\xff'),kind)
            occurrences=[]
            for file,offset in copies:
                raw=cache[file][offset+i*size:offset+(i+1)*size]
                if raw==data:occurrences.append({'file':file,'offset':offset+i*size,'length':size})
                else:issues.append({'category':group,'index':i,'file':file,'error':'Copy differs; excluded from automatic insertion'})
            rows.append({'id':len(rows),'category':group,'index':i,'encoding':kind,'offset':base+i*size,'source':source,'original_hex':data.hex(),'occurrences':occurrences})
    (ROOT/'analysis/fixed-catalog-original.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n','utf-8')
    (ROOT/'analysis/fixed-catalog-validation.json').write_text(json.dumps({'entries':len(rows),'copy_mismatches':issues},ensure_ascii=False,indent=2)+'\n','utf-8')
    print('Extracted',len(rows),'entries;',len(issues),'copy discrepancies')
    print('Discrepancies by category',__import__('collections').Counter(x['category'] for x in issues))
if __name__=='__main__':main()
