"""Execute the patched MIPS dispatch for every dialogue and PSX tutorial."""
import json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from pac import decompress
from textcodec import ROOT
from build_main_dialogue import SPECIAL,CANDIDATE
from field_names import default_names

def main():
    candidate=ROOT/'work/candidates'/CANDIDATE
    offsets=json.loads((candidate/'new_dialogue_offsets.json').read_text())
    source=json.loads((ROOT/'analysis/dialogue-original.json').read_text('utf8'))
    original=(ROOT/'work/decompressed/NAR/NARITA.PAC').read_bytes()
    modified=decompress((ROOT/'work/modified/NAR/NARITA.PAC').read_bytes())[0]
    # No overlay growth and no BSS write; only the original dispatch is code.
    assert len(original)==len(modified)
    rows=json.loads((ROOT/'translations/dialogue.complete-draft.json').read_text('utf8'))
    nar=(ROOT/'work/modified/NAR/NAR_BIN.BIN').read_bytes()
    bank=struct.unpack_from('<H',nar,0x6b710)[0]
    pointers=struct.unpack_from('<'+'H'*len(offsets),nar,0x6b712)
    assert [p+(65536 if i>=bank else 0) for i,p in enumerate(pointers)]==offsets
    runtime=json.loads((ROOT/'analysis/dialogue-runtime.json').read_text('utf8'))
    streams=[bytes.fromhex(x) for x in runtime['streams']]
    special={old:len(rows)+i for old,i in SPECIAL}
    uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0,0x200000)
    uc.mem_write(0xc8000,bytes(modified))
    uc.mem_write(0x1a6200,(ROOT/'work/modified/NAR/NAR_BIN3.BIN').read_bytes())
    uc.reg_write(UC_MIPS_REG_SP,0x801ff000)
    decoded=set()
    for row,offset in zip(source,offsets):
        uc.reg_write(UC_MIPS_REG_S0,offset)
        preserved={UC_MIPS_REG_A0:0x801ff010,UC_MIPS_REG_A1:0x8019b710,UC_MIPS_REG_V1:0x10000,
            UC_MIPS_REG_A2:0x6543,UC_MIPS_REG_A3:0x5678,UC_MIPS_REG_HI:0x12345678,UC_MIPS_REG_LO:0x23456789}
        for i,reg in enumerate([UC_MIPS_REG_T0,UC_MIPS_REG_T1,UC_MIPS_REG_T2,UC_MIPS_REG_T3,UC_MIPS_REG_T4,
            UC_MIPS_REG_T5,UC_MIPS_REG_T6,UC_MIPS_REG_T7,UC_MIPS_REG_T8,UC_MIPS_REG_T9]):preserved[reg]=0x1000+i*17
        for r,v in preserved.items():uc.reg_write(r,v)
        uc.mem_write((runtime['buffer_address']&0x1fffff)-16,b'\xa5'*1056)
        uc.emu_start(0x80101ea8,0x80102094,count=3000000)
        assert uc.reg_read(UC_MIPS_REG_PC)==0x80102094
        actual=uc.reg_read(UC_MIPS_REG_S0)&0xffffffff
        expected=runtime['buffer_address']
        assert actual==expected,(row['id'],hex(actual),hex(expected))
        for r,v in preserved.items():assert uc.reg_read(r)==v,(row['id'],r)
        assert uc.reg_read(UC_MIPS_REG_SP)==0x801ff000
        index=special.get(row['offset'],row['id']);decoded.add(index)
        stream=streams[index]
        assert bytes(uc.mem_read(expected&0x1fffff,len(stream)))==stream,row['id']
        assert bytes(uc.mem_read((expected&0x1fffff)+len(stream),1024-len(stream)))==b'\xa5'*(1024-len(stream))
        assert bytes(uc.mem_read((expected&0x1fffff)-16,16))==b'\xa5'*16
    # PSX dispatch redirects sixteen original SNES tutorial records. Decode
    # those retained originals directly too, covering all 3100 packed streams.
    direct=0
    for index in sorted(set(range(len(streams)))-decoded):
        uc.reg_write(UC_MIPS_REG_S0,0x801a6200+runtime['offsets'][index])
        for r,v in preserved.items():uc.reg_write(r,v)
        uc.mem_write((expected&0x1fffff)-16,b'\xa5'*1056)
        uc.emu_start(runtime['symbols']['kr_dialogue_dispatch'],0x80102094,count=3000000)
        assert uc.reg_read(UC_MIPS_REG_PC)==0x80102094
        assert uc.reg_read(UC_MIPS_REG_S0)==expected
        assert uc.reg_read(UC_MIPS_REG_SP)==0x801ff000
        for r,v in preserved.items():assert uc.reg_read(r)==v,(index,r)
        stream=streams[index]
        assert bytes(uc.mem_read(expected&0x1fffff,len(stream)))==stream,index
        assert bytes(uc.mem_read((expected&0x1fffff)+len(stream),1024-len(stream)))==b'\xa5'*(1024-len(stream))
        assert bytes(uc.mem_read((expected&0x1fffff)-16,16))==b'\xa5'*16
        decoded.add(index);direct+=1
    assert len(decoded)==len(streams)
    report={'dispatch_cases_passed':len(offsets),'special_tutorial_cases':len(SPECIAL),'overlay_size_preserved':True,
        'unique_native_streams_decoded':len(decoded),'redirected_originals_decoded_directly':direct,
        'native_bank_boundary':bank,'bank_pointer_reconstruction_cases':len(offsets),'exact_64k_boundary_present':65536 in offsets,
        'lossless_native_Huffman_decode':'all dispatched strings matched original native byte streams',
        'expansion_buffer_canaries':'preserved','caller_registers_stack_HI_LO':'preserved'}
    (ROOT/'analysis/dispatch-verification.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
    print(report)

if __name__=='__main__':main()
