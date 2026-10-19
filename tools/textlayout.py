"""Wrap dialogue using the native pixel advances and half-width spaces."""
import re
from korean_codec import normalize,font_index

TOKENS=re.compile(r'\{[^{}]+\}|[^{}]')

def glyph_width(token,mapping,assigned,widths):
    if token==' ':return 6
    if token.startswith('{'):
        if re.fullmatch(r'\{t\[[0-9A-F]{2}\]\}',token):return int(token[3:5],16)*6
        if re.fullmatch(r'\{h?char\d+\}',token):return 72
        return 80 if token in ('{item}','{spell}','{gp}') else 0
    return 12 if token in assigned else widths[font_index(mapping[token])+32]

def center_prologue(text,mapping,assigned,widths,limit=216):
    lines=[]
    for line in normalize(text).split('\n'):
        line=re.sub(r'\{t\[[0-9A-F]{2}\]\}','',line).lstrip(' ')
        tokens=TOKENS.findall(line)
        visible=[i for i,t in enumerate(tokens) if not t.startswith('{')]
        while visible and tokens[visible[-1]]==' ':
            del tokens[visible[-1]];visible=visible[:-1]
        length=sum(glyph_width(t,mapping,assigned,widths) for t in tokens)
        if length>limit:raise ValueError('Prologue line exceeds centered area')
        spaces=max(0,int(((limit-length)/2)/6+0.5))
        prefix=f'{{t[{spaces:02X}]}}' if visible and spaces else ''
        lines.append(prefix+''.join(tokens))
    return '\n'.join(lines)

def wrap(text,mapping,assigned,widths,limit=216):
    out=[];line=[];pixels=0
    def width(token):return glyph_width(token,mapping,assigned,widths)
    def flush():
        nonlocal line,pixels
        out.extend(line);line=[];pixels=0
    for token in TOKENS.findall(normalize(text)):
        if token=='\n' or token in ('{page}','{key}'):
            flush();out.append(token);continue
        n=width(token)
        if pixels+n>limit and line:
            spaces=[i for i,t in enumerate(line) if t==' ']
            if spaces:
                cut=spaces[-1]
                out.extend(line[:cut]);out.append('\n');line=line[cut+1:];pixels=sum(width(t) for t in line)
            else:
                flush();out.append('\n')
            if token==' ':continue
            if pixels+n>limit and line:
                flush();out.append('\n')
        line.append(token);pixels+=n
    flush()
    return ''.join(out)
