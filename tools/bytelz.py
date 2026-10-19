"""Byte-oriented LZ stream used by the PlayStation GUI texture resources."""
import struct
from collections import defaultdict,deque

def decompress(data):
    size=struct.unpack_from('<I',data)[0]
    if size>0x1000000:raise ValueError('Invalid byte-LZ size')
    output=bytearray();position=4
    while len(output)<size:
        flags=data[position];position+=1
        for bit in range(8):
            if len(output)==size:break
            if flags&(1<<bit):output.append(data[position]);position+=1
            else:
                token=struct.unpack_from('<H',data,position)[0];position+=2
                distance=token>>5;length=(token&31)+3
                if not distance or len(output)+length>size:raise ValueError('Invalid byte-LZ reference')
                for _ in range(length):output.append(output[-distance] if len(output)>=distance else 0)
    return bytes(output),position

def compress(data):
    output=bytearray(struct.pack('<I',len(data)));index=defaultdict(deque);position=0
    while position<len(data):
        flag_at=len(output);output.append(0);flags=0
        for bit in range(8):
            if position>=len(data):break
            length=0;distance=0;key=data[position:position+3];candidates=index[key]
            while candidates and candidates[0]<position-2047:candidates.popleft()
            for previous in reversed(candidates):
                n=3;limit=min(34,len(data)-position)
                while n<limit and data[previous+n]==data[position+n]:n+=1
                if n>length:length=n;distance=position-previous
                if n==limit:break
            used=length if length>=3 else 1
            if used==1:flags|=1<<bit;output.append(data[position])
            else:output+=struct.pack('<H',(distance<<5)|(used-3))
            for p in range(position,position+used):
                if p+2<len(data):index[data[p:p+3]].append(p)
            position+=used
        output[flag_at]=flags
    return bytes(output)
