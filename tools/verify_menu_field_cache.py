"""Execute bounded cache, overlapping decoders, fast return and fallback."""
import json,struct,random
import lz4.block
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress
R=ROOT/'work/v081-cache-payloads'
meta=json.loads((ROOT/'analysis/v081-field-cache.json').read_text('utf8'));s=meta['symbols'];routes=meta['routes']
u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
u.mem_write(0,b'\xa5'*0x200000)
exe=(R/'SLPM_861.98').read_bytes();base,size=struct.unpack_from('<II',exe,0x18);u.mem_write(base&0x1fffff,exe[0x800:0x800+size])
har=decompress((R/'HAR/HARATA.PAC').read_bytes())[0];u.mem_write(0xc8000,har)
ram=(ROOT/'work/v081-field-before-menu/ram.bin').read_bytes();vr=(ROOT/'work/v081-field-before-menu/vram-backup.bin').read_bytes()
graphics=b''.join(b''.join(vr[y*512+block*128:y*512+(block+1)*128] for y in range(256)) for block in range(4))
tail=bytearray(ram[0x188000:0x1cb800]);tail[0x1c5c00-0x188000:0x1c6200-0x188000]=(R/'NAR/NAR_BIN3.BIN').read_bytes()[0x1fa00:0x20000];tail=bytes(tail)
u.mem_write(0x188000,tail)
reads=[];uploads=[];gpu_calls=[];guard=bytes(u.mem_read(0x1e5000,0x18000))
disc=(R/'menu-disc.bin').read_bytes()
def lba(msf):
    bcd=lambda x:(x>>4)*10+(x&15)
    return (bcd(msf&255)*60+bcd((msf>>8)&255))*75+bcd((msf>>16)&255)-150
menu_lba=114063+meta['har_read_bytes']//2048
def hook(uc,address,size,data):
    def reg(x):return uc.reg_read(x)&0xffffffff
    args=[reg(x) for x in (UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3)]
    if address==0x800543ac:
        uc.mem_write(args[0]&0x1fffff,bytes(uc.mem_read(args[1]&0x1fffff,args[2])));uc.reg_write(UC_MIPS_REG_V0,args[0])
    elif address==0xa0:uc.ctl_remove_cache(0x8012c000,0x8012d000)
    elif address==0x8003ee34:
        assert args==[512,256,0x800c8000,0x20000];uc.mem_write(0xc8000,graphics)
    elif address==0x80040734:gpu_calls.append(address)
    elif address in (0x8003af2c,0x8003afd8):
        msf=struct.unpack('<I',uc.mem_read(args[0]&0x1fffff,4))[0];start=(lba(msf)-menu_lba)*2048
        assert 0<=start and start+args[3]<=len(disc)
        uc.mem_write(args[1]&0x1fffff,disc[start:start+args[3]]);reads.append(args[3])
    elif address==0x8003ef20:
        assert args==[512,256,0x80140000,0x20000];uploads.append(bytes(uc.mem_read(0x140000,0x20000)))
    elif address not in (0x80046d84,0x8004d398,0x8005ab0c):return
    uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
for a in (0x800543ac,0xa0,0x8003ee34,0x80040734,0x8003af2c,0x8003afd8,0x8003ef20,0x80046d84,0x8004d398,0x8005ab0c):u.hook_add(UC_HOOK_CODE,hook,begin=a,end=a)
saved={r:0x13570000+i for i,r in enumerate((UC_MIPS_REG_S0,UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_S3,UC_MIPS_REG_S4,UC_MIPS_REG_S5,UC_MIPS_REG_S6,UC_MIPS_REG_S7))}
def run(pc,a0=0,end=0x80037ff0):
    for r,v in saved.items():u.reg_write(r,v)
    u.reg_write(UC_MIPS_REG_GP,0x8006bf40);u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,end);u.reg_write(UC_MIPS_REG_A0,a0);u.reg_write(UC_MIPS_REG_A1,3)
    u.emu_start(pc,end,count=50000000)
    assert u.reg_read(UC_MIPS_REG_PC)==end,hex(u.reg_read(UC_MIPS_REG_PC))
    assert all(u.reg_read(r)==v for r,v in saved.items())
    assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
