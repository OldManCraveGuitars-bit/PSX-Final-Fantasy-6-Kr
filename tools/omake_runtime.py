"""Build the translated PlayStation bonus menu and its Galmuri7 renderer."""
import collections,heapq,json,re,struct,subprocess
from textcodec import ROOT
from korean_codec import normalize,raster,JP
from pac import compress,decompress
from bytelz import compress as byte_compress,decompress as byte_decompress

BASE=0x800c8000
CODE=0x33af0
BUFFER=0x37b80
CONFIG=0x37f80

def compile_runtime():
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/omake-runtime.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib',
        f'-Wl,-T{ROOT.as_posix()}/native/omake-runtime.ld,--build-id=none','-o',str(elf),
        str(ROOT/'native/omake_runtime.c'),str(ROOT/'native/omake_hooks.S')],check=True)
    binary=ROOT/'work/omake-runtime.bin'
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(binary)],check=True)
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        f=line.split()
        if len(f)==3:symbols[f[2]]=int(f[0],16)&0xffffffff
    return binary.read_bytes(),symbols

def huffman(streams):
    counts=collections.Counter(b''.join(streams));queue=[(n,[c]) for c,n in counts.items()];heapq.heapify(queue)
    lengths=collections.Counter()
    while len(queue)>1:
        a,x=heapq.heappop(queue);b,y=heapq.heappop(queue)
        for c in x+y:lengths[c]+=1
        heapq.heappush(queue,(a+b,x+y))
    if not lengths or max(lengths.values())>15:raise ValueError('Bonus Huffman code capacity')
    ordered=sorted(lengths,key=lambda c:(lengths[c],c));counts=[0]*16;first=[0]*16;indices=[0]*16
    for c in ordered:counts[lengths[c]]+=1
    code=n=0;codes={}
    for size in range(1,16):
        code=(code+counts[size-1])*2;first[size]=code;indices[size]=n
        for c in ordered[n:n+counts[size]]:codes[c]=(code+n-indices[size],size);n+=1
    table=struct.pack('<48H',*(counts+first+indices))+bytes(ordered)+bytes(256-len(ordered))
    packed={}
    for stream in sorted(set(streams)):
        if len(stream)>1024:raise ValueError('Bonus expansion buffer overflow')
        out=bytearray(struct.pack('<H',len(stream)));bits=n=0
        for c in stream:
            value,size=codes[c];bits=(bits<<size)|value;n+=size
            while n>=8:n-=8;out.append((bits>>n)&255)
        if n:out.append((bits<<(8-n))&255)
        packed[stream]=bytes(out)
    return table,packed

def wrap(text,limit=216):
    lines=[]
    for source in text.split('\n'):
        line=''
        for word in source.split(' '):
            candidate=(line+' '+word) if line else word
            if sum(6 if c==' ' else 12 for c in candidate)>limit and line:
                lines.append(line);line=word
            else:line=candidate
        lines.append(line)
    if any(sum(6 if c==' ' else 12 for c in line)>limit for line in lines):raise ValueError('Bonus unbreakable line')
    return '\n'.join(lines)

