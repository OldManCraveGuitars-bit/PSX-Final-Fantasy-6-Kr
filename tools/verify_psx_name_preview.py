"""Exercise original PSX printf, per-file fonts and card-buffer guards in MIPS."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from emu import ROOT
from pac import decompress
from korean_codec import raster,normalize

def main():
    report=json.loads((ROOT/'analysis/psx-name-preview-runtime.json').read_text('utf8'));syms=report['symbols']
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0x38000,(ROOT/'work/extracted/SLPM_861.98').read_bytes()[0x800:])
    u.mem_write(0xc8000,decompress((ROOT/'work/modified/DEODIR/DEO.PAC').read_bytes())[0])
    u.mem_write(0x36c20,(ROOT/'work/psx-name-runtime.bin').read_bytes())
    u.mem_write(0xeeec0,struct.pack('<I',0x801a0000));u.mem_write(0x1a00b8,struct.pack('<I',0x801b0000))
    source=(ROOT/'work/kr-v024-card-after-write.mcr').read_bytes()[0x2000:0x4000]
    selected=source;uploads=[];reads=[]
    def ret(value=0):
        u.reg_write(UC_MIPS_REG_V0,value);u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
    def hook(cpu,address,size,user):
        at=address&0x1fffff
        if at==0x43af0:
            dest=u.reg_read(UC_MIPS_REG_A2)&0x1fffff;n=u.reg_read(UC_MIPS_REG_A3)
            assert dest==0x1b0000 and n==8192
            u.mem_write(dest,bytes(selected));reads.append(n);ret(1)
        elif at==0x5adb8:
            rect=struct.unpack('<4h',u.mem_read(u.reg_read(UC_MIPS_REG_A0)&0x1fffff,8))
            assert 512<=rect[0]<576 and 416<=rect[1]<=504 and rect[2:]==(2,8),rect
            bits=bytes(u.mem_read(u.reg_read(UC_MIPS_REG_A1)&0x1fffff,32));uploads.append((rect,bits));ret()
        elif at==0x5ab0c:ret()
        elif at==0x5437c:
            p=u.reg_read(UC_MIPS_REG_A0)&0x1fffff;n=0
            while u.mem_read(p+n,1)!=b'\0':n+=1
            ret(n)
    u.hook_add(UC_HOOK_CODE,hook)
    def invoke(name,args):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801ffffc)
        for reg,v in zip([UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3],args):u.reg_write(reg,v)
        if len(args)>4:u.mem_write(0x1ff010,struct.pack('<I',args[4]))
        u.emu_start(syms[name],0x801ffffc,count=1000000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801ffffc,(name,hex(u.reg_read(UC_MIPS_REG_PC)))
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    def string(at):return bytes(u.mem_read(at,28)).split(b'\0')[0]
    def decode(data):
        assert data.startswith(b'~K'),data
        return ''.join(chr(int(data[i:i+4],16)) for i in range(2,26,4)).rstrip('\0')
    expected=[];saved_fonts=[]
    for index in range(3):
        card=bytearray(source)
        if index:
            card[0x202:0x208]=b'\xff'*6;card[0x200]=index-1
        selected=bytes(card);u.mem_write(0x1a00ea,struct.pack('<H',index));u.mem_write(0xe8dc8,b'\x55'*512)
        u.mem_write(0x1b3000,b'\xa5'*64)
        invoke('kr_psx_card_read',[0,0x800c8940,0x800e8dc8,512,0])
        assert bytes(u.mem_read(0xe8dc8,512))==b'\x55'*512
        invoke('kr_psx_read_complete',[0x801a0000])
        for previous,snapshot in enumerate(saved_fonts):
            assert bytes(u.mem_read(0x1b2000+previous*192,192))==snapshot,'Another save overwrote this name font'
        saved_fonts.append(bytes(u.mem_read(0x1b2000+index*192,192)))
        data=bytes(u.mem_read(0xe8ec8,256));u.mem_write(0xea950+index*256,data)
        assert sum(data[:232])==struct.unpack_from('<I',data,232)[0]
        assert bytes(u.mem_read(0x1b3000,64))==b'\xa5'*64
        expected.append(decode(data[:28].split(b'\0')[0]))
    assert expected[1:]==['티나','록'],expected
    # A damaged original preview must remain damaged, not acquire a new valid
    # checksum when the name extension happens to be readable.
    broken=bytearray(source);broken[256]^=1;selected=bytes(broken)
    invoke('kr_psx_card_read',[0,0x800c8940,0x800e8dc8,512,0]);invoke('kr_psx_read_complete',[0x801a0000])
    assert bytes(u.mem_read(0xe8dc8,512))==selected[:512]
    # Exercise source controls, raw cache glyphs and the dedicated current-name
    # buffer, including the unknown heroine's original question marks.
    names=json.loads((ROOT/'translations/fixed-catalog.ko.json').read_text('utf8'))
    u.mem_write(0x36000,source[0x1300:0x1f10]);u.mem_write(0x2f850,b'\x08')
    default_glyph_cases=0
    for i in range(64):
        u.mem_write(0x2f600,bytes((i,0))+b'\xff'*6)
        invoke('kr_psx_name',[0x8002f602])
        text=normalize(names[str(i)]['translation'])
        for j,(_,bits) in enumerate(uploads[-6:]):
            char=text[j] if j<len(text) else ''
            im=raster(char,True) if char and char!=' ' else None
            actual=bytes(((bits[y*4+x//2]>>((x&1)*4))&15)==3 for y in range(8) for x in range(8))
            glyph_expected=bytes(bool(im.getpixel((x,y))) if im else False for y in range(8) for x in range(8))
            assert actual==glyph_expected,('Default name font bitmap changed',i,j,char)
            default_glyph_cases+=1
        if names[str(i)]['translation']:assert decode(string(0xe9c5c))==normalize(names[str(i)]['translation'])
        else:assert string(0xe9c5c)==b''
    u.mem_write(0x2f600,b'\0\0'+b'\xcb'*6);invoke('kr_psx_name',[0x8002f602]);assert decode(string(0xe9c5c))=='??????'
    cache=bytearray(source[0x1300:0x1f10]);text='한 글A!?'
    for i,c in enumerate(text):
        struct.pack_into('<H',cache,16+i*2,ord(c));im=raster(c,True)
        cache[208+i*30+22:208+i*30+30]=bytes(sum(128>>x for x in range(8) if im.getpixel((x,y))) for y in range(8))
    struct.pack_into('<H',cache,4,2);checksum=0
    for c in cache[16:]:checksum=(((checksum<<1)|(checksum>>15))^c)&65535
    struct.pack_into('<H',cache,6,checksum)
    u.mem_write(0x36000,bytes(cache));u.mem_write(0x2f600,b'\0\0'+bytes(range(0x60,0x66)))
    invoke('kr_psx_name',[0x8002f602]);assert decode(string(0xe9c5c))==text
    u.mem_write(0xebd40,struct.pack('<I',0x801c0000));u.mem_write(0xebd3c,struct.pack('<I',0x801d0000));u.mem_write(0xe8d10,struct.pack('<I',0x801e0000))
    # Native PSX %s formatting owns positions and color; only UV/page and
    # the half-space correction are adjusted in the authored wrapper.
    for db in [0,1]:
        u.mem_write(0x1c0000,bytes(0x100));u.mem_write(0x1d0038,struct.pack('<I',db));u.mem_write(0x1e0000,b'\x55'*2048)
        for i in range(6):
            for offset in [4,16]:u.mem_write(0x1e0000+i*92+offset,struct.pack('<I',0xe1000017))
        u.mem_write(0x1c000a,struct.pack('<H',0x1234));u.mem_write(0x1c000c,struct.pack('<HH',7,0x100))
        u.mem_write(0x1f0000,b'%s\0')
        invoke('kr_psx_name_print',[0,3,2,0x801f0000,0x800e9c5c])
        count=struct.unpack('<H',u.mem_read(0x1c0002,2))[0];assert count==5,count
        for i,x in enumerate([24,36,44,52,60]):
            p=0x1e0000+i*92
            actual_x=struct.unpack('<h',u.mem_read(p+32+db*20,2))[0]
            assert actual_x==x,(db,i,actual_x,x)
            assert u.mem_read(p+36+db*20+1,1)[0]>=160
            for offset in [4,16]:assert struct.unpack('<I',u.mem_read(p+offset,4))[0]==0xe1000018
            assert struct.unpack('<H',u.mem_read(p+64,2))[0]==0x107,'Native window routing metadata changed'
            assert bytes(u.mem_read(p+38+db*20,2))==struct.pack('<H',0x1234)
        # The next frame can recycle these same primitives for ordinary labels.
        # Their font page must return to the original page on every emission.
        u.mem_write(0x1c0002,bytes(2));u.mem_write(0x1f0020,b'AB\0')
        syms['original_printf']=0x800cc050
        invoke('original_printf',[0,3,2,0x801f0000,0x801f0020])
        for i in range(2):
            for offset in [4,16]:
                value=struct.unpack('<I',u.mem_read(0x1e0000+i*92+offset,4))[0]
                assert value==0xe1000017,('Name texture page leaked into ordinary text',db,i,offset,hex(value),bytes(u.mem_read(0x1c0000,8)).hex())
    result={'default_names':64,'default_glyph_bitmap_cases':default_glyph_cases,'legacy_card_files':3,'legacy_first_names':expected,'custom_Hangul_ASCII_space':True,
        'original_unknown_name_preserved':True,'printf_double_buffers':2,'name_space_pixels':4,'uploads_within_empty_atlas':len(uploads),
        'recycled_primitives_restore_original_font_page':True,
        'read_bytes':reads,'file_buffer_canaries':'preserved','per_file_fonts_independent':True,'damaged_preview_checksum_preserved':True}
    (ROOT/'analysis/psx-name-preview-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print(result)

if __name__=='__main__':main()
