"""Execute the real menu read wrapper and native decoder with guarded RAM."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress

def main():
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0,bytes([0xa5])*0x200000)
    exe=(ROOT/'work/modified/SLPM_861.98').read_bytes()
    base,size=struct.unpack_from('<II',exe,0x18)
    u.mem_write(base&0x1fffff,exe[0x800:0x800+size])
    syms=json.loads((ROOT/'analysis/movie-subtitles-runtime.json').read_text('utf8'))['symbols']
    report=json.loads((ROOT/'analysis/menu-loading.json').read_text('utf8'))
    packed=(ROOT/'work/menu-disc.pac').read_bytes()[:report['read_bytes']]
    menu=(ROOT/'work/modified/HAR/MENUMENU.BIN').read_bytes()[:report['decoded_bytes']]
    overlay=decompress((ROOT/'work/modified/HAR/HARATA.PAC').read_bytes())[0]
    u.mem_write(0xc8000,overlay)
    calls=[]
    def cd_read(uc,address,size,data):
        if address!=0x8003af2c:return
        args=[uc.reg_read(r)&0xffffffff for r in [UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3]]
        assert args==[0x80063484,0x801a0000,0,len(packed)],args
        uc.mem_write(args[1]&0x1fffff,packed)
        calls.append(args)
        uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
    u.hook_add(UC_HOOK_CODE,cd_read,begin=0x8003af2c,end=0x8003af2c)
    saved={r:0x13570000+i for i,r in enumerate([UC_MIPS_REG_S0,UC_MIPS_REG_S1,UC_MIPS_REG_S2,UC_MIPS_REG_S3,UC_MIPS_REG_S4,UC_MIPS_REG_S5,UC_MIPS_REG_S6,UC_MIPS_REG_S7,UC_MIPS_REG_GP])}
    for r,v in saved.items():u.reg_write(r,v)
    u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
    for r,v in zip([UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2,UC_MIPS_REG_A3],[0x80063484,0x80140000,0,len(packed)]):u.reg_write(r,v)
    u.emu_start(syms['kr_menu_read'],0x801fffc0,count=20000000)
    assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
    assert len(calls)==1 and bytes(u.mem_read(0x140000,len(menu)))==menu
    assert bytes(u.mem_read(0xc8000,len(overlay)))==overlay
    assert bytes(u.mem_read(0x1a0000,len(packed)))==packed
    assert bytes(u.mem_read(0x1e5000,0x3000))==bytes([0xa5])*0x3000
    assert bytes(u.mem_read(0x1ed800,0x10000))==bytes([0xa5])*0x10000
    assert all(u.reg_read(r)==v for r,v in saved.items()) and u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    # Main-menu path: one contiguous read contains the original PAC followed
    # by the LZ4 menu. Decode HAR first, then use the cached menu without I/O.
    har=(ROOT/'work/modified/HAR/HARATA.PAC').read_bytes()
    combined=har+bytes(0x24800-len(har))+packed
    u.mem_write(0x168000,bytes([0x3c])*0x20000)
    u.mem_write(0x188000,combined)
    u.reg_write(UC_MIPS_REG_A0,0x80188000);u.reg_write(UC_MIPS_REG_A1,0x800c8000)
    u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
    u.emu_start(0x80041cec,0x801fffc0,count=20000000)
    assert bytes(u.mem_read(0xc8000,len(overlay)))==overlay
    assert bytes(u.mem_read(0x168000,0x20000))==bytes([0x3c])*0x20000
    assert bytes(u.mem_read(0x1ac800,len(packed)))==packed
    u.emu_start(syms['kr_menu_cached'],0x801fffc0,count=20000000)
    assert len(calls)==1 and bytes(u.mem_read(0x140000,len(menu)))==menu
    assert bytes(u.mem_read(0xc8000,len(overlay)))==overlay
    assert bytes(u.mem_read(0x1ac800,len(packed)))==packed
    assert bytes(u.mem_read(0x1e5000,0x3000))==bytes([0xa5])*0x3000
    assert bytes(u.mem_read(0x1ed800,0x10000))==bytes([0xa5])*0x10000
    # Save-card return executes HAR reload -> menu unpack -> later menu init.
    # Replay the actual resident call site, then unpack the same cache again.
    expected_call=(3<<26)|((syms['kr_menu_cached']>>2)&0x3ffffff)
    assert struct.unpack('<I',u.mem_read(0x3a1fc,4))[0]==expected_call
    for address in (0x80108eac,0x8010f988):
        assert struct.unpack_from('<I',overlay,address-0x800c8000)[0]==expected_call
    def har_reload(uc,address,size,data):
        uc.mem_write(0x188000,combined)
        uc.reg_write(UC_MIPS_REG_A0,0x80188000);uc.reg_write(UC_MIPS_REG_A1,0x800c8000)
        uc.reg_write(UC_MIPS_REG_PC,0x80041cec)
    h=u.hook_add(UC_HOOK_CODE,har_reload,begin=0x8003aa50,end=0x8003aa50)
    u.reg_write(UC_MIPS_REG_GP,0x8006bf40)
    u.reg_write(UC_MIPS_REG_SP,0x801fefe8);u.mem_write(0x1feff8,struct.pack('<I',0x801fffc0))
    u.mem_write(0x6c280,struct.pack('<II',0x80063484,len(packed)))
    u.emu_start(0x8003a1e8,0x801fffc0,count=20000000)
    assert bytes(u.mem_read(0x140000,len(menu)))==menu and len(calls)==1
    assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
    u.emu_start(syms['kr_menu_cached'],0x801fffc0,count=20000000)
    assert bytes(u.mem_read(0x140000,len(menu)))==menu
    assert bytes(u.mem_read(0x1ac800,len(packed)))==packed and len(calls)==1
    u.hook_del(h)
    # The late native job-sprite initializer now copies the exact cached data
    # instead of issuing another CD seek. Exercise its real patched entry.
    jobs=(ROOT/'work/extracted/HAR/JOBOBJ.BIN').read_bytes();copies=[]
    def memcpy(uc,address,size,data):
        a=[uc.reg_read(r)&0xffffffff for r in (UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2)]
        assert a==[0x800b1be8,int(report['job_sprite_cache_address'],16),8192],a
        uc.mem_write(a[0]&0x1fffff,bytes(uc.mem_read(a[1]&0x1fffff,a[2])))
        copies.append(a);uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
    h=u.hook_add(UC_HOOK_CODE,memcpy,begin=0x800543ac,end=0x800543ac)
    u.mem_write(0xb1bd8,b'\xa5'*(8192+32));u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
    u.emu_start(0x80110c7c,0x801fffc0,count=100)
    assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0 and len(copies)==1 and len(calls)==1
    assert bytes(u.mem_read(0xb1be8,8192))==jobs
    assert bytes(u.mem_read(0xb1bd8,16))==bytes(u.mem_read(0xb3be8,16))==b'\xa5'*16
    u.hook_del(h)
    # Independent block cases cover long extensions, unaligned matches,
    # offset-one overlapping copies, zero literals and near-64K distances.
    import lz4.block,random
    rng=random.Random(78)
    cases=[b'',b'A',b'ABCDE',b'A'*70000,bytes(range(256))*300]
    for size in (14,15,16,270,271,272,1024,65535):
        random_bytes=rng.randbytes(size)
        cases.extend([random_bytes,random_bytes+b'XY'+random_bytes,bytes([size&255])*size])
    for raw in cases:
        block=lz4.block.compress(raw,mode='high_compression',compression=12,store_size=True)
        u.mem_write(0x140000,bytes([0xa5])*(len(raw)+16));u.mem_write(0x1a0000,block)
        u.reg_write(UC_MIPS_REG_A0,0x801a0000);u.reg_write(UC_MIPS_REG_A1,0x80140000)
        u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.emu_start(0x80037680,0x801fffc0,count=20000000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
        assert bytes(u.mem_read(0x140000,len(raw)))==raw
        assert bytes(u.mem_read(0x140000+len(raw),16))==bytes([0xa5])*16
    result=dict(native_wrapper_and_decoder=True,lossless_output_bytes=len(menu),read_bytes=len(packed),
        overlay_preserved=True,compressed_source_preserved=True,system_records_preserved=True,music_buffer_preserved=True,
        stack_and_callee_saved_registers_preserved=True,staging_end=report['staging_end'],
        combined_read_and_cached_path=True,combined_read_bytes=len(combined),lz4_edge_cases=len(cases),
        native_save_return_then_repeated_menu_unpack=True,all_three_callers_use_validated_cache=True,
        cached_job_sprite_bytes_exact=len(jobs),late_job_sprite_CD_seek_removed=True)
    (ROOT/'analysis/menu-loading-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8');print(result)

if __name__=='__main__':main()