def patch(changes):
    original=decompress((ROOT/'work/extracted/OMAKEDIR/OMAKE.PAC').read_bytes())[0]
    if len(original)!=CODE:raise ValueError('Bonus overlay size guard')
    overlay=bytearray(original)+bytearray(0x38000-len(original))
    rows=json.loads((ROOT/'analysis/omake-original.json').read_text('utf8'))
    ko=json.loads((ROOT/'translations/omake.ko.json').read_text('utf8'))
    if len(ko)!=len(rows):raise ValueError('Bonus translations incomplete')
    small=json.loads((ROOT/'translations/omake-small.ko.json').read_text('utf8'))
    texts=[]
    for row in rows:
        text=normalize(ko[str(row['id'])]['translation']).replace('갓파','임프')
        if JP.search(text) or '【' in text or '\u3000' in text:raise ValueError(('Bonus untranslated text',row['id']))
        if 89<=row['id']<=521:text=' '.join(text.split())
        texts.append(wrap(text))
    if any(len(texts[i].split('\n'))>6 for i in range(89,522)):raise ValueError('Bonus description exceeds original panel height')
    chars=sorted(set(''.join(texts))-{' ','\n'})
    mapping={' ':0};mapping.update({c:i+1 for i,c in enumerate(chars)})
    if len(mapping)>882:raise ValueError('Bonus 12x12 font atlas overflow')
    small_mapping={c:i for i,c in enumerate(sorted({c for text in small['strings'] for c in text if ord(c)>127}))}
    small_tail_y=((max(0,len(mapping)-441)+20)//21)*12
    if len(small_mapping)>36*((256-small_tail_y)//8):raise ValueError('Bonus small font atlas overflow')
    small_locations={}
    for c,i in small_mapping.items():
        small_locations[c]=[512+(i%36)*7,small_tail_y+(i//36)*8]
    streams=[struct.pack('<'+'H'*(len(text)+1),*[0x8000 if c=='\n' else mapping[c] for c in text],0xffff) for text in texts]
    table,compressed=huffman(streams)
    cursor=0x21648
    def store(data,alignment=2):
        nonlocal cursor
        cursor=(cursor+alignment-1)//alignment*alignment;at=cursor;cursor+=len(data)
        if cursor>0x2b930:raise ValueError(('Bonus original text pool overflow',hex(cursor)))
        overlay[at:cursor]=data;return BASE+at
    table_address=store(table)
    positions={s:store(p) for s,p in compressed.items()}
    encoded=[]
    for row,text,stream in zip(rows,texts,streams):
        struct.pack_into('<I',overlay,row['pointer_offset'],positions[stream])
        encoded.append({'id':row['id'],'translation':text,'raw_hex':stream.hex(),'address':positions[stream]})
    small_encoded=[];pointers=[]
    for text in small['strings']:
        stream=bytearray()
        for c in text:
            if ord(c)<128:stream.append(ord(c))
            else:
                i=small_mapping[c];stream+=bytes((0x10+(i>>7),0x80+(i&127)))
        stream.append(0);pointers.append(store(stream));small_encoded.append(stream.hex())
    directory=store(struct.pack('<'+'I'*len(pointers),*pointers),4)
    attribute_names=[]
    for text in ['불','얼음','번개','독','물','땅','바람','성']:
        attribute_names.append(store(struct.pack('<'+'H'*(len(text)+1),*[mapping[c] for c in text],0xffff)))
    attributes=store(struct.pack('<8I',*attribute_names),4)
    overlay[cursor:0x2b930]=bytes(0x2b930-cursor)
    for row in small['records']:
        at=row['offset'];old=bytes.fromhex(row['raw_hex'])+b'\0'
        if original[at:at+len(old)]!=old:raise ValueError(('Bonus small literal guard',row['id']))
        replacement=bytes.fromhex(row['patched_hex'])
        # Some labels contain an internal kana-bank switch (magic level 10,
        # etc.). Plain-label callers skip only the first selector; Korean
        # references select their own atlas, so embedded switches are obsolete.
        if replacement.startswith((b'%k',b'%K')):
            replacement=replacement[:2]+re.sub(rb'%[kK]',b'',replacement[2:])
        overlay[at:at+row['length']]=replacement+bytes(row['length']-len(replacement))
    code,symbols=compile_runtime()
    if CODE+len(code)>BUFFER:raise ValueError('Bonus runtime overlaps expansion buffer')
    overlay[CODE:CODE+len(code)]=code
    struct.pack_into('<III',overlay,CONFIG,directory,table_address,len(pointers))
    struct.pack_into('<I',overlay,CONFIG+24,attributes)
    struct.pack_into('<I',overlay,CONFIG+28,small_tail_y)
    hooks=[]
    at=0x800d4530-BASE
    if original[at:at+4]!=struct.pack('<I',0x0c03692b):raise ValueError('Record column heading guard')
    struct.pack_into('<I',overlay,at,0x0c000000|((symbols['kr_omake_record_columns']>>2)&0x3ffffff))
    hooks.append({'address':0x800d4530,'symbol':'kr_omake_record_columns','original':original[at:at+4].hex()})
    for address,symbol in [(0x800e0df0,'kr_omake_wide_lookup_hook'),(0x800e0d68,'kr_omake_text_length'),
        (0x800dc420,'kr_omake_small_text'),(0x800dc210,'kr_omake_small_glyph'),
        (0x800dc494,'kr_omake_small_next_hook'),(0x800dc4e0,'kr_omake_small_advance_hook'),
        (0x800d9ba8,'kr_omake_printf_glyph'),(0x800d9d40,'kr_omake_puts'),
        (0x800da3dc,'kr_omake_printf_next_hook'),
        (0x800ccc78,'kr_omake_attributes'),
        (0x800e0ad0,'kr_omake_wide_glyph_hook')]:
        at=address-BASE
        struct.pack_into('<II',overlay,at,0x08000000|((symbols[symbol]>>2)&0x3ffffff),0)
        hooks.append({'address':address,'symbol':symbol,'original':original[at:at+8].hex()})
    old_texture=(ROOT/'work/extracted/OMAKEDIR/ALLTIM.BIN').read_bytes();tim=bytearray(byte_decompress(old_texture)[0])
    image_at=8+struct.unpack_from('<I',tim,8)[0];size,x,y,words,height=struct.unpack_from('<I4H',tim,image_at)
    if (x,y,words,height)!=(448,256,256,256):raise ValueError('Bonus texture geometry guard')
    pixels=bytearray(c for b in tim[image_at+12:image_at+size] for c in (b&15,b>>4));old_pixels=bytes(pixels)
    for gy in range(256):pixels[gy*1024+256:gy*1024+768]=bytes(512)
    source_mapping=json.loads((ROOT/'analysis/omake-font.json').read_text('utf8'))['mapping']
    original_glyphs={normalize(c):int(i) for i,c in source_mapping.items()}
    def put(c,gx,gy,small_font):
        glyph=raster(c,small=small_font);cell=8 if small_font else 12
        for yy in range(cell):
            for xx in range(7 if small_font else cell):
                fg=yy<glyph.height and glyph.getpixel((xx,yy))
                shadow=(xx>0 and yy<glyph.height and glyph.getpixel((xx-1,yy))) or (yy>0 and glyph.getpixel((xx,yy-1))) or (xx>0 and yy>0 and glyph.getpixel((xx-1,yy-1)))
                pixels[(gy+yy)*1024+gx+xx]=3 if fg else 1 if shadow else 0
    preserved=[]
    for c,i in mapping.items():
        gx=256+(i//441)*256+(i%441%21)*12;gy=(i%441//21)*12
        if ord(c)<128 and c in original_glyphs:
            old=original_glyphs[c];ox=256+old//441*256+(old%441%21)*12;oy=(old%441//21)*12
            for yy in range(12):pixels[(gy+yy)*1024+gx:(gy+yy)*1024+gx+12]=old_pixels[(oy+yy)*1024+ox:(oy+yy)*1024+ox+12]
            preserved.append(c)
        else:put(c,gx,gy,False)
    for c,i in small_mapping.items():
        gx,gy=small_locations[c];put(c,gx,gy,True)
    for yy in range(256):
        assert pixels[yy*1024:yy*1024+256]==old_pixels[yy*1024:yy*1024+256]
        assert pixels[yy*1024+768:(yy+1)*1024]==old_pixels[yy*1024+768:(yy+1)*1024]
    tim[image_at+12:image_at+size]=bytes(pixels[i]|(pixels[i+1]<<4) for i in range(0,len(pixels),2))
    packed_texture=byte_compress(bytes(tim));assert byte_decompress(packed_texture)[0]==tim
    if len(packed_texture)>len(old_texture):raise ValueError(('Bonus texture packed extent overflow',len(packed_texture),len(old_texture)))
    packed=compress(bytes(overlay));assert decompress(packed)[0]==overlay
    changes=dict(changes);changes['OMAKEDIR/OMAKE.PAC']=packed;changes['OMAKEDIR/ALLTIM.BIN']=packed_texture+bytes(len(old_texture)-len(packed_texture))
    exe=bytearray(changes.get('SLPM_861.98',(ROOT/'work/extracted/SLPM_861.98').read_bytes()))
    prefix=0x80038000-struct.unpack_from('<I',exe,0x18)[0]
    load_bytes=(len(packed)+2047)//2048*2048
    if exe[0x1f5c+prefix:0x1f64+prefix]!=struct.pack('<II',0x3c0d0001,0x35adc800):raise ValueError('Bonus compressed read-size guard')
    struct.pack_into('<II',exe,0x1f5c+prefix,0x3c0d0000|(load_bytes>>16),0x35ad0000|(load_bytes&65535))
    # The old 0x801c8800 staging buffer ended at 0x801e5000. The expanded
    # compressed overlay crossed that boundary and destroyed bonus records.
    # Move only this transient read/decompression input, below the live data.
    staging=0x801c0000
    if staging+load_bytes>0x801e5000:raise ValueError('Bonus staging overlaps system records')
    for address,guard,word in [(0x8003a128,0x8f8501b4,0x3c05801c),
                               (0x8003a13c,0x8f8401b4,0x3c04801c)]:
        at=address-0x80038000+0x800+prefix
        if struct.unpack_from('<I',exe,at)[0]!=guard:raise ValueError('Bonus staging loader guard')
        struct.pack_into('<I',exe,at,word)
    inventory=json.loads((ROOT/'analysis/disc_inventory.json').read_text('utf8'))
    lba=next(x['extent_lba'] for x in inventory['entries'] if x['path']=='DUMMY0.DAT')+1024
    absolute=lba+150;minute=absolute//4500;second=absolute//75%60;frame=absolute%75
    bcd=lambda value:(value//10)*16+value%10
    msf=bytes((bcd(minute),bcd(second),bcd(frame),0))
    if exe[0x2bcd0+prefix:0x2bcd4+prefix]!=bytes.fromhex('00460200'):raise ValueError('Bonus compressed MSF guard')
    exe[0x2bcd0+prefix:0x2bcd4+prefix]=msf;changes['SLPM_861.98']=bytes(exe)
    report={'records':len(rows),'small_literals':len(small['records']),'small_strings':len(pointers),'mapping':mapping,
        'fonts':{'large':'Galmuri9','small':'Galmuri7'},'cell':[12,12],'small_cell':[8,8],
        'space_pixels':6,'small_space_pixels':4,'small_mapping':small_mapping,'preserved_large_English':preserved,
        'small_locations':small_locations,'small_secondary_y':small_tail_y,
        'max_description_lines':max(len(texts[i].split('\n')) for i in range(89,522)),
        'runtime_bytes':len(code),'overlay_bytes':len(overlay),
        'overlay_packed_bytes':len(packed),'texture_packed_bytes':len(packed_texture),'pool_bytes':cursor-0x21648,
        'pool_capacity':0x2b930-0x21648,'huffman_address':table_address,'small_directory_address':directory,
        'symbols':symbols,'hooks':hooks,'encoded':encoded,'small_encoded':small_encoded,
        'relocation_lba':lba,'relocation_msf':msf.hex(),'compressed_read_bytes':load_bytes,
        'compressed_staging_address':hex(staging),'compressed_staging_end':hex(staging+load_bytes),
        'preserved_system_records_start':'0x801e5000',
        'native_gameplay_verification':'pending','new_runtime_memory_gap':'pending native write-watch'}
    (ROOT/'analysis/omake-insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    (ROOT/'work/omake-patched.bin').write_bytes(overlay)
    print({k:v for k,v in report.items() if k not in ['mapping','small_mapping','small_locations','symbols','hooks','encoded','small_encoded']})
    return changes

if __name__=='__main__':
    for path,data in patch({}).items():
        if path=='SLPM_861.98':
            (ROOT/'work/omake-loader-test-exe.bin').write_bytes(data);continue
        p=ROOT/'work/modified'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