run(meta['prepare_symbols']['kr_cache_prepare_bootstrap'])
u.mem_write(0xc8000,har)
header=bytes(u.mem_read(0x1e2000,16));magic,tail_src,ts,gs=struct.unpack('<4I',header)
assert magic==0x3143464b
assert lz4.block.decompress(bytes(u.mem_read(tail_src&0x1fffff,ts)))==tail
assert lz4.block.decompress(bytes(u.mem_read(0x179000,gs)))==graphics
cache_vram=bytes(u.mem_read(0x179000,0x19000));cache_tail=bytes(u.mem_read(0x1a8000,0x3b000))
run(s['kr_cache_menu_load'])
menu=(R/'HAR/MENUMENU.BIN').read_bytes()
assert bytes(u.mem_read(0x140000,0x33000))==menu[:0x33000]
assert bytes(u.mem_read(0x192000,0xe000))==menu[0x52000:0x60000]
assert bytes(u.mem_read(0x179000,0x19000))==cache_vram
assert bytes(u.mem_read(0x1a8000,0x3b000))==cache_tail
assert bytes(u.mem_read(0x13e000,0x2000))==(ROOT/'work/extracted/HAR/JOBOBJ.BIN').read_bytes()
before_reads=len(reads)
run(s['kr_cache_close_entry'],2)
assert uploads==[graphics] and len(reads)==before_reads+1
assert bytes(u.mem_read(0x188000,len(tail)))==tail
assert bytes(u.mem_read(0x130000,0x58000))==(R/'NAR/NAR_BIN.BIN').read_bytes()[:0x58000]
field=decompress((R/'NAR/NARITA.PAC').read_bytes())[0]
assert bytes(u.mem_read(0xc8000,len(field)))==field
assert bytes(u.mem_read(0x1e5000,0x18000))==guard
# Incompressible data and every small output capacity must fail without crossing limits.
rng=random.Random(81);raw=rng.randbytes(0x43800);bounds=[]
u.mem_write(0x135000,(ROOT/'work/menu-cache_main.bin').read_bytes())
u.mem_write(0x12c000,(ROOT/'work/menu-cache-prepare.bin').read_bytes())
u.ctl_remove_cache(0x8012c000,0x8012d000)
for cap in (32,1024,0x3a000):
    u.mem_write(0xc8000,raw);u.mem_write(0x1a8000+cap,b'GUARD')
    u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x80037ff0)
    for reg,val in zip((UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3),(0x800c8000,len(raw),0x801a8000,cap)):u.reg_write(reg,val)
    u.mem_write(0x1ff010,struct.pack('<I',0x8010c000))
    u.emu_start(meta['prepare_symbols']['kr_cache_pack'],0x80037ff0,count=50000000)
    assert u.reg_read(UC_MIPS_REG_V0)==0 and bytes(u.mem_read(0x1a8000+cap,5))==b'GUARD'
    bounds.append(cap)
# Invalid cache reaches the existing safe full loader before copying return code.
u.mem_write(0x1e2000,bytes(4));run(s['kr_cache_close_entry'],end=0x8003a450)
result=dict(cache_tail_bytes=ts,cache_graphics_bytes=gs,cache_roundtrip_exact=True,
    split_menu_overlap_decode_exact=True,field_prefix_and_native_overlay_exact=True,graphics_upload_exact=True,
    full_reload_fallback=True,bounded_compression_failure_capacities=bounds,
    name_cache_music_system_records_and_stack_preserved=True,fast_return_CD_bytes=routes['FIELD_CACHE_READ_BYTES'])
(ROOT/'analysis/v081-field-cache-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8');print(result)
