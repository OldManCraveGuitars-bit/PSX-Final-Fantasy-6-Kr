"""Build the extended Galmuri7 atlas and native menu output hooks."""
import json,struct,subprocess
from pathlib import Path
from textcodec import ROOT
from korean_codec import raster,CONTROL,normalize
from small_ui import LABELS
from pac import compress,decompress
from small_text import patch_labels

MENU_SIZE=0x68000
MENU_READ_SIZE=0x60000
ATLAS=0x26000
CODE=0x2e000
LABEL_DATA=0x25050
RELOCATE_LBA=114063

def compile_runtime(field_cache=False):
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/menu-runtime.elf'
    linker=ROOT/'native/menu-runtime.ld'
    if field_cache:
        linker=ROOT/'work/menu-cache-runtime.ld'
        linker.write_text((ROOT/'native/menu-runtime.ld').read_text('utf8').replace('0x8019f400','0x8019f500'),'utf8')
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float',
        '-mno-abicalls','-fno-pic','-G0','-ffreestanding','-fno-builtin','-O2','-Wall','-Wextra','-Werror',
        '-nostdlib',*(['-DFF6_FIELD_CACHE','-fno-tree-loop-distribute-patterns'] if field_cache else []),'-I'+str(ROOT/'work'),f'-Wl,-T{linker.as_posix()},--build-id=none','-o',str(elf),
        str(ROOT/'native/small_runtime.c'),str(ROOT/'native/small_hooks.S'),
        str(ROOT/'native/hangul_name.c'),str(ROOT/'native/name_editor.c'),str(ROOT/'native/menu_big_text.c'),str(ROOT/'native/boost_settings.c'),str(ROOT/'native/boost_menu_hooks.S')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','-R','.bigtext','-R','.boost',str(elf),str(ROOT/'work/menu-runtime.bin')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','-j','.bigtext',str(elf),str(ROOT/'work/menu-big-runtime.bin')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary','-j','.boost',str(elf),str(ROOT/'work/menu-boost-runtime.bin')],check=True)
    syms={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:syms[fields[2]]=int(fields[0],16)&0xffffffff
    return (ROOT/'work/menu-runtime.bin').read_bytes(),syms

def glyph_pixels(data):
    return [[((data[y*2]>>(7-x))&1)|(((data[y*2+1]>>(7-x))&1)<<1) for x in range(8)] for y in range(8)]

def build_atlas(menu):
    pixels=bytearray(256*256)
    def put(index,glyph):
        u=(index&15)*8+((index&512)>>2);v=(index&0x1f0)>>1
        for y in range(8):pixels[(v+y)*256+u:(v+y)*256+u+8]=bytes(glyph[y])
    for i in range(256):put(i,glyph_pixels(menu[0xa400+i*16:0xa410+i*16]))
    texts=[''.join(x[2] for x in LABELS),'새 게임']
    from boost_settings import texts as boost_texts
    texts.extend(r['translation'] for r in boost_texts().values())
    for filename in ['fixed-catalog.ko.json','menu-labels.ko.json','menu-jobs.ko.json']:
        rows=json.loads((ROOT/'translations'/filename).read_text('utf8'))
        texts.extend(x['translation'] for x in rows.values())
    chars=sorted(set(''.join(CONTROL.sub('',normalize(t)) for t in texts)))
    chars=[c for c in chars if ord(c)>127]
    from small_text import ascii_glyphs
    original_ascii=ascii_glyphs()
    missing_ascii={c for row in boost_texts().values() for c in row['translation']
                   if ord(c)<128 and c!=' ' and original_ascii[ord(c)]==255}
    chars=sorted(set(chars)|missing_ascii)
    # The name editor has its own 51-jamo font resource.
    if len(chars)>767:raise ValueError(f'Small font capacity exceeded: {len(chars)}')
    slots=[x for x in range(256,1023) if x&255!=255]
    if len(chars)>len(slots):raise ValueError('Small-font terminator reservation overflow')
    mapping=dict(zip(chars,slots))
    for c,index in mapping.items():
        im=raster(c,small=True);glyph=[]
        for y in range(8):
            row=[]
            for x in range(8):
                fg=im.getpixel((x,y))
                shadow=(x>0 and im.getpixel((x-1,y))) or (y>0 and im.getpixel((x,y-1))) or (x>0 and y>0 and im.getpixel((x-1,y-1)))
                row.append(3 if fg else 1 if shadow else 0)
            glyph.append(row)
        put(index,glyph)
    packed=bytes(pixels[i]|(pixels[i+1]<<4) for i in range(0,len(pixels),2))
    return packed,mapping

def patch(changes):
    menu=bytearray(changes['HAR/MENUMENU.BIN'])
    overlay=bytearray(decompress(changes['HAR/HARATA.PAC'])[0])
    atlas,mapping=build_atlas(menu)
    from boost_settings import prepare_menu
    prepare_menu(mapping);code,symbols=compile_runtime()
    if CODE+len(code)>0x30800:raise ValueError('Menu runtime allocation overflow')
    menu+=bytes(MENU_SIZE-len(menu));menu[ATLAS:ATLAS+len(atlas)]=atlas;menu[CODE:CODE+len(code)]=code
    boost=(ROOT/'work/menu-boost-runtime.bin').read_bytes()
    if len(boost)>0xc00:raise ValueError(('Boost menu runtime allocation overflow',len(boost),0xc00))
    menu[0x5f400:0x5f400+len(boost)]=boost
    pointer_replacements={}
    menu,overlay=patch_labels(menu,overlay,mapping)
    from menu_big_text import patch as patch_big_text
    menu,overlay=patch_big_text(menu,overlay,mapping)
    names=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    name_fixes={13:'우마로',21:'모루루',27:'즈모모그',60:'페타페타'}
    for i in range(64):
        text=normalize(name_fixes.get(i,names[str(i)]['translation']))
        if len(text)>6:raise ValueError(('Default name too long',i,text))
        encoded=text.encode('utf-16le')+bytes((6-len(text))*2)
        menu[0x25400+i*12:0x2540c+i*12]=encoded
    font_blocks=(ROOT/'work/korean-name-fonts.bin').read_bytes()
    if 0x32000+len(font_blocks)>0x4f600:raise ValueError('Name-font resource allocation overflow')
    menu[0x32000:0x32000+len(font_blocks)]=font_blocks
    for filename,at,limit in [('korean-name-jamo.bin',0x4f600,0x50000),('korean-name-ascii.bin',0x52000,0x53000)]:
        data=(ROOT/'work'/filename).read_bytes()
        if at+len(data)>limit:raise ValueError('Name glyph allocation overflow')
        menu[at:at+len(data)]=data
    from hangul_name import LEADS,VOWELS
    jamo=json.loads((ROOT/'analysis/name-font-blocks.json').read_text('utf8'))['jamo']
    keys=LEADS+[' ']+VOWELS+[' ']*9+list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')+[' ']*4+list('0123456789')+list('.-_!?')+[' ']*5
    assert len(keys)==100
    grid=[]
    for c in keys*2:
        if c in jamo:grid.append(0x60+jamo.index(c))
        elif 'A'<=c<='Z':grid.append(0xc0+ord(c)-ord('A'))
        elif '0'<=c<='9':grid.append(0x53+ord(c)-ord('0'))
        elif c in '.-_!?':grid.append(0xda+'.-_!?'.index(c))
        else:grid.append(0xff)
    if source_grid:=overlay[0x653bc:0x653c4]:
        if source_grid!=bytes.fromhex('8b8d898f91353739'):raise ValueError('Native name-grid guard')
    overlay[0x653bc:0x65484]=bytes(grid)
    menu[0x25800:0x25990]=''.join(keys*2).encode('utf-16le')
    hooks=[(0x8010fda4,'kr_upload_small',True),
        (0x8010e280,'kr_restore_small_after_save',True),
        (0x800f5ae0,'kr_label_hook',False),
        (0x800f5fc8,'kr_rich_label_hook',False),
        (0x80120144,'kr_sprite_begin',False),
        (0x801204a0,'kr_sprite_page_1',False),(0x80120788,'kr_sprite_page_2',False),
        (0x8012028c,'kr_row_start_1',False),(0x80120580,'kr_row_start_2',False),
        (0x80120348,'kr_cell_1',False),(0x80120634,'kr_cell_2',False),
        (0x80120380,'kr_x_1',False),(0x8012066c,'kr_x_2',False),
        (0x800fd35c,'kr_name_begin',True),(0x800fd488,'kr_name_keys_hook',False),
        (0x8011aeb8,'kr_big_get_letter',False)]
    hooks.extend([(0x800f45b0,'kr_boost_config_init',True),(0x800f45d4,'kr_boost_config_tick',True)])
    hooks.append((0x800de850,'kr_config_magic_hook',False))
    source=(ROOT/'work/decompressed/HAR/HARATA.PAC').read_bytes()
    guards={0x8010fda4:'6b3f040800000000',0x8010e280:'4f7e040c00000000',
        0x800f45b0:'2725030c00000000',0x800f45d4:'3234030c00000000',
        0x800de850:'0780023c6cc1428c',
        0x800f5ae0:'c8ffbd273400bfaf',
        0x80120144:'a8ffbd274800b6af',0x801204a0:'140008251380023c',0x80120788:'140008251380023c'}
    for address,symbol,link in hooks:
        at=address-0x800c8000
        if address in guards and source[at:at+8].hex()!=guards[address]:raise ValueError(('Runtime hook guard',hex(address),source[at:at+8].hex()))
        if overlay[at:at+8]!=source[at:at+8]:raise ValueError('Overlapping overlay mutation')
        instruction=((3 if link else 2)<<26)|((symbols[symbol]>>2)&0x3ffffff)
        struct.pack_into('<II',overlay,at,instruction,0)
    # Description text is recopied every frame, before the native task checks
    # its next byte for a terminator. Expand references as the loader returns.
    at=0x800f1bd4-0x800c8000
    if source[at:at+8]!=bytes.fromhex('2800bd270800e003'):raise ValueError('Description loader return guard')
    struct.pack_into('<II',overlay,at,(2<<26)|((symbols['kr_big_expand']>>2)&0x3ffffff),0x27bd0028)
    packed=compress(bytes(overlay));capacity=len(changes['HAR/HARATA.PAC'])
    if len(packed)>capacity:raise ValueError('Menu overlay capacity exceeded')
    exe=bytearray((ROOT/'work/extracted/SLPM_861.98').read_bytes())
    if exe[0x1f3c:0x1f44].hex()!='0200093c00582935':raise ValueError('Menu read-size guard')
    # The final 32 KiB is a write-only GPU packet pool. Every used packet is
    # written in full before it is linked, so reading its zero padding wastes
    # sixteen CD sectors on each menu entry.
    if any(menu[MENU_READ_SIZE:]):raise ValueError('Static data entered the menu packet pool')
    struct.pack_into('<II',exe,0x1f3c,0x3c090000|(MENU_READ_SIZE>>16),0x35290000|(MENU_READ_SIZE&65535))
    if exe[0x2bc84:0x2bc88]!=bytes.fromhex('00264700'):raise ValueError('Native CD-address guard')
    minute,remainder=divmod(RELOCATE_LBA+150,4500);second,frame=divmod(remainder,75)
    bcd=lambda n:(n//10)*16+n%10
    exe[0x2bc84:0x2bc88]=bytes((bcd(minute),bcd(second),bcd(frame),0))
    # The original fast return restores a 128 KiB VRAM backup from 80168000.
    # Extended menu assets occupy that buffer. Reload the original field files
    # from CD and rebuild the VRAM backup before returning to the field instead.
    for at,expected in [(0x2ca0,'2f000212'),(0x2e08,'13000212')]:
        if exe[at:at+4].hex()!=expected:raise ValueError('Native field re-entry guard')
        exe[at:at+4]=bytes(4)
    changes=dict(changes);changes.update({'HAR/MENUMENU.BIN':bytes(menu),'HAR/HARATA.PAC':packed+bytes(capacity-len(packed)),'SLPM_861.98':bytes(exe)})
    report={'font':'Galmuri7','atlas_tiles':1024,'additional_glyphs':len(mapping),'space_advance':4,
        'sprite_page_pool':{'address':'0x801a0000','bytes':0x8000,'buffers':2,'sprites_per_buffer':1024},
        'menu_load_address':'0x80140000','menu_read_bytes':MENU_READ_SIZE,'runtime_bytes':len(code),
        'field_reentry':'full CD reload, original VRAM backup rebuilt',
        'save_menu_reentry':'primary extended-font page restored after final original font-page rebuild in task 8010e1ec',
        'mapping':mapping,'symbols':symbols,'label_pointers':pointer_replacements,
        'native_ui_verification':'pending','name_entry_integration':'native hooks compiled; runtime verification pending',
        'name_cache':{'address':'0x80036000','save_mirror':'0x80030700','bytes':3088,'within_existing_save_payload':True},
        'name_grid_keys':keys,'name_limit':6}
    (ROOT/'analysis/small-runtime.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    return changes
