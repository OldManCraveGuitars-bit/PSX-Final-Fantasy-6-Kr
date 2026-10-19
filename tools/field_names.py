"""Translate default names and expand player-composed names in field dialogue."""
import json,struct,subprocess
from textcodec import ROOT
from korean_codec import normalize,encode,font_index,CONTROL

NAME_FIXES={13:'우마로',21:'모루루',27:'즈모모그',60:'페타페타'}

def default_names():
    rows=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    return [normalize(NAME_FIXES.get(i,rows[str(i)]['translation'])) for i in range(64)]

def patch(nar,overlay,mapping,assigned):
    sources=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))[:64]
    translated=default_names();entries={};ordered=[]
    for row,text in zip(sources,translated):
        source=bytes.fromhex(row['original_hex']);data=encode(text,mapping)
        if len(data)>12:raise ValueError(('Default name exceeds native expansion buffer',text))
        if source in entries and entries[source]!=data:raise ValueError('Ambiguous default name')
        entries[source]=data
        ordered.append(data)
    strings=bytearray();offsets=[];known={}
    for data in ordered:
        if data not in known:known[data]=len(strings);strings+=data+b'\0'
        offsets.append(known[data])
    if len(strings)>256:raise ValueError('Default-name byte offsets overflow')
    header='static const unsigned char kr_name_offsets[] __attribute__((section(".name_data")))={'+','.join(map(str,offsets))+'};\n'
    header+='static const unsigned char kr_translated_names[] __attribute__((section(".name_data")))={'+','.join(map(str,strings))+'};\n'
    question=encode('?',mapping)
    if len(question)!=2:raise ValueError('Field question-mark encoding changed')
    header+=f'#define KR_NAME_QUESTION_0 {question[0]}\n#define KR_NAME_QUESTION_1 {question[1]}\n'
    (ROOT/'work/field_name_data.h').write_text(header,'ascii')
    all_rows=json.loads((ROOT/'analysis/dialogue-native-layout.json').read_text('utf8'))+json.loads((ROOT/'translations/map-titles.json').read_text('utf8'))
    used_chars=set(normalize(''.join(CONTROL.sub('',x['translation']) for x in all_rows)+''.join(translated)))
    used_indices={font_index(mapping[c]) for c in used_chars if c in mapping and c!='\n'}
    code_indices=set(range(184,223));data_indices=set(range(51,64));hook_indices=set(range(1085,1100))
    if used_indices&(code_indices|data_indices|hook_indices):raise ValueError('Reserved name-runtime glyphs became visible')
    start=0x80194bd0+184*22;limit=0x80194bd0+223*22
    data_start=0x80194bd0+51*22;data_limit=0x80194bd0+64*22
    hook_start=(0x80194bd0+1085*22+3)&~3;hook_limit=0x80194bd0+1100*22
    elf=ROOT/'work/field-name.elf';binfile=ROOT/'work/field-name.bin';tool=ROOT/'references/psx-toolchain/bin'
    script=f'OUTPUT_ARCH(mips)\nENTRY(kr_field_name)\nSECTIONS {{ .name_data 0x{data_start:08x} : SUBALIGN(1) {{ *(.name_data) }} .text 0x{start:08x} : SUBALIGN(4) {{ *(.text .text.*) }} .rodata : SUBALIGN(4) {{ *(.rodata .rodata.*) }} .name_hooks 0x{hook_start:08x} : {{ *(.name_hooks) }} /DISCARD/ : {{ *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }} }}\n'
    (ROOT/'work/field-name.ld').write_text(script,'ascii')
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float',
        '-mno-abicalls','-fno-pic','-G0','-ffreestanding','-fno-builtin','-Os','-falign-functions=4','-falign-loops=4','-Wall','-Wextra','-Werror',
        '-nostdlib',f'-I{ROOT.as_posix()}/work',f'-Wl,-T{ROOT.as_posix()}/work/field-name.ld,--build-id=none',
        '-o',str(elf),str(ROOT/'native/field_name.c'),str(ROOT/'native/field_name_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(binfile)],check=True)
    # Read the two allocated sections independently; the binary between them
    # contains visible font glyphs and must remain byte-identical.
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','--only-section=.name_data',str(elf),str(ROOT/'work/field-name-data.bin')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','--only-section=.text','--only-section=.rodata',str(elf),str(ROOT/'work/field-name-code.bin')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','--only-section=.name_hooks',str(elf),str(ROOT/'work/field-name-hooks.bin')],check=True)
    data=(ROOT/'work/field-name-data.bin').read_bytes();code=(ROOT/'work/field-name-code.bin').read_bytes();hooks=(ROOT/'work/field-name-hooks.bin').read_bytes()
    if start+len(code)>limit or data_start+len(data)>data_limit or hook_start+len(hooks)>hook_limit:raise ValueError(('Field name-runtime allocation overflow',len(code),limit-start,len(data),data_limit-data_start,len(hooks),hook_limit-hook_start))
    nar[start-0x80130000:start-0x80130000+len(code)]=code
    nar[data_start-0x80130000:data_start-0x80130000+len(data)]=data
    nar[hook_start-0x80130000:hook_start-0x80130000+len(hooks)]=hooks
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:symbols[fields[2]]=int(fields[0],16)&0xffffffff
    for address,symbol in [(0x80102d78,'kr_field_hchar'),(0x80102ea4,'kr_field_char')]:
        struct.pack_into('<II',overlay,address-0x800c8000,(2<<26)|((symbols[symbol]>>2)&0x3ffffff),0)
    report={'runtime_address':hex(start),'runtime_bytes':len(code),'capacity':limit-start,'data_address':hex(data_start),'data_bytes':len(data),'hook_address':hex(hook_start),'hook_bytes':len(hooks),
        'default_names':len(sources),'unique_default_names':len(entries),'symbols':symbols,
        'cache_address':'0x80036000','save_mirror':'0x80030700','dynamic_font_indices':[1152,1247],
        'field_native_verification':'pending'}
    (ROOT/'analysis/field-name-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return nar,overlay
