"""Compare all native PSX message primitives with the former 16-bit storage."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from cdimage import directory_records
from pac import decompress


def old_overlay():
    path=ROOT/'work/candidates/FF6-KR-main-development-v070/FF6-KR-main-development-v070.bin'
    with path.open('rb') as f:
        _,_,lba,size=directory_records(f)['DEODIR/DEO.PAC'];out=bytearray()
        for i in range((size+2047)//2048):f.seek((lba+i)*2352+24);out+=f.read(2048)
    return decompress(bytes(out[:size]))[0]


def machine(overlay):
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0x38000,(ROOT/'work/extracted/SLPM_861.98').read_bytes()[0x800:]);u.mem_write(0xc8000,overlay)
    trace=[]
    def hook(_u,address,size,data):
        if address==0x800543ac:
            dest=u.reg_read(UC_MIPS_REG_A0);src=u.reg_read(UC_MIPS_REG_A1);n=u.reg_read(UC_MIPS_REG_A2)
            u.mem_write(dest&0x1fffffff,bytes(u.mem_read(src&0x1fffffff,n)))
            u.reg_write(UC_MIPS_REG_V0,dest);u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
        elif address==0x800d3108:trace.append((u.reg_read(UC_MIPS_REG_A0),struct.unpack('<hh',u.mem_read(0xeebe4,4))))
    u.hook_add(UC_HOOK_CODE,hook)
    def invoke(id,db,absolute):
        u.mem_write(0xebde4,bytes(0x2e00));u.mem_write(0xeebe4,bytes(32));trace.clear()
        u.mem_write(0xebd3c,struct.pack('<I',0x801d0000));u.mem_write(0x1d0038,struct.pack('<I',db))
        u.mem_write(0xeebec,struct.pack('<hh',12,12));u.mem_write(0xeebfc,struct.pack('<hh',21,256));u.mem_write(0xeec02,bytes(2))
        saved=[UC_MIPS_REG_S0,UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_S3,UC_MIPS_REG_S4]
        for i,reg in enumerate(saved):u.reg_write(reg,0x12345000+i)
        u.reg_write(UC_MIPS_REG_A0,absolute);u.reg_write(UC_MIPS_REG_A1,14);u.reg_write(UC_MIPS_REG_A2,10);u.reg_write(UC_MIPS_REG_A3,id)
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.emu_start(0x800d33dc,0x801fffc0,count=100000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0,(id,hex(u.reg_read(UC_MIPS_REG_PC)))
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
        assert [u.reg_read(reg) for reg in saved]==[0x12345000+i for i in range(len(saved))]
        count=struct.unpack('<H',u.mem_read(0xeec02,2))[0]
        primitives=bytes(u.mem_read(0xebde4,count*92))
        u.reg_write(UC_MIPS_REG_A0,id);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.emu_start(0x800d3380,0x801fffc0,count=10000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
        return list(trace),primitives,u.reg_read(UC_MIPS_REG_V0)
    return invoke


def main():
    before=old_overlay();after=decompress((ROOT/'work/modified/DEODIR/DEO.PAC').read_bytes())[0]
    original=decompress((ROOT/'work/extracted/DEODIR/DEO.PAC').read_bytes())[0]
    assert after[0x1f978:]==original[0x1f978:],'Native actor data was overwritten'
    baseline=machine(before);current=machine(after);cases=0;glyphs=0
    for db in [0,1]:
        for absolute in [0,1]:
            for id in range(74):
                a=baseline(id,db,absolute);b=current(id,db,absolute)
                assert a==b,('Message glyph, coordinates, primitives or length changed',id,db,absolute)
                cases+=1;glyphs+=len(b[0])
    report=json.loads((ROOT/'analysis/psx-ui-insertion.json').read_text('utf8'))
    result=dict(native_messages=74,comparison_cases=cases,native_glyph_draws=glyphs,
        comparison='v070 16-bit glyph storage vs byte-index storage: identical glyphs, XY, raw GPU primitives, length and ABI',
        large_font_cell=[12,12],space=6,native_actor_data='all bytes from 0x800e7978 through the end of the original overlay are restored exactly',
        text_pool_used=report['message_pool_total_used'],text_pool_capacity=report['message_pool_capacity'],font_address=report['name_preview']['font_data'])
    (ROOT/'analysis/psx-message-storage-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)


if __name__=='__main__':main()
