"""Losslessly pack native field dialogue without borrowing UI/font storage."""
import json,struct,subprocess
from textcodec import ROOT
from omake_runtime import huffman

BUFFER=0x80033000

def pack(streams,main_count):
    table,compressed=huffman(streams)
    packed=bytearray();offsets=[]
    for i,stream in enumerate(streams):
        data=compressed[stream]
        if i<main_count and len(packed)<65536 and len(packed)+len(data)>65536:
            packed+=bytes(65536-len(packed))
        offsets.append(len(packed));packed+=data
    main_bytes=offsets[main_count] if main_count<len(offsets) else len(packed)
    # Persist the exact streams for exhaustive native decoding verification.
    report={'records':len(streams),'main_records':main_count,'raw_bytes':sum(map(len,streams)),
        'packed_bytes':len(packed),'buffer_address':BUFFER,'buffer_bytes':1024,
        'max_expanded_bytes':max(map(len,streams)),'offsets':offsets,
        'streams':[x.hex() for x in streams],'font_or_graphics_storage_used':False}
    return packed,offsets[:main_count],offsets[main_count:],main_bytes,table,report

def insert_runtime(script,used,table,report):
    start=(used+3)&~3;address=0x801a6200+start
    values=struct.unpack('<176H',table)
    (ROOT/'work/dialogue_huffman.h').write_text('static const unsigned short kr_dialogue_huffman[176]={'+','.join(map(str,values))+'};\n','ascii')
    linker=ROOT/'work/dialogue-runtime.ld'
    linker.write_text(f'OUTPUT_ARCH(mips)\nENTRY(kr_dialogue_dispatch)\nSECTIONS {{ . = 0x{address:08x}; .text : {{ *(.text .text.*) }} .rodata : {{ *(.rodata .rodata.*) }} /DISCARD/ : {{ *(.MIPS.abiflags .reginfo .pdr .comment .gnu.attributes) }} }}\n','ascii')
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/dialogue-runtime.elf';binary=ROOT/'work/dialogue-runtime.bin'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib',f'-I{ROOT.as_posix()}/work',
        f'-Wl,-T{linker.as_posix()},--build-id=none','-o',str(elf),str(ROOT/'native/dialogue_runtime.c'),str(ROOT/'native/dialogue_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(binary)],check=True)
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        f=line.split()
        if len(f)==3:symbols[f[2]]=int(f[0],16)&0xffffffff
    code=binary.read_bytes()
    if start+len(code)>0x1afa0:raise ValueError('Dialogue decoder allocation overflow')
    script[start:start+len(code)]=code
    report.update(runtime_address=address,runtime_bytes=len(code),symbols=symbols)
    (ROOT/'analysis/dialogue-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return start+len(code),symbols
