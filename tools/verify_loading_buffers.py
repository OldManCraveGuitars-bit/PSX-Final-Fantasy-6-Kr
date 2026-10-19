"""Replay the native PAC decoder with both queued battle data buffers resident."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress

def main():
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0x38000,(ROOT/'work/extracted/SLPM_861.98').read_bytes()[0x800:])
    code=(ROOT/'work/movie-subtitles.bin').read_bytes();u.mem_write(0x37800,code)
    syms=json.loads((ROOT/'analysis/movie-subtitles-runtime.json').read_text('utf8'))['symbols']
    packed=(ROOT/'work/modified/BTL/BATTLE.PAC').read_bytes();expected=decompress(packed)[0]
    data=(ROOT/'work/modified/BTL/FF6_BTL.BIN').read_bytes();assert len(data)==0x48c00
    def decode():
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.reg_write(UC_MIPS_REG_A0,0x8014f800);u.reg_write(UC_MIPS_REG_A1,0x800c8000)
        u.emu_start(0x80041cec,0x801fffc0,count=15000000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
    # Reproduce the former race deterministically: the second queued read
    # overwrites 15 KiB of compressed source before the decoder consumes it.
    u.mem_write(0x14f800,packed);u.mem_write(0x197c00,data)
    decode()
    broken=bytes(u.mem_read(0xc8000,len(expected)))
    assert broken!=expected
    first=next(i for i,(a,b) in enumerate(zip(broken,expected)) if a!=b)
    # The safe staging starts precisely after the first read's sector extent.
    u.mem_write(0x14f800,packed);u.mem_write(0x19b800,data)
    decode();assert bytes(u.mem_read(0xc8000,len(expected)))==expected
    saved={reg:0x10203040+i for i,reg in enumerate([UC_MIPS_REG_V0,UC_MIPS_REG_T0,UC_MIPS_REG_T1,UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_RA])}
    for reg,value in saved.items():u.reg_write(reg,value)
    u.emu_start(syms['kr_battle_data_shift'],0x8003a9b4,count=1000000)
    assert u.reg_read(UC_MIPS_REG_PC)==0x8003a9b4
    assert bytes(u.mem_read(0x197c00,len(data)))==data
    assert bytes(u.mem_read(0xc8000,len(expected)))==expected
    assert all(u.reg_read(reg)==value for reg,value in saved.items())
    assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000 and u.reg_read(UC_MIPS_REG_V1)==0x801aea1e
    bonus=json.loads((ROOT/'analysis/omake-insertion.json').read_text('utf8'))
    start=int(bonus['compressed_staging_address'],16)&0x1fffff
    assert start+bonus['compressed_read_bytes']<=0x1e5000
    sentinel=bytes((i*13+9)&255 for i in range(0x1000));u.mem_write(0x1e5000,sentinel)
    payload=(ROOT/'work/modified/OMAKEDIR/OMAKE.PAC').read_bytes()
    u.mem_write(start,payload+bytes(bonus['compressed_read_bytes']-len(payload)))
    assert bytes(u.mem_read(0x1e5000,len(sentinel)))==sentinel
    result=dict(former_battle_overlap_reproduced=True,first_corrupt_address=hex(0x800c8000+first),
        battle_overlay_bytes_preserved=len(expected),battle_data_shift_bytes=len(data),
        native_decoder_and_shift=True,registers_and_stack_preserved=True,
        bonus_system_records_preserved=True,bonus_staging=[hex(start),hex(start+bonus['compressed_read_bytes'])])
    (ROOT/'analysis/v076-loader-buffer-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8')
    print(result)

if __name__=='__main__':main()
