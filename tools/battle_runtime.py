"""Build the battle-specific Korean atlas and initial fixed-name output hooks."""
import json,struct,subprocess
from textcodec import ROOT
from korean_codec import raster,CONTROL,normalize
from small_text import encode_small,allocate_aliases,ascii_glyphs,icon_codes
from pac import compress,decompress

def compile_runtime():
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/battle-runtime.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib',
        f'-Wl,-T{ROOT.as_posix()}/native/battle-runtime.ld,--build-id=none','-o',str(elf),
        str(ROOT/'native/battle_runtime.c'),str(ROOT/'native/battle_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(ROOT/'work/battle-runtime.bin')],check=True)
    symbols={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:symbols[fields[2]]=int(fields[0],16)&0xffffffff
    return (ROOT/'work/battle-runtime.bin').read_bytes(),symbols

def prepare():
    originals=json.loads((ROOT/'analysis/fixed-catalog-original.json').read_text('utf8'))
    translated=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    selected=[]
    for category in ['character','spell','command','item','monster']:selected.extend(r for r in originals if r['category']==category)
    texts=[normalize(translated[str(r['id'])]['translation']).strip() for r in selected]
    all_texts=[normalize(r['translation']) for r in translated.values()]
    chars=sorted(c for c in set(''.join(CONTROL.sub('',s) for s in all_texts)) if ord(c)>127)
    slots=[i for i in range(512,1023) if i&255!=255]+list(range(376,448))
    if len(chars)>len(slots):raise ValueError('Battle small font overflow')
    mapping=dict(zip(chars,slots));font=bytearray(4672)
    for c,tile in mapping.items():
        image=raster(c,small=True)
        for y in range(8):
            index=tile-376 if tile<512 else 72+tile-512
            font[index*8+y]=sum(0x80>>x for x in range(8) if image.getpixel((x,y)))
    resource=bytearray(0x3c00)
    aliases=allocate_aliases(mapping);unique={};cursor=0x1b58;records=[]
    for i,(r,text) in enumerate(zip(selected,texts)):
        stream=encode_small(text,mapping,aliases)+b'\0'
        if stream not in unique:
            unique[stream]=cursor;resource[cursor:cursor+len(stream)]=stream;cursor+=len(stream)
        struct.pack_into('<I',resource,0xf00+i*4,0x80197c00+unique[stream])
        records.append({'id':i,'source_id':r['id'],'category':r['category'],'index':r['index'],'translation':text,'hex':stream.hex()})
    packed_font=compress(bytes(font))
    if cursor>0x3200:raise ValueError(('Battle dictionary allocation overflow',cursor,0x3200))
    # The large-text allocator supplies the packed atlas address. The freed
    # prefix area 0x3200..0x3a00 maps small tile IDs to the large native font.
    (ROOT/'work/battle-korean-font.pac').write_bytes(packed_font)
    for c,code in aliases.items():struct.pack_into('<H',resource,0x3a00+(code-0x80)*2,mapping[c])
    resource[0x3b00:0x3b80]=ascii_glyphs();icons,controls=icon_codes()
    for name,code in icons.items():resource[0x3b80+code-2]=controls[name]
    code,symbols=compile_runtime()
    if len(code)>0xf00:raise ValueError(('Battle name runtime overflow',len(code),0xf00))
    resource[:len(code)]=code
    (ROOT/'work/battle-korean-persistent.bin').write_bytes(resource)
    (ROOT/'work/battle-korean-font.bin').write_bytes(font)
    overlay=bytearray((ROOT/'work/decompressed/BTL/BATTLE.PAC').read_bytes());hooks=[]
    for address,symbol,guard in [(0x80156820,'kr_battle_draw','e0ffbd272158a000'),
        (0x800d5420,'kr_battle_monster_hook','1200a2970780033c'),
        (0x800d5684,'kr_battle_command_hook','1200a2970780033c'),
        (0x800d3490,'kr_battle_spell_list_hook','1200a2970780033c'),
        (0x800d3708,'kr_battle_spell_short_hook','1200a2970780033c'),(0x800d5b3c,'kr_battle_spell_menu_hook','1200a2970780033c'),
        (0x800d31f0,'kr_battle_item_list_hook','1200a2970780033c'),(0x800d5904,'kr_battle_item_menu_hook','1200a2970780033c'),
        (0x800d3950,'kr_battle_monster_list_hook','1200a2970780033c'),(0x800d4b40,'kr_battle_character','e0ffbd270280053c'),
        (0x800f90d4,'kr_battle_name_color_1','963b22a01200a297'),(0x800f929c,'kr_battle_name_color_2','963b22a000008390'),
        (0x801568b4,'kr_battle_row_1','21c000001f008230'),(0x80156b90,'kr_battle_row_2','c270040021c00000'),
        (0x8015692c,'kr_battle_cell_1','ffff03316b006210'),(0x80156bf4,'kr_battle_cell_2','ffff033151006210'),
        (0x80156954,'kr_battle_x_1','212042020f000331'),(0x80156c1c,'kr_battle_x_2','212042020f000331'),
        (0x80156ac4,'kr_battle_page_1','14004a251980023c'),(0x80156d24,'kr_battle_page_2','1400a5241980023c'),
        (0x801516e4,'kr_battle_frame','e46b22a40380033c')]:
        at=address-0x800c8000
        if overlay[at:at+8].hex()!=guard:raise ValueError(('Battle hook guard',hex(address),overlay[at:at+8].hex()))
        # 801517b4 loops directly to 801516e8, the second patched word.
        # Keep its original LUI: a NOP here makes later window slots read
        # their enable flags through the previous iteration's v1 register.
        delay=0x3c038003 if symbol=='kr_battle_frame' else 0
        struct.pack_into('<II',overlay,at,(2<<26)|((symbols[symbol]>>2)&0x3ffffff),delay)
        hooks.append({'address':address,'bytes':overlay[at:at+8].hex(),'symbol':symbol})
    # Native BG3 uploads no longer touch the private Korean page. Reuploading
    # the entire atlas after each canvas update caused severe magic-menu lag.
    (ROOT/'work/battle-overlay-small-names.bin').write_bytes(overlay)
    report={'entries':len(records),'glyphs':len(mapping),'dictionary_bytes':cursor-0x1b58,'runtime_bytes':len(code),
        'resource_address':'0x80197c00','resource_bytes':len(resource),'font_address':'assigned by battle large-text allocator',
        'font_bytes':len(font),'font_packed_bytes':len(packed_font),
        'hooks':hooks,'symbols':symbols,'records':records,
        'mapping':mapping,'native_gameplay_verification':'pending','integrated_into_disc':False}
    (ROOT/'analysis/battle-small-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    print({k:v for k,v in report.items() if k not in ['mapping','records','symbols','hooks']})
    return resource,font,overlay,report
def patch(changes):
    resource,font,overlay,report=prepare()
    data=bytearray((ROOT/'work/extracted/BTL/FF6_BTL.BIN').read_bytes())
    data+=bytes(0x45000-len(data))
    from battle_big_text import patch as patch_big
    data,resource,overlay,big_report=patch_big(data,resource,overlay,report)
    (ROOT/'work/battle-korean-persistent.bin').write_bytes(resource)
    (ROOT/'work/battle-overlay-small-names.bin').write_bytes(overlay)
    (ROOT/'work/battle-korean-data.bin').write_bytes(resource+data)
    source=(ROOT/'work/extracted/BTL/BATTLE.PAC').read_bytes()
    packed=compress(bytes(overlay));assert decompress(packed)[0]==overlay
    capacity=(len(source)+2047)//2048*2048
    if len(packed)>capacity:raise ValueError(('Battle overlay allocation overflow',len(packed),capacity))
    data=resource+data
    exe=bytearray(changes['SLPM_861.98'])
    if exe[0x1f6c:0x1f74]!=bytes.fromhex('04000f3c0050ef35'):raise ValueError('Battle read-size guard')
    struct.pack_into('<II',exe,0x1f6c,0x3c0f0004,0x35ef8c00)
    if exe[0x30a4:0x30a8]!=bytes.fromhex('00b8a534'):raise ValueError('Battle data destination guard')
    # Retain the original CD destination until the compressed battle overlay
    # is consumed. movie_subtitles.patch installs the resident forward move.
    if exe[0x2bca4:0x2bca8]!=bytes.fromhex('00321400'):raise ValueError('Battle native MSF guard')
    lba=122071;minute,remainder=divmod(lba+150,4500);second,frame=divmod(remainder,75)
    bcd=lambda n:n//10*16+n%10
    exe[0x2bca4:0x2bca8]=bytes((bcd(minute),bcd(second),bcd(frame),0))
    changes=dict(changes);changes.update({'BTL/BATTLE.PAC':packed+bytes(max(0,len(source)-len(packed))),
        'BTL/FF6_BTL.BIN':bytes(data),'SLPM_861.98':bytes(exe)})
    report.update(integrated_into_disc=True,overlay_packed_bytes=len(packed),data_file_bytes=len(data),
        data_load_address='0x80197c00',data_original_address='0x8019b800',data_relocation='DUMMY1.DAT',
        data_CD_staging='0x8019b800..0x801e4400; shift after both reads and overlay decompression',
        music_stream_buffer='0x801ed800..0x801fd800; preserved')
    (ROOT/'analysis/battle-small-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return changes
if __name__=='__main__':prepare()
