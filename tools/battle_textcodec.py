"""Battle-only control operands, distinct from field dialogue commands."""
from textcodec import table
from korean_codec import normalize,JP

ARGS={2:'char',6:'wait',8:'slot2',9:'slot3',10:'slot4',11:'monster',12:'command',13:'monster_number',14:'item',15:'attack',18:'string'}
SIMPLE={0:'end',1:'newline',4:'color',5:'pause',7:'key',16:'var0',17:'var1',19:'var2',20:'var3'}

def string_end(data,start):
    p=start
    while p<len(data):
        c=data[p];p+=1
        if c==0:return p
        if c in ARGS or 0x1c<=c<=0x1f:p+=1
    raise ValueError('Unterminated battle text')

def decode(data):
    tbl=table('nullTerminated');out=[];p=0
    while p<len(data):
        c=data[p];p+=1
        if not c:break
        if c in ARGS:
            if p==len(data):raise ValueError('Missing battle control operand')
            out.append('{'+ARGS[c]+'['+f'{data[p]:02X}'+']}');p+=1
        elif c in SIMPLE:
            out.append('\n' if c==1 else '{'+SIMPLE[c]+'}')
        else:
            code=bytes((c,))
            if 0x1c<=c<=0x1f:
                code+=data[p:p+1];p+=1
            value=tbl.get(code,'{'+code.hex().upper()+'}')
            if value.startswith('\\') and JP.search(value):value=value[1:]
            out.append(value)
    return ''.join(out)

def encode(text,mapping):
    import re
    simple={v:bytes((k,)) for k,v in SIMPLE.items()}
    args={v:k for k,v in ARGS.items()};out=bytearray()
    for part in re.split(r'(\{[^{}]+\})',normalize(text)):
        if part.startswith('{'):
            key=part[1:-1]
            if key in simple:out+=simple[key]
            elif re.fullmatch(r'[A-Za-z0-9_]+\[[0-9A-F]{2}\]',key):
                name,arg=key[:-1].split('[');out+=bytes((args[name],int(arg,16)))
            elif re.fullmatch('[0-9A-F]{2}',key):out+=bytes.fromhex(key)
            else:raise ValueError('Unknown battle control '+part)
        else:
            for c in part:out+=mapping[c]
    return bytes(out)
