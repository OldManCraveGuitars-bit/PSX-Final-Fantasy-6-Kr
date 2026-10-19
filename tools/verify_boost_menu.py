"""Execute configuration input code against native R3000 menu assets."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress

def main():
    r=json.loads((ROOT/'analysis/small-runtime.json').read_text('utf8'));s=r['symbols']
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0x140000,(ROOT/'work/modified/HAR/MENUMENU.BIN').read_bytes())
    u.mem_write(0xc8000,decompress((ROOT/'work/modified/HAR/HARATA.PAC').read_bytes())[0])
    u.mem_write(0x37800,(ROOT/'work/movie-subtitles.bin').read_bytes())
    u.mem_write(0x30700,struct.pack('<I',0x314e524b)+b'\x02\0\0\0'+bytes(8)+b'\xa5'*3072)
    u.mem_write(0x36000,bytes(u.mem_read(0x30700,3088)))
    drawn=[];calls=[]
    stubs={0x800c949c,0x800d8390,0x800d83f8,0x800fca90,0x800fca48,0x800fc9c4,0x800cd0c8,0x800fcc68,0x8005ab0c,0x8005ac90}
    def code(uc,at,size,user):
        if at==s['kr_boost_line']:
            args=[uc.reg_read(reg) for reg in [UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3]]
            text=[];ptr=args[3]&0x1fffff
            while True:
                tile=int.from_bytes(uc.mem_read(ptr,2),'little');ptr+=2
                if tile==65535:break
                text.append(tile)
            width=sum(4 if tile==0x8ffe else 8 for tile in text)
            assert args[0]*8+width<=240,(args,width)
            drawn.append(dict(x=args[0]*8,y=(args[1]%32)*8,width=width,palette=args[2],tiles=tuple(text)))
            uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
        elif at in stubs:
            calls.append(at);uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
    u.hook_add(UC_HOOK_CODE,code)
    def invoke(name):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.emu_start(s[name],0x801fffc0,count=300000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    def tick(high=0,low=0,repeat=0):
        u.mem_write(0x2e008,bytes([low,high,0,repeat]));invoke('kr_boost_config_tick')
    def flags():return u.mem_read(0x3070c,1)[0]
    invoke('kr_boost_config_init');assert len(drawn)==0
    assert int.from_bytes(u.mem_read(0x2588f,2),'little')&0x8000
    tick();assert calls[-1]==0x800cd0c8
    u.mem_write(0x2e04a,b'\x01');tick();assert len(drawn)==6
    drawn.clear();tick();assert not drawn
    u.mem_write(0x2e04a,b'\0');tick()
    drawn.clear();tick(low=16);assert len(drawn)==16
    # Four labelled rows have two distinct fixed columns and a highlighted
    # active setting; each label ends before its OFF/ON columns.
    for y in (56,80,104,128):
        rows=[x for x in drawn if x['y']==y and x['x']>=32]
        assert len(rows)==3 and rows[0]['x']+rows[0]['width']<rows[1]['x']
        assert rows[1]['x']+rows[1]['width']<rows[2]['x']
    for i in range(4):
        tick(high=1);assert flags()==(1<<(i+1))-1
        tick(high=4)
    assert flags()==15
    for i in range(4):
        tick(high=2);assert flags()==15^((1<<(i+1))-1)
        tick(high=4)
    assert flags()==0
    tick(low=128);assert flags()==1
    tick(low=128);assert flags()==0
    assert bytes(u.mem_read(0x30700,3088))==bytes(u.mem_read(0x36000,3088))
    assert bytes(u.mem_read(0x30710,3072))==b'\xa5'*3072
    tick(high=128);drawn.clear();tick();assert calls[-1]==0x800cd0c8
    magic=[]
    for index in range(6):
        u.mem_write(0x2fd54,bytes([0xa0|index]));drawn.clear();invoke('kr_config_magic')
        assert len(drawn)==6
        permutation=bytes(u.mem_read(0x12b488+index*4,3))
        assert all(row['x']+row['width']<=240 for row in drawn)
        assert u.mem_read(0x2fd54,1)[0]==0xa0|index
        magic.append([v//4 for v in permutation])
    assert len(set(tuple(v) for v in magic))==6
    result=dict(native_controller_combinations=True,all_four_independent=True,confirm_toggle=True,cancel_returns_native_configuration=True,
        original_settings_input_passes_through=True,labels_and_OFF_ON_columns_do_not_overlap=True,
        small_font_cell=8,space_pixels=4,name_payload_unchanged=True,save_mirror_equals_live=True,
        native_magic_order_permutations_preserved=magic,native_config_value_unchanged_by_render=True)
    (ROOT/'analysis/boost-menu-mips-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print(result)
if __name__=='__main__':main()
