"""Save-preview fonts use their own blank texture rectangle and file buffer."""
import json,struct,subprocess
from korean_codec import ROOT,normalize,raster

ADDRESS=0x80036c20
LIMIT=0x80037800

def compile_runtime(overlay,original,font_offset):
    rows=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    names=[normalize(rows[str(i)]['translation']) for i in range(64)]
    assert all(len(s)<=6 for s in names)
    defaults=b''.join(s.encode('utf-16le')+bytes((6-len(s))*2) for s in names)
    chars=sorted(set(''.join(names))|{'?'})
    glyphs=bytearray()
    for c in chars:
        im=raster(c,True);glyphs+=struct.pack('<H',ord(c))
        glyphs+=bytes(sum(128>>x for x in range(8) if im.getpixel((x,y))) for y in range(8))
    assert len(defaults)==768 and len(glyphs)<=0x3b8
    overlay[0xc58:0xc58+768]=defaults
    font_offset=(font_offset+3)&~3
    if not 0x1b454<=font_offset or font_offset+len(glyphs)>0x1c194:raise ValueError('PSX name font exceeds the reserved text pool')
    if any(overlay[font_offset:font_offset+len(glyphs)]):raise ValueError('PSX name font overlaps translated text or runtime helpers')
    overlay[font_offset:font_offset+len(glyphs)]=glyphs
    font_address=0x800c8000+font_offset
    (ROOT/'work/psx-name-data.h').write_text(f'#define PSX_NAME_GLYPHS {len(chars)}\n#define PSX_NAME_FONT_ADDRESS 0x{font_address:08x}\n','ascii')
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/psx-name-runtime.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float',
        '-mno-abicalls','-fno-pic','-G0','-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror',
        '-nostdlib','-I'+str(ROOT/'work'),f'-Wl,-T{ROOT.as_posix()}/native/psx-name-runtime.ld,--build-id=none',
        '-o',str(elf),str(ROOT/'native/psx_name_preview.c'),str(ROOT/'native/psx_name_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(ROOT/'work/psx-name-runtime.bin')],check=True)
    code=(ROOT/'work/psx-name-runtime.bin').read_bytes()
    if ADDRESS+len(code)>LIMIT:raise ValueError(('PSX preview resident code overflow',len(code),LIMIT-ADDRESS))
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        f=line.split()
        if len(f)==3:symbols[f[2]]=int(f[0],16)&0xffffffff
    def hook(at,name,expected,jal=True):
        assert struct.unpack_from('<I',original,at)[0]==expected,(hex(at),hex(expected))
        struct.pack_into('<I',overlay,at,((3 if jal else 2)<<26)|((symbols[name]>>2)&0x3ffffff))
    hook(0x15ed0,'kr_psx_name',0x27bdffe0,False);overlay[0x15ed4:0x15ed8]=bytes(4)
    hook(0x3918,'kr_psx_glyph_page_reset',0xa5a20040,False)
    struct.pack_into('<I',overlay,0x391c,0xa5a20040)
    hook(0x3930,'kr_psx_half_space',0x94a20018,False)
    struct.pack_into('<I',overlay,0x3934,0x94a20018)
    hook(0x3f90,'kr_psx_literal_half_space',0x96420018,False)
    struct.pack_into('<I',overlay,0x3f94,0x96420018)
    overlay[0x15ed8:0x15f14]=bytes(0x3c)
    hook(0xe500,'kr_psx_card_read',0x0c010ebc)
    hook(0xe74c,'kr_psx_card_read',0x0c010ebc)
    hook(0xe564,'kr_psx_read_complete_hook',0x27bdffc0,False);overlay[0xe568:0xe56c]=bytes(4)
    for at in [0x1355c,0x136f8,0x13e04,0x16a18]:hook(at,'kr_psx_name_print',0x0c033014)
    assert struct.unpack_from('<I',original,0xebd0)[0]==0x34042000
    struct.pack_into('<I',overlay,0xebd0,0x34043000)
    report={'runtime_address':hex(ADDRESS),'runtime_bytes':len(code),'default_names':64,'glyphs':len(chars),
        'default_data':hex(0x800c8c58),'font_data':hex(font_address),'font_data_end':font_address+len(glyphs),
        'native_actor_script_table_preserved':True,
        'file_buffer_bytes':0x3000,'card_read_bytes':0x2000,'font_cache_bytes':4096,
        'dynamic_font_rectangle':{'x_words':512,'y':416,'width_words':64,'height':96},
        'font':'Galmuri7','space_pixels':4,'symbols':symbols,'native_verification':'pending'}
    (ROOT/'analysis/psx-name-preview-runtime.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    return report
