"""Translate native field item/spell substitutions inside the existing load."""
import json,struct,subprocess
from textcodec import ROOT
from korean_codec import CONTROL,normalize,encode,raster
from battle_big_text import Pool

def patch(nar,script,overlay,mapping,script_used):
    fixed=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    translations=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    rows=[r for category in ['item','spell'] for r in fixed if r['category']==category]
    texts=[CONTROL.sub('',normalize(translations[str(r['id'])]['translation'])).strip() for r in rows]
    missing=sorted(set(''.join(texts))-mapping.keys());extended=dict(mapping)
    if len(missing)>96:raise ValueError('Field catalog dynamic glyph overflow')
    font=bytearray()
    for i,char in enumerate(missing):
        index=1152+i-224;extended[char]=bytes((0x1c+(index>>8),index&255))
        image=raster(char)
        for y in range(11):font+=struct.pack('<H',sum(1<<(11-x) for x in range(12) if image.getpixel((x,y))))
    start=(script_used+3)&~3;address=0x801a6200+start
    linker=ROOT/'work/field-catalog.ld'
    linker.write_text(f'OUTPUT_ARCH(mips)\nENTRY(kr_field_catalog)\nSECTIONS {{ . = 0x{address:08x}; .text : {{ *(.text .text.*) }} .rodata : {{ *(.rodata .rodata.*) }} .data : {{ *(.data .data.*) }} .bss : {{ *(.bss .bss.* COMMON) }} /DISCARD/ : {{ *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }} }}\n','ascii')
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/field-catalog.elf';binary=ROOT/'work/field-catalog.bin'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib',f'-Wl,-T{linker.as_posix()},--build-id=none',
        '-o',str(elf),str(ROOT/'native/field_catalog.c'),str(ROOT/'native/field_catalog_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(binary)],check=True)
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:symbols[fields[2]]=int(fields[0],16)&0xffffffff
    code=binary.read_bytes();script[start:start+len(code)]=code
    pool=Pool([(0x73cfc+16,0x745fc),(0x7463c,0x7474a),(0x76200+start+len(code),0x76200+0x1afa0)])
    directory=pool.alloc(len(rows)*4,4,'field name pointers');font_at=pool.alloc(len(font),2,'field extra glyphs')
    def put(at,value):
        if at>=0x76200:script[at-0x76200:at-0x76200+len(value)]=value
        else:nar[at:at+len(value)]=value
    put(font_at,font);records=[];unique={}
    for i,(row,text) in enumerate(zip(rows,texts)):
        encoded=encode(text,extended)+b'\0'
        if encoded not in unique:
            at=pool.alloc(len(encoded),1,'field name');put(at,encoded);unique[encoded]=at
        at=unique[encoded];put(directory+i*4,struct.pack('<I',0x80130000+at))
        records.append({'id':i,'category':row['category'],'index':row['index'],'translation':text,'hex':encoded.hex(),'offset':at})
    struct.pack_into('<III',nar,0x73cfc,0x80130000+directory,0x80130000+font_at,len(missing))
    hooks=[];original=(ROOT/'work/decompressed/NAR/NARITA.PAC').read_bytes()
    for at,symbol in [(0x801034d8,'kr_field_item_hook'),(0x80103624,'kr_field_spell_hook'),(0x8010089c,'kr_boost_new_game')]:
        offset=at-0x800c8000
        if overlay[offset:offset+8]!=original[offset:offset+8]:raise ValueError('Field catalog hook overlap')
        guard=overlay[offset:offset+8].hex();struct.pack_into('<II',overlay,offset,(2<<26)|((symbols[symbol]>>2)&0x3ffffff),0)
        hooks.append({'address':at,'original':guard,'symbol':symbol})
    report={'records':records,'extra_glyphs':missing,'extra_glyph_bytes':len(font),'runtime_address':address,'runtime_bytes':len(code),
        'symbols':symbols,'hooks':hooks,'free_bytes':sum(b-a for a,b in pool.free),'native_gameplay_verification':'pending'}
    (ROOT/'analysis/field-catalog-insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return nar,script,overlay
