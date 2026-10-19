"""Relocate battle large strings through guarded native reference records."""
import collections,heapq,json,struct,subprocess
from textcodec import ROOT
from korean_codec import allocate,build_large,font_index,normalize
from battle_textcodec import encode
from small_text import ascii_glyphs

DATA_BASE=0x8019b800
FONT_OFFSET=0x3b0f8
CODE_OFFSET=FONT_OFFSET+936*22
DIGIT_FIRST=901
DIGIT_COUNT=10

def compile_runtime():
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/battle-big-runtime.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib',
        f'-Wl,-T{ROOT.as_posix()}/native/battle-big-runtime.ld,--build-id=none','-o',str(elf),
        str(ROOT/'native/battle_big_text.c'),str(ROOT/'native/battle_big_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(ROOT/'work/battle-big-runtime.bin')],check=True)
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:symbols[fields[2]]=int(fields[0],16)&0xffffffff
    return (ROOT/'work/battle-big-runtime.bin').read_bytes(),symbols

def huffman(streams):
    counts=collections.Counter(b''.join(streams));queue=[(n,[c]) for c,n in counts.items()];heapq.heapify(queue)
    lengths=collections.Counter()
    while len(queue)>1:
        a,x=heapq.heappop(queue);b,y=heapq.heappop(queue)
        for c in x+y:lengths[c]+=1
        heapq.heappush(queue,(a+b,x+y))
    if max(lengths.values())>15:raise ValueError('Huffman code exceeds native table')
    ordered=sorted(lengths,key=lambda c:(lengths[c],c));frequencies=[0]*16;first=[0]*16;indices=[0]*16
    for c in ordered:frequencies[lengths[c]]+=1
    n=code=0;codes={}
    for size in range(1,16):
        code=(code+frequencies[size-1])*2;first[size]=code;indices[size]=n
        for c in ordered[n:n+frequencies[size]]:codes[c]=(code+n-indices[size],size);n+=1
    table=struct.pack('<48H',*(frequencies+first+indices))+bytes(ordered)+bytes(256-len(ordered))
    def compress(stream):
        if len(stream)>255:raise ValueError('Battle text exceeds native expansion buffer')
        out=bytearray((len(stream),));bits=0;n=0
        for c in stream:
            v,k=codes[c];bits=(bits<<k)|v;n+=k
            while n>=8:n-=8;out.append((bits>>n)&255)
        if n:out.append((bits<<(8-n))&255)
        return bytes(out)
    return table,{s:compress(s) for s in streams}

class Pool:
    def __init__(self,ranges):self.free=[list(x) for x in sorted(ranges)];self.used=[]
    def alloc(self,n,alignment=2,label=''):
        choices=[]
        for i,(lo,hi) in enumerate(self.free):
            at=(lo+alignment-1)//alignment*alignment
            if at+n<=hi:choices.append((hi-at-n,i,at))
        if not choices:raise ValueError(('Battle text pool exhausted',label,n,sum(b-a for a,b in self.free),self.free))
        _,i,at=min(choices);lo,hi=self.free.pop(i)
        if at>lo:self.free.append([lo,at])
        if at+n<hi:self.free.append([at+n,hi])
        self.used.append({'offset':at,'bytes':n,'label':label});return at

def patch(data,resource,overlay,small_report):
    fixed=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    names=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    selected=[r for r in fixed if r['encoding']=='bigText'];rows=selected[:]
    texts=[normalize(names[str(r['id'])]['translation']).strip() for r in selected]
    for name in ['descriptions','battle-abilities','battle-messages']:
        extra=json.loads((ROOT/'analysis'/(name+'-original.json')).read_text('utf8'))
        translated=json.loads((ROOT/'translations'/(name+'.ko.json')).read_text('utf8'))
        rows+=extra;texts += [normalize(translated[str(r['id'])]['translation']).strip() for r in extra]
    mapping,assigned=allocate(texts+[normalize(r['translation']) for r in names.values()],reserved_indices=range(DIGIT_FIRST,DIGIT_FIRST+DIGIT_COUNT))
    if max(font_index(v) for v in mapping.values() if v in assigned.values())>=930:raise ValueError('Battle large font/code overlap')
    streams=[encode(t,mapping)+b'\0' for t in texts]
    original=(ROOT/'work/extracted/BTL/FF6_BTL.BIN').read_bytes()
    data[FONT_OFFSET:FONT_OFFSET+1248*22]=build_large(original[FONT_OFFSET:FONT_OFFSET+1248*22],assigned,mapping)
    # Preserve original numeral pixels before the tail is occupied by code.
    # kr_big_glyph also redirects dynamically generated native digits here.
    for digit in range(DIGIT_COUNT):
        old=FONT_OFFSET+(1075+digit)*22;new=FONT_OFFSET+(DIGIT_FIRST+digit)*22
        data[new:new+22]=original[old:old+22]
    # These copies are bypassed by the small-name hooks or guarded large paths.
    # Monster names remain intact because the battle engine compares their bytes.
    ranges=[]
    for category in ['character','spell','command','item','esper','attack','esper_attack','monster_attack']:
        occurrences=[o for r in fixed if r['category']==category for o in r['occurrences'] if o['file']=='BTL/FF6_BTL.BIN']
        ranges.append((min(o['offset'] for o in occurrences),max(o['offset']+o['length'] for o in occurrences)))
    groups={};references=[]
    for identifier,row in enumerate(rows[len(selected):],len(selected)):
        occ=next(o for o in row['occurrences'] if o['file']=='BTL/FF6_BTL.BIN')
        key=(occ['base'],occ['capacity']);group=groups.setdefault(key,{'cursor':occ['base'],'refs':{}})
        ref=bytes((0x18,identifier%255+1,identifier//255+1,0)) if texts[identifier] else b'\0'
        # Identical translations may share one native reference within each pool.
        stream=streams[identifier]
        if stream not in group['refs']:
            at=group['cursor'];group['refs'][stream]=at;data[at:at+len(ref)]=ref;group['cursor']+=len(ref)
        at=group['refs'][stream]
        relative=at-occ['base']+occ.get('pointer_bias',0)
        struct.pack_into('<H',data,occ['pointer_offset'],relative)
        references.append({'record':identifier,'pointer_offset':occ['pointer_offset'],'offset':at,'bias':occ.get('pointer_bias',0)})
    for (base,capacity),g in groups.items():
        if g['cursor']>base+capacity:raise ValueError('Battle reference pool overflow')
        ranges.append((g['cursor'],base+capacity))
    # The complete original font tail starts above every used text glyph.
    code,symbols=compile_runtime();lut=bytearray(b'\xff\xff'*1248)
    small_mapping=small_report['mapping'];ascii_table=ascii_glyphs()
    resource[0x3200:0x3a00]=b'\xff\xff'*1024
    for char,codepoint in mapping.items():
        if font_index(codepoint)<0:continue
        if char in small_mapping:tile=small_mapping[char]
        elif len(char)==1 and 0<=ord(char)<128:tile=256+ascii_table[ord(char)]
        else:continue
        struct.pack_into('<H',lut,font_index(codepoint)*2,tile)
        struct.pack_into('<H',resource,0x3200+tile*2,font_index(codepoint))
    lut_at=(CODE_OFFSET+len(code)+3)&~3
    if lut_at+len(lut)>FONT_OFFSET+1248*22:raise ValueError(('Battle font-tail runtime overflow',len(code),len(lut)))
    data[CODE_OFFSET:CODE_OFFSET+len(code)]=code;data[lut_at:lut_at+len(lut)]=lut
    table,compressed=huffman(set(streams))
    assert len(table)==352
    data[0x44d00:0x44e60]=table;data[0x44e80:0x44f80]=bytes(256)
    pool=Pool(ranges);packed_font=(ROOT/'work/battle-korean-font.pac').read_bytes()
    directory_at=pool.alloc(len(rows)*2,label='large-text pointer directory')
    font_at=pool.alloc(len(packed_font),label='compressed Galmuri7 battle atlas')
    data[font_at:font_at+len(packed_font)]=packed_font
    positions={}
    for stream,packed in sorted(compressed.items(),key=lambda x:(-len(x[1]),x[0])):
        at=pool.alloc(len(packed),label='text');positions[stream]=at;data[at:at+len(packed)]=packed
    encoded=[]
    for i,(row,text,stream) in enumerate(zip(rows,texts,streams)):
        at=positions[stream];offset=at-0x11a00
        if offset<0 or offset&1 or offset//2>65535:raise ValueError('Battle compact pointer overflow')
        struct.pack_into('<H',data,directory_at+i*2,offset//2)
        encoded.append({'id':i,'category':row['category'],'index':row['index'],'translation':text,'hex':stream.hex(),'offset':at})
    struct.pack_into('<I',resource,0x3ba8,DATA_BASE+font_at)
    struct.pack_into('<III',resource,0x3bb0,DATA_BASE+directory_at,DATA_BASE+lut_at,font_index(mapping['?']))
    hooks=[]
    for address,symbol in [(0x800d1440,'kr_big_glyph'),(0x800d0550,'kr_big_command'),(0x800d0b3c,'kr_big_attack'),
        (0x800d0dfc,'kr_big_item'),(0x800d01e0,'kr_big_character'),(0x800d0680,'kr_big_reward_character'),(0x800d339c,'kr_big_small_list_hook'),
        (0x800d3678,'kr_big_small_short_hook'),(0x800d3a74,'kr_big_small_magitek_hook'),(0x800d307c,'kr_big_small_bushido_hook'),(0x800d3b98,'kr_big_small_summon_hook'),(0x800d5a84,'kr_big_small_menu_hook'),
        (0x8014081c,'kr_big_monster_attack_source_hook'),(0x801276dc,'kr_big_esper_attack_copy_hook')]:
        at=address-0x800c8000
        source=(ROOT/'work/decompressed/BTL/BATTLE.PAC').read_bytes()
        if overlay[at:at+8]!=source[at:at+8]:raise ValueError(('Overlapping battle hook',hex(address)))
        guard=source[at:at+8].hex();struct.pack_into('<II',overlay,at,(2<<26)|((symbols[symbol]>>2)&0x3ffffff),0)
        hooks.append({'address':address,'symbol':symbol,'original':guard,'bytes':overlay[at:at+8].hex()})
    if struct.unpack_from('<I',overlay,0x38+0x18*4)[0]!=0x800d009c:raise ValueError('Battle reference opcode guard')
    struct.pack_into('<I',overlay,0x38+0x18*4,symbols['kr_big_ref_case'])
    report={'records':len(rows),'fixed_big_names':len(selected),'glyphs':len(assigned),'runtime_bytes':len(code),
        'font_tail_offset':CODE_OFFSET,'small_lut_offset':lut_at,'directory_offset':directory_at,'font_offset':font_at,
        'original_text_bytes':sum(map(len,set(streams))),'compressed_text_bytes':sum(map(len,compressed.values())),
        'free_text_bytes':sum(b-a for a,b in pool.free),'huffman_offset':0x44d00,'buffer_offset':0x44e80,
        'max_expanded_bytes':max(map(len,streams)),'hooks':hooks,'symbols':symbols,'encoded':encoded,'references':references,
        'allocations':pool.used,'mapping':{k:v.hex() for k,v in mapping.items()},
        'digit_glyph_relocation':{'original_first':1075,'safe_first':DIGIT_FIRST,'count':DIGIT_COUNT,'pixels':'original 12x11 glyphs, unchanged'},
        'native_gameplay_verification':'pending'}
    (ROOT/'analysis/battle-big-text-insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print({k:v for k,v in report.items() if k not in ['hooks','symbols','encoded','references','allocations','mapping']})
    return data,resource,overlay,report
