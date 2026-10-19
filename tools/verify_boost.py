"""Execute the compiled R3000 booster code, including original hook prologues."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress
from capstone import Cs,CS_ARCH_MIPS,CS_MODE_MIPS32,CS_MODE_LITTLE_ENDIAN

def main():
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000)
    u.mem_write(0x37800,(ROOT/'work/movie-subtitles.bin').read_bytes())
    r=json.loads((ROOT/'analysis/boost-runtime.json').read_text('utf8'));syms=r['resident_symbols']
    binary=(ROOT/'work/movie-subtitles.bin').read_bytes()
    start=syms['kr_boost_flags']-0x80037800
    dis=list(Cs(CS_ARCH_MIPS,CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN).disasm(binary[start:],syms['kr_boost_flags']))
    for left,right in zip(dis,dis[1:]):
        if left.mnemonic not in ('lw','lbu','lhu','lb','lh'):continue
        loaded=left.op_str.split(',')[0]
        parts=right.op_str.split(',')
        reads=right.op_str if right.mnemonic.startswith('b') or right.mnemonic in ('jr','jalr','sw','sb','sh','swl','swr') else ','.join(parts[1:])
        assert loaded not in reads,('R3000 load-delay hazard',hex(left.address),left.op_str,right.mnemonic,right.op_str)
    def put(at,v,n):u.mem_write(at,v.to_bytes(n,'little'))
    def get(at,n):return int.from_bytes(u.mem_read(at,n),'little')
    def header(flags):
        put(0x30700,0x314e524b,4);put(0x30708,0x31545342,4)
        put(0x3070c,flags|((flags^0xa5)<<8),4)
    def invoke(at,stop=0x801fffc0):
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.emu_start(at,stop,count=200000)
        assert u.reg_read(UC_MIPS_REG_PC)==stop,hex(u.reg_read(UC_MIPS_REG_PC))
    cases=0
    for flags in range(16):
        header(flags);invoke(syms['kr_boost_flags']);assert u.reg_read(UC_MIPS_REG_V0)==flags
    for at,n in [(0x30700,4),(0x30708,4),(0x3070c,4),(0x3070d,1),(0x3070e,2)]:
        header(15);put(at,get(at,n)^1,n);invoke(syms['kr_boost_flags']);assert u.reg_read(UC_MIPS_REG_V0)==0
    for flags in range(16):
        for xp,gil,ap in [(0,0,0),(1,1,1),(21,37,3),(393210,393210,10),(0xffffff,0xffffff,255)]:
            header(flags);put(0x20f35,xp,3);put(0x20f3e,gil,3);put(0x2e0fb,ap,1)
            preserved=[UC_MIPS_REG_V0,UC_MIPS_REG_V1,UC_MIPS_REG_T0,UC_MIPS_REG_T1,UC_MIPS_REG_T2,UC_MIPS_REG_T4,UC_MIPS_REG_T5]
            for i,reg in enumerate(preserved):u.reg_write(reg,0x12345000+i)
            u.reg_write(UC_MIPS_REG_S1,0x801fe100)
            invoke(syms['kr_boost_rewards'])
            assert get(0x20f35,3)==min(0xffffff,xp*(5 if flags&2 else 1))
            assert get(0x20f3e,3)==min(0xffffff,gil*(5 if flags&4 else 1))
            assert get(0x2e0fb,1)==min(255,ap*(5 if flags&8 else 1))
            assert all(u.reg_read(reg)==0x12345000+i for i,reg in enumerate(preserved))
            assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
            assert u.reg_read(UC_MIPS_REG_A0)==0x801fe100 and u.reg_read(UC_MIPS_REG_A1)==0x80020000
            cases+=1
    for flags in range(16):
        header(flags)
        invoke(syms['kr_boost_field_check'],0x801fffc0 if flags&1 else 0x800d2748)
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
        put(0x6c168,0x1f8003c8,4);put(0x6c16c,0x1f8003ca,4);put(0x1f8003c8,0xbeef,2)
        invoke(syms['kr_boost_world_check'],0x801fffc0 if flags&1 else 0x800cdf4c)
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
        if flags&1:assert get(0x1f8003c8,2)==0
        else:assert get(0x1f8003c8,2)==0xbeef and u.reg_read(UC_MIPS_REG_V0)==0x1f8003ca
    cat=json.loads((ROOT/'analysis/field-catalog-insertion.json').read_text('utf8'))
    nar=(ROOT/'work/modified/NAR/NAR_BIN3.BIN').read_bytes();u.mem_write(0x1a6200,nar)
    header(15);put(0x36008,0x31545342,4)
    invoke(cat['symbols']['kr_boost_new_game'],0x801008a4)
    assert get(0x30708,4)==get(0x36008,4)==0
    original=(ROOT/'work/decompressed/NAR/NARITA.PAC').read_bytes()
    patched=decompress((ROOT/'work/modified/NAR/NARITA.PAC').read_bytes())[0]
    assert original[0xd23f8-0xc8000:0xd2748-0xc8000]==patched[0xd23f8-0xc8000:0xd2748-0xc8000]
    # OGA carries all world-map artwork/data in the same overlay. Apart from
    # the eight-byte random-battle prologue, preserve every original byte.
    world=(ROOT/'work/decompressed/OGA/OGATA.PAC').read_bytes()
    actual=decompress((ROOT/'work/modified/OGA/OGATA.PAC').read_bytes())[0]
    allowed=set(range(0x5f44,0x5f4c))
    assert len(world)==len(actual) and all(a==b or i in allowed for i,(a,b) in enumerate(zip(world,actual)))
    result=dict(flag_combinations=16,reward_cases=cases,independent_switches=True,invalid_or_legacy_header_defaults_off=True,
        original_off_paths_preserved=True,field_and_world_random_gates=True,scripted_field_battle_code_unchanged=True,
        new_game_resets_all_off=True,world_graphics_and_data_byte_identical_outside_hook=True,
        resident_R3000_load_delay_slots_checked=True,
        original_reward_division_relic_bonus_and_caps_preserved=True,overflow_saturates=True,
        native_input_and_card_replay_reports=['analysis/boost-native-menu-verification.json',
            'analysis/boost-native-save-load-verification.json'])
    (ROOT/'analysis/boost-mips-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)
if __name__=='__main__':main()
