"""Fit Korean dialogue through the existing 23-entry MTE expansion table."""
import collections,re,json,struct
from korean_codec import *

def choose_dictionary(texts,mapping,limit=23,capacity=140):
    segments=[s for t in texts for s in CONTROL.split(t) if s and not s.startswith('{')]
    # Boundaries and private replacement markers cannot occur inside an entry.
    parts=[]
    for s in segments:parts.extend(re.split(r'[\n\ue000-\uefff]',s))
    selected=[];used=0
    for index in range(limit):
        counts=collections.Counter()
        for s in parts:
            for n in range(2,6):
                counts.update(s[i:i+n] for i in range(len(s)-n+1) if '\ue000' not in s[i:i+n] and not any(0xe000<=ord(c)<=0xefff for c in s[i:i+n]))
        ranked=[]
        for phrase,n in counts.items():
            if n<8:continue
            raw=encode(phrase,mapping);cost=(len(raw)+1+3)&~3
            if len(raw)>9:continue
            if used+cost+4*(limit-index-1)>capacity:continue
            savings=n*(len(raw)-1)
            ranked.append((savings,phrase,cost,raw))
        if not ranked:break
        _,phrase,cost,raw=max(ranked,key=lambda x:x[0])
        selected.append((phrase,raw));used+=cost
        marker=chr(0xe000+index)
        parts=[s.replace(phrase,marker) for s in parts]
    return selected

def compress_text(text,mapping,dictionary):
    for i,(phrase,raw) in enumerate(dictionary):
        text=re.sub(r'(\{[^{}]+\})|'+re.escape(phrase),lambda m:m[1] if m[1] else chr(0xe000+i),text)
    out=bytearray()
    for s in re.split('([\ue000-\uefff])',text):
        if len(s)==1 and 0xe000<=ord(s)<=0xefff:out.append(0xd9+ord(s)-0xe000)
        else:out+=encode(s,mapping)
    return bytes(out)

def patch_table(data,dictionary):
    if len(dictionary)!=23:raise ValueError('Expected all 23 MTE entries')
    out=bytearray(data);start=0x56174;end=0x56200;cursor=start
    if data[0x56170:0x5617c]!=bytes.fromhex('c7c700001ff91ff800000000'):raise ValueError('MTE original guard failed')
    out[start:end]=bytes(end-start)
    for i,(phrase,raw) in enumerate(dictionary):
        size=(len(raw)+1+3)&~3
        if cursor+size>end:raise ValueError('MTE table overflow')
        out[cursor:cursor+len(raw)]=raw
        struct.pack_into('<I',out,0x56204+i*4,0x800c8000+cursor)
        cursor+=size
    return out

if __name__=='__main__':
    rows=json.loads((ROOT/'translations/dialogue.complete-draft.json').read_text('utf-8'));texts=[x['translation'] for x in rows]
    mapping,assigned=allocate(texts);save_allocation(mapping,assigned)
    dictionary=choose_dictionary(texts,mapping)
    size=sum(len(compress_text(t,mapping,dictionary))+1 for t in texts)
    report={'uncompressed_bytes':sum(len(encode(t,mapping))+1 for t in texts),'mte_bytes':size,'original_capacity':0x1afa0,'mte_table_bytes':sum((len(raw)+4)&~3 for _,raw in dictionary),'dictionary':[{ 'code':hex(0xd9+i),'text':p,'bytes':b.hex()} for i,(p,b) in enumerate(dictionary)]}
    (ROOT/'analysis/korean-mte-plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report,ensure_ascii=False))
