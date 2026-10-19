from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
DEF=json.loads((ROOT/'references/ff6tools/ff6/ff6j-sfc.json').read_text('utf-8'))

def table(kind='dialog'):
    return {bytes.fromhex(k[2:]):v for name in DEF['textEncoding'][kind]['charTable'] for k,v in DEF['charTable'][name]['char'].items()}

def decode(data,kind='dialog',stop=False):
    tbl=table(kind);out=[];p=0
    while p<len(data):
        code=data[p:p+1];p+=1
        if 0x1c<=code[0]<=0x1f and p<len(data):code+=data[p:p+1];p+=1
        val=tbl.get(code,'{'+code.hex().upper()+'}')
        if code==b'\0':
            if stop:break
            val='[END]\n'
        elif val=='\\n':val='\n'
        elif val=='\\pad':val='□'
        elif val.endswith('['):
            val='{'+val[1:]+(f'{data[p]:02X}' if p<len(data) else '??')+']}'
            p+=1
        elif val.startswith('\\') and len(code)==2 and any('\u3040'<=c<='\u30ff' or '\uff66'<=c<='\uff9f' for c in val[1:]):val=val[1:]
        elif val.startswith('\\'): val='{'+val[1:]+'}'
        out.append(val)
    return ''.join(out)

def encode_original(text,kind='dialog'):
    rev={v:k for k,v in table(kind).items()}
    out=bytearray();p=0
    while p<len(text):
        choices=[s for s in rev if text.startswith(s,p)]
        if not choices:raise ValueError(text[p:p+20])
        s=max(choices,key=len);out+=rev[s];p+=len(s)
    return bytes(out)

if __name__=='__main__':
    for file,offset,size in [('NAR/NAR_BIN3.BIN',0,2200),('NAR/NAR_BIN.BIN',465000,5000),('HAR/MENUMENU.BIN',25000,8000),('BTL/FF6_BTL.BIN',178000,8000)]:
        b=(ROOT/'work/extracted'/file).read_bytes()
        print('\n',file,hex(offset));print(decode(b[offset:offset+size]))
