"""Tagged Korean small-text encoding, including original English/icon glyphs."""
import collections,json,re,struct
from functools import lru_cache
from textcodec import ROOT,table
from korean_codec import normalize,CONTROL

@lru_cache(maxsize=1)
def text_catalog():
    texts=[]
    for filename in ['fixed-catalog.ko.json','descriptions.ko.json','battle-abilities.ko.json','menu-labels.ko.json']:
        rows=json.loads((ROOT/'translations'/filename).read_text('utf8'))
        texts.extend(x['translation'] for x in rows.values())
    return texts

def allocate_aliases(mapping):
    counts=collections.Counter(c for text in text_catalog() for c in CONTROL.sub('',normalize(text)) if c in mapping)
    return {c:0x80+i for i,(c,_) in enumerate(counts.most_common(127))}

def ascii_glyphs():
    result=bytearray([0xff]*128)
    folder=ROOT/'references/ff6-disassembly/tools/char_table'
    for filename in ['romaji.json','small_symbols_jp.json']:
        for code,values in json.loads((folder/filename).read_text('utf8')).items():
            for c in values if isinstance(values,list) else [values]:
                if len(c)==1 and ord(c)<128:result[ord(c)]=int(code,16)
    for c,code in [('m',0x5d),('h',0x5e),('p',0x5f)]:result[ord(c)]=code
    for c in 'abcdefghijklmnopqrstuvwxyz':
        if result[ord(c)]==0xff:result[ord(c)]=result[ord(c.upper())]
    return bytes(result)

@lru_cache(maxsize=1)
def icon_codes():
    controls={v[1:]:k[0] for k,v in table('smallText').items() if v.startswith('\\') and len(k)==1 and k[0]>=0x20}
    counts=collections.Counter(token for text in text_catalog() for token in re.findall(r'\{([^{}]+)\}',text) if token in controls)
    return {name:2+i for i,(name,_) in enumerate(counts.most_common(25))},controls

def encode_small(text,mapping,aliases):
    out=bytearray(b'\x16');controls={v[1:]:k for k,v in table('smallText').items() if v.startswith('\\') and len(k)==1}
    icons,_=icon_codes()
    for part in re.split(r'(\{[^{}]+\})',normalize(text)):
        if not part:continue
        if part.startswith('{'):
            name=part[1:-1]
            if name not in controls or controls[name][0]<0x20:raise ValueError(('Unsupported small-text control',part))
            out+=bytes((icons[name],)) if name in icons else b'\x1b'+controls[name];continue
        for c in part:
            if c=='\n':raise ValueError('Small-text newline needs a layout-aware caller')
            if ord(c)<128:out.append(ord(c))
            elif c in aliases:out.append(aliases[c])
            else:
                glyph=mapping[c];out+=bytes((0x1c+(glyph>>8),glyph&255))
    return bytes(out)

def patch_labels(menu,overlay,mapping):
    aliases=allocate_aliases(mapping);menu[0x30d00:0x30d80]=ascii_glyphs()
    icons,controls=icon_codes()
    for name,code in icons.items():menu[0x30d80+code-2]=controls[name]
    for c,code in aliases.items():struct.pack_into('<H',menu,0x30e00+(code-0x80)*2,mapping[c])
    originals=json.loads((ROOT/'analysis/menu-labels-original.json').read_text('utf8'))
    translated=json.loads((ROOT/'translations/menu-labels.ko.json').read_text('utf8'))
    if len(originals)>512:raise ValueError('Positioned menu-label index overflow')
    cursor=0x31200
    for row in originals:
        if row['record_bytes']<4:raise ValueError('Menu reference stub does not fit')
        text=translated[str(row['id'])]['translation']
        record=struct.pack('<H',row['xy'])+encode_small(text,mapping,aliases)+b'\0'
        if cursor+len(record)>0x32000:raise ValueError('Positioned menu-label pool overflow')
        struct.pack_into('<H',menu,0x55800+row['id']*2,cursor-0x30000)
        menu[cursor:cursor+len(record)]=record;cursor+=len(record)
        identifier=row['id'];stub=bytes((0x15,identifier)) if identifier<256 else bytes((0x14,identifier&255,identifier>>8))
        if row['record_bytes']<2+len(stub):raise ValueError('Extended menu reference does not fit')
        at=row['offset'];overlay[at:at+row['record_bytes']]=struct.pack('<H',row['xy'])+stub+bytes(row['record_bytes']-2-len(stub))
    metadata={'labels_inserted':len(originals),'font':'Galmuri7','bytecode_aliases':len(aliases),
        'label_pool_bytes':cursor-0x31200,'label_pool_capacity':0xe00,'space_pixels':4,
        'aliases':{c:hex(code) for c,code in aliases.items()},'mapping':mapping,
        'English_and_icon_glyphs':'original glyphs','runtime_verification':'pending'}
    (ROOT/'analysis/small-text-insertion.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n','utf8')
    from menu_catalog import patch as patch_catalog
    menu,_=patch_catalog(menu,cursor,mapping)
    return menu,overlay
