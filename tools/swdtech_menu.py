"""Dedicated fixed-cell picker and proportional finished-name glyph hooks."""
import json,struct,subprocess
from textcodec import ROOT
from korean_codec import font_index

def patch(menu,overlay,mapping):
    rows=json.loads((ROOT/'translations/swdtech-characters.ko.json').read_text('utf8'))
    assert rows['239']['translation']==rows['255']['translation']==' ', 'SwdTech space/padding must remain half-width spaces'
    for c in range(256):
        text=rows.get(str(c),{'translation':' '})['translation']
        assert len(text)==1,(c,text)
        struct.pack_into('<H',menu,0x5d000+c*2,font_index(mapping[text]))
    tool=ROOT/'references/psx-toolchain/bin';elf=ROOT/'work/swdtech-menu.elf'
    subprocess.run([str(tool/'mipsel-none-elf-gcc.exe'),'-march=r3000','-mabi=32','-msoft-float','-mno-abicalls','-fno-pic','-G0',
        '-ffreestanding','-fno-builtin','-Os','-Wall','-Wextra','-Werror','-nostdlib',
        f'-Wl,-T{ROOT.as_posix()}/native/swdtech-menu.ld,--build-id=none','-o',str(elf),str(ROOT/'native/swdtech_menu.c')],check=True)
    subprocess.run([str(tool/'mipsel-none-elf-objcopy.exe'),'-O','binary',str(elf),str(ROOT/'work/swdtech-menu.bin')],check=True)
    code=(ROOT/'work/swdtech-menu.bin').read_bytes();assert len(code)<=0x1e00
    menu[0x5d200:0x5d200+len(code)]=code
    syms={}
    for line in subprocess.check_output([str(tool/'mipsel-none-elf-nm.exe'),'-n',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:syms[fields[2]]=int(fields[0],16)&0xffffffff
    hooks=[]
    for address,symbol in [(0x8011a0b0,'kr_swdtech_name'),(0x800e4e08,'kr_swdtech_cell'),(0x800e5a64,'kr_swdtech_cell')]:
        at=address-0x800c8000;old=(3<<26)|((0x8011b048>>2)&0x3ffffff)
        assert struct.unpack_from('<I',overlay,at)[0]==old,hex(address)
        struct.pack_into('<I',overlay,at,(3<<26)|((syms[symbol]>>2)&0x3ffffff))
        hooks.append({'address':address,'symbol':symbol})
    report={'characters':len(rows),'table_offset':0x5d000,'code_offset':0x5d200,'code_bytes':len(code),'symbols':syms,'hooks':hooks,
            'name_space_pixels':6,'picker_cell_pixels':12,'saved_name_bytes_unchanged':True}
    (ROOT/'analysis/v087-swdtech-menu-insertion.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    return menu,overlay
