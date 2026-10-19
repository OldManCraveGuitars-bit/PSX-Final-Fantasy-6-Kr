"""Patch the PlayStation-only save/load interface and its two native fonts."""
import json,re,struct,unicodedata
from textcodec import ROOT
from korean_codec import raster
from bytelz import decompress as byte_decompress,compress as byte_compress
from pac import decompress,compress
from prepare_psx_ui import PRINTF
from psx_label_format import old_kana

def mips_j(address):return (2<<26)|((address>>2)&0x3ffffff)
def put_code(data,cursor,instructions):
    cursor=(cursor+3)&~3;code=struct.pack('<'+'I'*len(instructions),*instructions)
    data[cursor:cursor+len(code)]=code
    return 0x800c8000+cursor,cursor+len(code)

def patch(changes):
    label_path=ROOT/'translations/psx-small-labels.ko.json'
    printf=PRINTF
    if label_path.exists():
        rows=json.loads(label_path.read_text('utf8'))
        printf={row['source']:row['translation'] for row in rows.values()}
        if set(printf)!=set(PRINTF):raise ValueError('PSX small-label source keys changed')
        for source_text,text in printf.items():
            if re.findall(r'%(?:\d*[diuxsf]|p)',source_text)!=re.findall(r'%(?:\d*[diuxsf]|p)',text):
                raise ValueError(('PSX small-label format controls changed',source_text))
    source=(ROOT/'work/extracted/DEODIR/DEO.PAC').read_bytes()
    overlay=bytearray(decompress(source)[0]);original=bytes(overlay)
    # Save previews contain a second set of job labels. Resolve them against
    # the existing editor-managed job catalog, so edits have one source.
    def kana_key(text):
        text=re.sub(r'%[kK]','',unicodedata.normalize('NFKC',text))
        return ''.join(chr(ord(c)-0x60) if '\u30a1'<=c<='\u30f6' else c for c in text)
    jobs=json.loads((ROOT/'translations/menu-jobs.ko.json').read_text('utf8'))
    jobs_by_source={kana_key(r['source']):r['translation'] for r in jobs.values() if r['source']}
    preview_jobs={};at=0xfe0
    while at<0x1098:
        end=original.index(0,at,0x1098);raw=original[at:end]
        if raw.startswith((b'%k',b'%K')):
            text=unicodedata.normalize('NFKC',raw.decode('cp932'))
            preview_jobs[text]=jobs_by_source[kana_key(text)]
        at=(end+4)&~3
    assert len(preview_jobs)==18
    printf={**printf,**preview_jobs}
    # A resident header/footer duplicates these labels outside the first pool.
    # This legacy wording refers to the same physical memory-card warning;
    # keep its Korean text linked to the existing EXE-managed warning record.
    aliases={'%kスロット%Kヲ ヌカナイデクダサイ':'%kメモリーカード%Kヲ ヌカナイデクダサイ'}
    printf.update({alias:printf[parent] for alias,parent in aliases.items()})
    packed=(ROOT/'work/extracted/DEODIR/ALLTIM.BIN').read_bytes()
    tim=bytearray(byte_decompress(packed)[0])
    image_at=8+struct.unpack_from('<I',tim,8)[0]
    size,x,y,words,height=struct.unpack_from('<I4H',tim,image_at)
    assert (x,y,words,height)==(448,256,188,256)
    pixels=bytearray(c for b in tim[image_at+12:image_at+size] for c in (b&15,b>>4))
    def put_glyph(x,y,c,small=False):
        glyph=raster(c,small=small);width,height=(8,8) if small else (12,12)
        for gy in range(height):
            for gx in range(width):
                fg=gy<glyph.height and glyph.getpixel((gx,gy))
                shadow=(gx>0 and gy<glyph.height and glyph.getpixel((gx-1,gy))) or (gy>0 and glyph.getpixel((gx,gy-1))) or (gx>0 and gy>0 and glyph.getpixel((gx-1,gy-1)))
                pixels[(y+gy)*752+x+gx]=3 if fg else 1 if shadow else 0
    originals=json.loads((ROOT/'analysis/psx-ui-messages-original.json').read_text('utf8'))
    translated=json.loads((ROOT/'translations/psx-ui-messages.ko.json').read_text('utf8'))
    # Retain the original English letters, numerals, Roman numeral and ellipsis.
    mapping={' ':0,'E':62,'M':63,'P':64,'T':65,'Y':66,'Ⅵ':70,'O':111,'K':112,'1':124,'2':125,'…':91}
    chars=sorted(set(''.join(row['translation'] for row in translated.values()))-set(mapping)-{'\n'})
    available=[i for i in range(1,189) if i not in mapping.values()]
    if len(chars)>len(available):raise ValueError(('PSX UI message font overflow',len(chars),len(available)))
    for c,i in zip(chars,available):mapping[c]=i;put_glyph(256+(i%21)*12,(i//21)*12,c)
    put_glyph(256,0,' ')
    cursor=0x1b454
    for row in originals:
        text=translated[str(row['id'])]['translation']
        # This UI has only 189 glyph slots. Store their indices as bytes and
        # reserve FE/FF for newline/end. The saved space holds the name font
        # inside this existing text allocation, away from native script tables.
        encoded=bytes([0xfe if c=='\n' else mapping[c] for c in text]+[0xfe,0xff])
        struct.pack_into('<I',overlay,row['pointer_offset'],0x800c8000+cursor)
        overlay[cursor:cursor+len(encoded)]=encoded;cursor=(cursor+len(encoded)+3)&~3
    text_end=cursor
    narrow={
        0xb394:(0x94830000,0x90830000),0xb398:(0x3402ffff,0x340200ff),
        0xb3a4:(0x3403ffff,0x340300ff),0xb3a8:(0x24840002,0x24840001),
        0xb3ac:(0x94820000,0x90820000),
        0xb440:(0x96040000,0x92040000),0xb444:(0x3402ffff,0x340200ff),
        0xb450:(0x34148000,0x341400fe),0xb454:(0x3413ffff,0x341300ff),
        0xb46c:(0x26100002,0x26100001),0xb484:(0x26100002,0x26100001),
        0xb488:(0x96040000,0x92040000),
    }
    for at,(expected,new) in narrow.items():
        if struct.unpack_from('<I',original,at)[0]!=expected:raise ValueError(('PSX byte-index reader guard',hex(at)))
        struct.pack_into('<I',overlay,at,new)
    # Keep the native blank-glyph primitive and its bookkeeping. Adjust only
    # its final X advance.
    space_code=[0x16000002,0,0x2442fffa,0xa6a20000,mips_j(0x800d3308),0]
    address,cursor=put_code(overlay,cursor,space_code)
    if original[0xb300:0xb308]!=struct.pack('<II',0x00521021,0xa6a20000):raise ValueError('PSX message space hook guard')
    struct.pack_into('<II',overlay,0xb300,mips_j(address),0x00521021)
    # CE29C draws window borders from ASCII tile maps such as "(---)!   !".
    # Their blank cells are geometry, so retain the original eight-pixel grid.
    # Actual small text uses the separate printf half-space hooks.
    assert overlay[0x635c:0x6364]==original[0x635c:0x6364]
    # Physical-card confirmation keeps only the original save fields in WRAM.
    # Restore the tagged name extension from the already-read card payload.
    restore_code=[0x27bdffd0,0xafbf002c,(3<<26)|((0x800543ac>>2)&0x3ffffff),0]
    restore_code += [0xafa80010+(i<<16)+(i*4) for i in range(6)]
    restore_code += [0x3c088003,0x8d093500,0x3c0a314e,0x354a524b,0x152a000e,0,
        0x35093500,0x350a6000,0x350b0700,0x340c0c10,
        0x8d2d0000,0x25290004,0xad4d0000,0xad6d0000,0x254a0004,0x256b0004,0x258cfffc,0x1580fff8,0]
    restore_code += [0x8fa80010+(i<<16)+(i*4) for i in range(6)]+[0x8fbf002c,0,0x03e00008,0x27bd0030]
    address,cursor=put_code(overlay,cursor,restore_code)
    if original[0x1128c:0x11294]!=struct.pack('<II',0x0c0150eb,0x02463023):raise ValueError('Card-name restore hook guard')
    struct.pack_into('<I',overlay,0x1128c,(3<<26)|((address>>2)&0x3ffffff))
    # The temporary memory file uses the same raw save payload.
    quick=[0x3c048002,0x3484f600,0x3c058003,0x34a52400,0x34062000,
        (3<<26)|((address>>2)&0x3ffffff),0,0x34020001,0x3c01800e,0xa02233e4,mips_j(0x800d5484),0]
    quick=struct.pack('<12I',*quick)
    overlay[0xd428:0xd47c]=quick+bytes(0xd47c-0xd428-len(quick))
    restore_address=address
    if cursor>0x1c194:raise ValueError(('PSX message pool overflow',hex(cursor)))
    overlay[cursor:0x1c194]=bytes(0x1c194-cursor)
    # DE/DF are native combining dakuten/handakuten, not regular letters.
    # Assigning Hangul there changes its baseline and character advance.
    # The native formatter selects one of two 61-character kana banks. Keep
    # English glyphs intact and replace only those two Japanese banks.
    banks=[{c for source_text,text in printf.items() if source_text not in preview_jobs for c in text if ord(c)>127},
           {c for text in preview_jobs.values() for c in text if ord(c)>127}]
    if any(len(bank)>61 for bank in banks):raise ValueError(('PSX small font bank overflow (DE/DF reserved)',[len(bank) for bank in banks]))
    assignments={source_text:int(source_text in preview_jobs) for source_text in printf}
    encodings=[{c:0xa1+i for i,c in enumerate(sorted(bank))} for bank in banks]
    for bank,encoding in enumerate(encodings):
        for c,code in encoding.items():
            glyph=code+0x20 if bank else code-0x20
            put_glyph((glyph%32)*8,(glyph//32)*8,c,True)
    labels=[]
    for source_text,text in printf.items():
        old=old_kana(source_text)+b'\0';bank=assignments[source_text]
        encoded=(b'%K' if bank else b'%k')+b''.join(bytes((ord(c),)) if ord(c)<128 else bytes((encodings[bank][c],)) for c in text)+b'\0'
        if len(encoded)>len(old):raise ValueError(('PSX fixed label capacity',source_text,text,len(encoded),len(old)))
        positions=[];start,stop=0,len(original)
        while (at:=original.find(old,start,stop))>=0:
            if at+len(old)>0x1154:raise ValueError(('PSX label match outside native literal pools',source_text,hex(at)))
            positions.append(at);overlay[at:at+len(old)]=encoded+bytes(len(old)-len(encoded));start=at+len(old)
        if not positions:raise ValueError(('PSX label source not found',source_text,old.hex()))
        labels.append({'source':source_text,'translation':text,'occurrences':positions,'font_bank':bank,**({'editor_source_alias':aliases[source_text]} if source_text in aliases else {})})
    # The preview atlas is below the original fonts/portraits. No existing
    # texture pixels, including the scrolling-arrow glyphs, may be borrowed.
    if any(pixels[yy*752+xx] for yy in range(160,256) for xx in range(256,512)):
        raise ValueError('PSX preview atlas overlaps original graphics')
    from psx_name_preview import compile_runtime
    preview=compile_runtime(overlay,original,font_offset=cursor)
    cursor=preview['font_data_end']-0x800c8000
    # Border tiles recycle the same primitives as save-preview names, but
    # bypass printf's page reset. Restore page 7 for BOTH GPU buffers before
    # returning each native border sprite; leave UVs, CLUT and geometry intact.
    border_reset=[]
    for offset in (4,16):
        border_reset += [0x8c610000|offset,0,0x00010902,0x00010900,
                         0x34210007,0xac610000|offset]
    border_reset += [0x03e00008,0]
    border_address,cursor=put_code(overlay,cursor,border_reset)
    if original[0x6290:0x6298]!=struct.pack('<II',0xa46d0040,0x03e00008):
        raise ValueError('PSX border page reset hook guard')
    struct.pack_into('<II',overlay,0x6290,mips_j(border_address),0xa46d0040)
    if cursor>0x1c194:raise ValueError(('PSX border helper exceeds text pool',hex(cursor)))
    if overlay[0x1f978:]!=original[0x1f978:]:raise ValueError('Native actor scripts/tables changed')
    tim[image_at+12:image_at+size]=bytes(pixels[i]|(pixels[i+1]<<4) for i in range(0,len(pixels),2))
    new_tim=byte_compress(bytes(tim));assert byte_decompress(new_tim)[0]==tim
    if len(new_tim)>len(packed):raise ValueError(('PSX GUI texture capacity',len(new_tim),len(packed)))
    new_overlay=compress(bytes(overlay));assert decompress(new_overlay)[0]==overlay
    overlay_capacity=((len(source)+2047)//2048)*2048
    if len(new_overlay)>overlay_capacity:raise ValueError(('PSX GUI overlay capacity',len(new_overlay),overlay_capacity))
    changes=dict(changes);changes['DEODIR/ALLTIM.BIN']=new_tim+bytes(len(packed)-len(new_tim))
    changes['DEODIR/DEO.PAC']=new_overlay+bytes(max(0,len(source)-len(new_overlay)))
    report={'message_count':len(originals),'small_label_records':len(labels),'small_label_occurrences':sum(len(x['occurrences']) for x in labels),
        'preview_job_labels':len(preview_jobs),'preview_job_source':'translations/menu-jobs.ko.json',
        'fonts':{'messages':'Galmuri9','small':'Galmuri7'},'spaces':{'messages':6,'small':4},
        'message_font_glyphs':len(mapping),'small_bank_glyphs':[len(x) for x in banks],
        'message_pool_bytes':text_end-0x1b454,'message_pool_capacity':0x1c194-0x1b454,
        'message_storage':'8-bit native glyph indices; FE newline / FF end; original 12x12 drawing unchanged',
        'message_pool_total_used':cursor-0x1b454,
        'border_page_reset':hex(border_address),
        'texture_packed_bytes':len(new_tim),'overlay_packed_bytes':len(new_overlay),
        'physical_card_name_restore':hex(restore_address),
        'name_restore_bytes':len(restore_code)*4,
        'physical_card_name_restore_hook':'0x800d928c','quick_name_restore_hook':'0x800d5428',
        'labels':labels,'mapping':mapping,'small_encodings':encodings,'name_preview':preview,'native_verification':'pending'}
    (ROOT/'analysis/psx-ui-insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return changes

if __name__=='__main__':
    changes=patch({})
    for file,data in changes.items():
        target=ROOT/'work/modified'/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print('Built',list(changes))
