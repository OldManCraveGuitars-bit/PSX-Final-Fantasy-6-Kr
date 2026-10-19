"""Discover omitted kana literals and stage a complete editor import."""
import json,re
from textcodec import ROOT
from korean_codec import normalize
from omake_terms import glossary
from prepare_omake_small import key

def main():
    bank=json.loads((ROOT/'translations/omake-small.ko.json').read_text('utf8'))
    raw=(ROOT/'work/decompressed/OMAKEDIR/OMAKE.PAC').read_bytes()
    covered={p for r in bank['records'] for p in range(r['offset'],r['offset']+r['length'])}
    terms=glossary();terms.update({key('ベスト'):'최고',key('ヤリコミド'):'달성률'})
    ids={text:i for i,text in enumerate(bank['strings'])};added=[]
    for m in re.finditer(rb'%[kK][^\0]*',raw[:0x32f0]):
        if m.start() in covered or not re.search(rb'[\xa1-\xdf]',m[0]):continue
        source=m[0];out=bytearray();cursor=0;refs=[]
        for run in re.finditer(rb'[\xa1-\xdf]+(?:-[\xa1-\xdf]+)*-?|%[HRDU](?:%[HRDU])*',source):
            if run[0].startswith(b'%'):
                text=''.join({'H':'좌','R':'우','D':'하','U':'상'}[chr(c)] for c in run[0][1::2])
            else:text=terms[key(run[0].decode('cp932'))]
            if text not in ids:ids[text]=len(bank['strings']);bank['strings'].append(text)
            i=ids[text];out+=source[cursor:run.start()]+bytes((1+(i>>7),0x80+(i&127)));cursor=run.end();refs.append(i)
        out+=source[cursor:]+b'\0'
        row=dict(id=len(bank['records']),offset=m.start(),length=len(source)+1,
            source=normalize(source.decode('cp932')),raw_hex=source.hex(),patched_hex=out.hex(),reference_ids=refs)
        assert len(out)<=row['length']
        bank['records'].append(row);added.append(row['id'])
    target=ROOT/'work/bonus-small-import.json'
    target.write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n','utf8')
    print(dict(added_literals=len(added),strings=len(bank['strings']),total_literals=len(bank['records']),staging=str(target)))

if __name__=='__main__':main()
