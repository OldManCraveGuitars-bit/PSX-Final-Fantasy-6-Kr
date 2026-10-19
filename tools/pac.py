"""FF6 PSX 16-bit LZ codec (verified against SLPM-86198 at 80041d00)."""
from pathlib import Path
import struct
from collections import defaultdict, deque

def decompress(data: bytes):
    size=struct.unpack_from('<I',data)[0]
    if size>0x1000000 or size&1: raise ValueError('Invalid PAC size')
    out=bytearray(); pos=4
    while len(out)<size:
        flags=struct.unpack_from('<H',data,pos)[0]; pos+=2
        for bit in range(8):
            word=struct.unpack_from('<H',data,pos)[0]; pos+=2
            if flags&(1<<bit): out+=struct.pack('<H',word)
            else:
                dist=(word>>5)*2
                if not dist: raise ValueError('Invalid zero-distance PAC token')
                for _ in range((word&31)+2):
                    at=len(out)-dist
                    out+=out[at:at+2] if at>=0 else b'\0\0'
            if len(out)>=size: break
    if len(out)!=size: raise ValueError('PAC length mismatch')
    return bytes(out),pos

def compress(data: bytes):
    if len(data)&1: raise ValueError('PAC requires even length')
    words=struct.unpack('<'+'H'*(len(data)//2),data)
    out=bytearray(struct.pack('<I',len(data))); index=defaultdict(deque); pos=0
    while pos<len(words):
        flag_at=len(out); out+=b'\0\0'; flags=0
        for bit in range(8):
            if pos>=len(words): break
            length=0; distance=0
            key=words[pos:pos+2]
            candidates=index[key]
            while candidates and candidates[0]<pos-2047: candidates.popleft()
            for prev in reversed(candidates):
                n=2; maxlen=min(33,len(words)-pos)
                while n<maxlen and words[prev+n]==words[pos+n]: n+=1
                if n>length: length=n;distance=pos-prev
                if n==maxlen: break
            used=length if length>=2 else 1
            if used==1: flags|=1<<bit; token=words[pos]
            else: token=(distance<<5)|(used-2)
            out+=struct.pack('<H',token)
            for p in range(pos,pos+used):
                if p+1<len(words): index[words[p:p+2]].append(p)
            pos+=used
        struct.pack_into('<H',out,flag_at,flags)
    return bytes(out)

def main():
    root=Path(__file__).resolve().parents[1]
    for f in (root/'work/extracted').rglob('*.PAC'):
        data,used=decompress(f.read_bytes())
        out=root/'work/decompressed'/f.relative_to(root/'work/extracted')
        out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
        packed=compress(data)
        assert decompress(packed)[0]==data
        print(str(f.relative_to(root/'work/extracted')),len(data),'consumed',used,'original',f.stat().st_size,'repacked',len(packed))

if __name__=='__main__': main()
