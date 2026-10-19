"""Compare native window traversal against the repaired MIPS frame hook.

Uses a real Whelk dialogue RAM capture. All 256 window-enable masks execute
the real window builders; their calls and produced display tables must match
the unhooked native loop. The delivered v081 must fail the same oracle.
"""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from emu import ROOT
from pac import decompress

def main():
    folder=ROOT/'work/v081-boss-after-cache-7-memory'
    ram=(folder/'ram.bin').read_bytes()
    regs=json.loads((folder/'state.json').read_text('utf8'))
    original=(ROOT/'work/decompressed/BTL/BATTLE.PAC').read_bytes()
    fixed=decompress((ROOT/'work/v082-cache-payloads/BTL/BATTLE.PAC').read_bytes())[0]
    broken=decompress((ROOT/'work/v081-cache-payloads/BTL/BATTLE.PAC').read_bytes())[0]
    native=bytearray(fixed);offset=0x1516e4-0xc8000
    native[offset:offset+8]=original[offset:offset+8]
    engines=[]
    for overlay in [native,fixed,broken]:
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
        u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000)
        u.mem_write(0,ram);u.mem_write(0xc8000,bytes(overlay))
        trace=[]
        def callback(uc,address,size,events):
            if address in (0x801512d8,0x80151454,0x801553e0):
                events.append([hex(address)]+[uc.reg_read(r) for r in (UC_MIPS_REG_A0,UC_MIPS_REG_A1,UC_MIPS_REG_A2)])
        u.hook_add(UC_HOOK_CODE,callback,trace,0x801512d8,0x801553e0)
        engines.append((u,trace))
    def run(engine,mask):
        u,trace=engine;trace.clear()
        # Restore all mutable RAM outside the executable overlay.
        u.mem_write(0,ram[:0xc8000]);u.mem_write(0x188000,ram[0x188000:])
        u.mem_write(0x3220c,bytes((mask,)))
        u.reg_write(UC_MIPS_REG_GP,regs['g0.gp']);u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
        u.emu_start(0x801516ac,0x801fffc0,count=1000000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
        return list(trace),bytes(u.mem_read(0x190560,0x1000)),bytes(u.mem_read(0x6c0f8,0x20)),bytes(u.mem_read(0x18f000,0x310))
    detected=[]
    for mask in range(256):
        expected=run(engines[0],mask)
        assert run(engines[1],mask)==expected,hex(mask)
        if run(engines[2],mask)!=expected:detected.append(mask)
    assert detected,'Regression test must reject v081'
    result=dict(native_window_masks=256,fixed_all_match_native=True,v081_mismatches=len(detected),v081_sample_masks=detected[:12],
        tested='Actual MIPS frame loop, native window builders, call order and output tables',
        cause='Backedge 801517b4 enters 801516e8; replacing its LUI with NOP loses the window-enable pointer after the first slot.')
    (ROOT/'analysis/v082-battle-window-loop-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8')
    print(result)

if __name__=='__main__':main()
