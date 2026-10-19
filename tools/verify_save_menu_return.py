"""Run the whole native save-return task, including its late font rebuild."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress


def main():
    menu=(ROOT/'work/modified/HAR/MENUMENU.BIN').read_bytes()
    overlay=decompress((ROOT/'work/modified/HAR/HARATA.PAC').read_bytes())[0]
    original=(ROOT/'work/decompressed/HAR/HARATA.PAC').read_bytes()
    symbols=json.loads((ROOT/'analysis/small-runtime.json').read_text('utf8'))['symbols']
    hook=struct.unpack_from('<II',overlay,0x8010e280-0x800c8000)
    assert hook==((3<<26)|((symbols['kr_restore_small_after_save']>>2)&0x3ffffff),0)
    for address in [0x800cec18,0x8011303c]:
        at=address-0x800c8000;assert overlay[at:at+8]==original[at:at+8]
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    u.mem_map(0,0x200000);u.mem_write(0xc8000,overlay);u.mem_write(0x140000,menu)
    atlas=menu[0x26000:0x2e000];vram=bytearray([0xa5])*1048576
    events=[];native_result=None
    def callback(_u,address,_size,_data):
        nonlocal native_result
        if address==0x8003e03c:
            x=u.reg_read(UC_MIPS_REG_A1);y=u.reg_read(UC_MIPS_REG_A2)
            events.append(('original_font_page',x,y))
            for row in range(y,y+128):
                vram[row*2048+x*2:row*2048+(x+256)*2]=bytes([0x55])*512
        elif address==0x8003d4c0:events.append(('original_other_graphics',))
        elif address==0x8011f93c:
            events.append(('original_final_canvas_setup',));native_result=bytes(vram)
        elif address==0x8005adb8:
            rect=struct.unpack('<4h',u.mem_read(u.reg_read(UC_MIPS_REG_A0)&0x1fffff,8))
            assert rect==(512,0,64,256),rect
            assert u.reg_read(UC_MIPS_REG_A1)==0x80166000
            assert events[-2:]==[('original_final_canvas_setup',),('draw_sync',)]
            events.append(('primary_atlas_upload',))
            for y in range(256):vram[y*2048+1024:y*2048+1152]=atlas[y*128:(y+1)*128]
        elif address==0x8005ab0c:
            assert u.reg_read(UC_MIPS_REG_A0)==0;events.append(('draw_sync',))
        else:
            assert address==0x80040ce4
            value=u.reg_read(UC_MIPS_REG_A0)&255;at=u.reg_read(UC_MIPS_REG_A1)&0x1fffff
            u.mem_write(at,bytes([value]))
        u.reg_write(UC_MIPS_REG_V0,0);u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
    for address in [0x8003e03c,0x8003d4c0,0x8011f93c,0x8005adb8,0x8005ab0c,0x80040ce4]:
        u.hook_add(UC_HOOK_CODE,callback,begin=address,end=address)
    for frame in range(2):
        events.clear();native_result=None
        registers=[UC_MIPS_REG_S0,UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_S3,UC_MIPS_REG_S4,UC_MIPS_REG_S5,UC_MIPS_REG_S6,UC_MIPS_REG_S7,UC_MIPS_REG_S8,UC_MIPS_REG_GP]
        preserved={reg:0x12340000+i for i,reg in enumerate(registers)}
        for reg,value in preserved.items():u.reg_write(reg,value)
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.emu_start(0x8010e1ec,0x801fffc0,count=10000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
        assert all(u.reg_read(reg)==value for reg,value in preserved.items())
        assert [e for e in events if e[0]=='original_font_page']==[
            ('original_font_page',768,256),('original_font_page',512,0),
            ('original_font_page',512,128),('original_font_page',544,0),('original_font_page',544,128)]
        assert events[-4:]==[('original_final_canvas_setup',),('draw_sync',),('primary_atlas_upload',),('draw_sync',)]
        for y in range(512):
            start=y*2048
            if y<256:
                assert vram[start+1024:start+1152]==atlas[y*128:(y+1)*128]
                assert vram[start:start+1024]==native_result[start:start+1024]
                assert vram[start+1152:start+2048]==native_result[start+1152:start+2048]
            else:assert vram[start:start+2048]==native_result[start:start+2048]
    result={'whole_native_save_return_task':'passed','original_font_page_rebuilds':5,
            'extended_font_restored_after_last_original_upload':True,
            'restore_rectangle':[512,0,64,256],'other_native_vram_preserved':True,
            'repeated_return_cases':2,'no_per_frame_hook':True,
            'callee_saved_registers_and_stack':'preserved'}
    (ROOT/'analysis/save-menu-return-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8')
    print(result)


if __name__=='__main__':main()
