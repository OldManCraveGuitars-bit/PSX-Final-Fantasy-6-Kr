"""Execute the enemy-name producer AND consumer, including FF operands."""
import json,struct,sys
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from emu import ROOT
from pac import decompress

def main():
    target=sys.argv[1] if len(sys.argv)>1 else 'v084'
    reports={tag:json.loads((ROOT/f'analysis/{tag}-battle-big-text-insertion.json').read_text('utf8')) for tag in ['v083',target]}
    result={}
    for tag,r in reports.items():
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
        u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000)
        u.mem_write(0,(ROOT/'work/v082-volts-counter-entry-memory/ram.bin').read_bytes())
        p=ROOT/f'work/{tag}-cache-payloads'
        u.mem_write(0xc8000,decompress((p/'BTL/BATTLE.PAC').read_bytes())[0])
        u.mem_write(0x197c00,(p/'BTL/FF6_BTL.BIN').read_bytes())
        for ptr,value in [(0x6c168,0x1f8003c8),(0x6c16c,0x1f8003ca),(0x6c1a0,0x1f8003cc),(0x6c1d8,0x1f8003d4)]:
            u.mem_write(ptr,struct.pack('<I',value))
        seen=[];copying=False
        def hook(uc,at,size,user):
            if copying and at==0x8014091c:uc.emu_stop()
            elif at==r['symbols']['kr_big_original_glyph']:
                seen.append(struct.unpack('<H',uc.mem_read(0x2e026,2))[0]//22)
                uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
            elif at==0x800cfcd8:uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
        u.hook_add(UC_HOOK_CODE,hook)
        failed=[];tested=0
        for index in range(384):
            row=r['encoded'][229+index];identifier=row['id']
            expected=bytes((0x18,identifier%255+1,identifier//255+1,0))
            u.mem_write(0x237d4,b'\xa5'*18);u.mem_write(0x1ff010,struct.pack('<H',index*8))
            u.mem_write(0x1f8003ca,b'\0\0');u.reg_write(UC_MIPS_REG_SP,0x801ff000)
            copying=True;u.emu_start(0x8014081c,0x801fffc0,count=50000);copying=False
            assert u.reg_read(UC_MIPS_REG_PC)==0x8014091c,(tag,index,hex(u.reg_read(UC_MIPS_REG_PC)))
            got=bytes(u.mem_read(0x237d5,4))
            if got!=expected:failed.append(dict(index=index,text=row['translation'],expected=expected.hex(),actual=got.hex()))
            if tag=='v083':continue
            assert got==expected,(index,got.hex(),expected.hex())
            assert bytes(u.mem_read(0x237d4,1))==b'\xa5'
            assert bytes(u.mem_read(0x237d9,13))==b'\xa5'*13
            u.mem_write(0x268a7,struct.pack('<HB',0x37d5,2))
            u.reg_write(UC_MIPS_REG_RA,0x801fffc0);seen.clear()
            u.emu_start(0x800cfbb4,0x801fffc0,count=500000)
            assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
            assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
            stream=bytes.fromhex(row['hex']);glyphs=[];at=0
            while stream[at]:
                c=stream[at];at+=1
                if 0x1c<=c<=0x1f:idx=224+(c-0x1c)*256+stream[at];at+=1
                else:assert c>=32;idx=c-32
                if 1075<=idx<1085:idx=901+idx-1075
                glyphs.append(idx)
            assert seen==glyphs,(index,seen,glyphs)
            tested+=1
        result[tag]=dict(broken_references=failed,native_producer_and_dispatcher_cases=tested)
    assert [r['index'] for r in result['v083']['broken_references']]==[25,280]
    result['scope']='All 384 enemy-specific names: native producer hook, FF-terminated copier/continuation, original control dispatcher, complete glyph sequence, output canaries.'
    (ROOT/f'analysis/{target}-enemy-attack-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
