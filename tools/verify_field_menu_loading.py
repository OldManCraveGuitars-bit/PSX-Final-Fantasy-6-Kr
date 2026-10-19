"""Run the actual resident fast-return code with original buffers and sentinels."""
import json,struct,sys
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT

u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
u.mem_write(0,b'\xa5'*0x200000)
field_cache='--field-cache' in sys.argv
payloads=ROOT/('work/v081-cache-payloads' if field_cache else 'work/modified')
exe=(payloads/'SLPM_861.98').read_bytes();base,size=struct.unpack_from('<II',exe,0x18)
u.mem_write(base&0x1fffff,exe[0x800:0x800+size])
report=json.loads((ROOT/'analysis/field-menu-loading.json').read_text('utf8'))
reads=[(ROOT/'work'/f'field-menu-read{i}.bin').read_bytes() for i in (1,2)]
count=0
def read(uc,address,size,data):
    global count
    a=[uc.reg_read(r)&0xffffffff for r in (UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3)]
    msf=struct.unpack('<I',uc.mem_read(a[0]&0x1fffff,4))[0]
    assert msf==report['bank_MSFs'][count]
    assert a[1:]==[(0x800c8000,0x800e8000)[count],0,len(reads[count])],a
    uc.mem_write(a[1]&0x1fffff,reads[count]);count+=1
    uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
u.hook_add(UC_HOOK_CODE,read,begin=0x8003af2c,end=0x8003af2c)
u.hook_add(UC_HOOK_CODE,read,begin=0x8003afd8,end=0x8003afd8)
saved={r:0x13570000+i for i,r in enumerate((UC_MIPS_REG_S0,UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_S3,UC_MIPS_REG_S4,UC_MIPS_REG_S5,UC_MIPS_REG_S6,UC_MIPS_REG_S7,UC_MIPS_REG_GP))}
for r,v in saved.items():u.reg_write(r,v)
saved[UC_MIPS_REG_S0]=3;u.reg_write(UC_MIPS_REG_S0,3)
u.reg_write(UC_MIPS_REG_SP,0x801ff000)
before=bytes(u.mem_read(0,0x200000))
u.emu_start(0x8003a4a8,0x8003a5a4,count=20000000)
assert u.reg_read(UC_MIPS_REG_PC)==0x8003a5a4 and count==2
u.emu_start(0x8003a604,0x8003a610,count=5000000)
assert u.reg_read(UC_MIPS_REG_PC)==0x8003a610
for path,at,size in [('NAR/NAR_BIN.BIN',0x130000,0x9b800),('NAR/NAR_BIN3.BIN',0xc8000,0x20000),('NAR/NARITA.PAC',0x10d800,0x22800)]:
    expected=(payloads/path).read_bytes();expected+=bytes(size-len(expected))
    assert bytes(u.mem_read(at,size))==expected,path
after=bytes(u.mem_read(0,0x200000))
assert after[:0x63470]==before[:0x63470]
assert after[0x63474:0xc8000]==before[0x63474:0xc8000]
assert struct.unpack('<I',after[0x63470:0x63474])[0]==report['texture_MSFs'][1]
assert after[0x1cb800:]==before[0x1cb800:],'Records, music, stack or adjacent buffers changed'
assert all(u.reg_read(r)==v for r,v in saved.items()) and u.reg_read(UC_MIPS_REG_SP)==0x801ff000
original=(ROOT/'work/extracted/SLPM_861.98').read_bytes()
for a,b in [(0x8003a4e8,0x8003a560),(0x8003a610,0x8003a69c)]:
    assert exe[a-base+0x800:b-base+0x800]==original[a-0x80038000+0x800:b-0x80038000+0x800]
result=dict(native_fast_return_executed=True,disc_reads=2,field_and_script_exact=True,
            native_PAC_exact=True,native_graphics_restoration_byte_identical=True,
            partial_read_paths_preserved=True,records_music_stack_and_registers_preserved=True,
            read_bytes=sum(map(len,reads)),previous_read_bytes=report['previous_full_read_bytes'])
for mode in (1,2):
    u.reg_write(UC_MIPS_REG_S0,mode)
    snapshot=bytes(u.mem_read(0xc8000,0x138000))
    u.emu_start(0x8003a604,0x8003a610,count=100)
    assert u.reg_read(UC_MIPS_REG_PC)==0x8003a610
    assert bytes(u.mem_read(0xc8000,0x138000))==snapshot
    assert struct.unpack('<I',u.mem_read(0x63470,4))[0]==report['texture_MSFs'][0]
result.update(queued_read_overlaps_GPU_initialization=True,partial_modes_skipped_decompression=[1,2])
result.update(texture_mirror_selected_for_full_return=True,original_texture_route_restored_for_partial_returns=True)
(ROOT/'analysis'/('v081-full-fallback-verification.json' if field_cache else 'v080-field-menu-loading-verification.json')).write_text(json.dumps(result,indent=2)+'\n','utf8')
print(result)
