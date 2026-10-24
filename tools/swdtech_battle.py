"""Add saved-name conversion without relocating any existing battle resource."""
import json,struct,subprocess
from textcodec import ROOT
from korean_codec import font_index,raster
CODE=0x801dceb0;TABLE=0x801dd200;BASE=0x80197c00;FONT=0x801d68f8
def patch(data,overlay):
    before=bytes(data);old_overlay=bytes(overlay)
    data=bytearray(data);overlay=bytearray(overlay)
    report=json.loads((ROOT/'work/snapshots/v086-before-bushido-fix/analysis/battle-big-text-insertion.json').read_text('utf8'))
    rows=json.loads((ROOT/'translations/swdtech-characters.ko.json').read_text('utf8'))
    mapping={k:bytes.fromhex(v) for k,v in report['mapping'].items()}
    assert rows['239']['translation']==rows['255']['translation']==' '
    used={font_index(v) for v in mapping.values()}|set(range(901,911))
    free=iter(i for i in range(911,930) if i not in used)
    added={}
    for c in sorted({r['translation'] for r in rows.values()}-mapping.keys()):
        i=next(free);bank,k=divmod(i-224,256);mapping[c]=bytes((0x1c+bank,k));added[c]=i
        im=raster(c);glyph=b''.join(struct.pack('<H',sum(1<<(11-x) for x in range(12) if im.getpixel((x,y)))) for y in range(11))
        at=FONT-BASE+i*22;data[at:at+22]=glyph
    for c in range(256):
        value=mapping[rows.get(str(c),{'translation':' '})['translation']]
        assert len(value)<=2
        struct.pack_into('<H',data,TABLE-BASE+c*2,int.from_bytes(value,'little'))
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/swdtech-battle.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib',f'-Wl,-T{ROOT.as_posix()}/native/swdtech-battle.ld,--build-id=none',
        '-o',str(elf),str(ROOT/'native/swdtech_battle.c'),str(ROOT/'native/swdtech_battle_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(ROOT/'work/swdtech-battle.bin')],check=True)
    code=(ROOT/'work/swdtech-battle.bin').read_bytes();assert CODE+len(code)<=TABLE
    assert CODE>=0x8019b800+report['small_lut_offset']+2496 and TABLE+512<=FONT+1248*22
    data[CODE-BASE:CODE-BASE+len(code)]=code
    syms={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        p=line.split()
        if len(p)==3:syms[p[2]]=int(p[0],16)&0xffffffff
    at=0x801275b4-0x800c8000;assert overlay[at:at+8]==bytes.fromhex('0780023c6cc1428c')
    struct.pack_into('<II',overlay,at,(2<<26)|((syms['kr_swdtech_battle_hook']>>2)&0x3ffffff),0)
    bonus=json.loads((ROOT/'translations/omake-manual.json').read_text('utf8'))
    for i,end in enumerate([0x90,0x9a,0xa0,0xd5,0xe9,0x9d,0xec,0xc2]):
        assert ''.join(rows[str(c)]['translation'] for c in [0xd3,0xaa,0x9e,0xef,end])==bonus[str(570+i)]
    report['mapping']={c:v.hex() for c,v in mapping.items()};report['symbols'].update(syms)
    report['glyphs']+=len(added)
    allowed=[(FONT-BASE+i*22,FONT-BASE+(i+1)*22) for i in added.values()]+[(CODE-BASE,CODE-BASE+len(code)),(TABLE-BASE,TABLE-BASE+512)]
    assert all(a==b or any(lo<=i<hi for lo,hi in allowed) for i,(a,b) in enumerate(zip(before,data)))
    assert overlay[:at]==old_overlay[:at] and overlay[at+8:]==old_overlay[at+8:]
    report['bushido_names']={'count':8,'source':'translations/omake-manual.json:570..577','custom_character_table':TABLE-0x8019b800,
        'custom_characters':249,'runtime_address':CODE,'runtime_bytes':len(code),'added_glyphs':added,
        'original_directory_font_assignments_and_renderers_preserved':True,'saved_name_bytes_unchanged':True}
    (ROOT/'analysis/battle-big-text-insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return data,overlay,report
