"""Exercise all native attack-name routes and compare digit pixels to JP ROM.

The oracle is the original font, rather than encoded glyph indices (which
were valid even when those glyph slots had been overwritten by runtime code).
"""
import json,struct,re,sys
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from emu import ROOT
from pac import decompress
from korean_codec import font_index,original_fixed
FONT=0x1d68f8

def main():
    tag=sys.argv[1] if len(sys.argv)>1 else 'v083'
    r=json.loads((ROOT/f'analysis/{tag}-battle-big-text-insertion.json').read_text('utf8'))
    old=json.loads((ROOT/'analysis/v082-battle-big-text-insertion.json').read_text('utf8'))
    small=json.loads((ROOT/'analysis/battle-small-runtime.json').read_text('utf8'))
    originals=(ROOT/'work/extracted/BTL/FF6_BTL.BIN').read_bytes()
    expected={c:originals[0x3b0f8+font_index(h)*22:0x3b0f8+font_index(h)*22+22] for c,h in original_fixed().items() if c in '0123456789'}
    def engine(tag,report):
        u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
        u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000)
        u.mem_write(0,(ROOT/'work/v082-volts-counter-entry-memory/ram.bin').read_bytes())
        p=ROOT/f'work/{tag}-cache-payloads'
        u.mem_write(0xc8000,decompress((p/'BTL/BATTLE.PAC').read_bytes())[0])
        u.mem_write(0x197c00,(p/'BTL/FF6_BTL.BIN').read_bytes())
        u.mem_write(0x6c168,struct.pack('<I',0x1f8003c8))
        u.mem_write(0x6c16c,struct.pack('<I',0x1f8003ca))
        u.mem_write(0x6c1a0,struct.pack('<I',0x1f8003cc))
        seen=[]
        def glyph(uc,at,size,data):
            off=struct.unpack('<H',uc.mem_read(0x2e026,2))[0]
            seen.append(bytes(uc.mem_read(FONT+off,22)))
            uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
        at=report['symbols']['kr_big_original_glyph'];u.hook_add(UC_HOOK_CODE,glyph,begin=at,end=at)
        def invoke(addr,arg):
            seen.clear();u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
            u.mem_write(0x1f8003c8,struct.pack('<H',arg));u.mem_write(0x2e07a,b'\0')
            u.emu_start(addr,0x801fffc0,count=500000)
            assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
            assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
            return list(seen)
        return u,invoke
    fixed,invoke=engine(tag,r);broken,invoke_old=engine('v082',old)
    checked=[];rejected=[]
    for spell in range(255):
        text=small['records'][64+spell]['translation'] if spell<54 else r['encoded'][spell-54]['translation']
        text=re.sub(r'\{[^}]+\}','',text)
        actual=invoke(r['symbols']['kr_big_attack'],spell)
        assert len(actual)==len(text),(spell,len(actual),text)
        if not any(c.isdigit() for c in text):continue
        previous=invoke_old(old['symbols']['kr_big_attack'],spell)
        for i,c in enumerate(text):
            if c in expected:
                assert actual[i]==expected[c],(spell,c)
                if previous[i]!=expected[c]:rejected.append([spell,c])
        checked.append(spell)
    # Also execute the common glyph hook used by native variable-number paths.
    for i,c in enumerate('0123456789'):
        fixed.mem_write(0x2e026,struct.pack('<H',(1075+i)*22))
        assert invoke(r['symbols']['kr_big_glyph'],0)==[expected[c]]
    # No character used by an encoded record may reach runtime/LUT pixels.
    used=set(''.join(re.sub(r'\{[^}]+\}','',row['translation']) for row in r['encoded']))
    for c in used:
        idx=font_index(bytes.fromhex(r['mapping'][c]))
        if c in expected:idx=901+int(c)
        assert idx<930,(c,idx)
    assert rejected
    out=dict(attack_name_routes=255,numbered_attack_names=len(checked),native_digit_glyphs=10,original_digit_bitmaps_exact=True,
        v082_wrong_digit_cases=len(rejected),numbered_attack_ids=checked,all_used_text_glyphs_outside_code=True,
        scope='Actual MIPS name renderer through shared rasterizer; original 12x11 numeral pixels are the oracle.')
    (ROOT/f'analysis/{tag}-battle-digit-verification.json').write_text(json.dumps(out,indent=2)+'\n','utf8')
    print(out)

if __name__=='__main__':main()
